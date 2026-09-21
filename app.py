from flask import Flask, render_template, request, redirect, url_for
import os
import sqlite3
import json
import pdfplumber
import fitz
import pytesseract
from PIL import Image
from datetime import datetime
from werkzeug.utils import secure_filename
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from models.predictor import predict_resume

app = Flask(__name__, template_folder="template", static_folder="static")

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads/resumes")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_PATH = os.environ.get("DB_PATH", "jobs.db")

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
MAX_RESUME_SIZE = 5 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = MAX_RESUME_SIZE
if os.environ.get("TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            job_title TEXT NOT NULL,
            job_description TEXT NOT NULL,
            skill1 TEXT,
            priority1 INTEGER,
            skill2 TEXT,
            priority2 INTEGER,
            skill3 TEXT,
            priority3 INTEGER,
            skill4 TEXT,
            priority4 INTEGER,
            skill5 TEXT,
            priority5 INTEGER,
            minimum_score INTEGER NOT NULL,
            skill_requirements TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    job_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
    }
    if "skill_requirements" not in job_columns:
        conn.execute("ALTER TABLE jobs ADD COLUMN skill_requirements TEXT")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS applicants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicant_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            qualification TEXT,
            experience INTEGER,
            resume_filename TEXT,
            similarity_score REAL,
            skill_score REAL,
            ats_score REAL,
            prediction TEXT,
            applied_company TEXT,
            applied_job TEXT,
            applied_job_id INTEGER,
            created_at TEXT NOT NULL
        )
        """
    )
    applicant_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(applicants)").fetchall()
    }
    if "applied_job_id" not in applicant_columns:
        conn.execute("ALTER TABLE applicants ADD COLUMN applied_job_id INTEGER")
    conn.commit()
    conn.close()


def get_job_history():
    conn = get_db_connection()
    jobs = conn.execute(
        "SELECT * FROM jobs ORDER BY datetime(created_at) DESC"
    ).fetchall()
    conn.close()
    return jobs


def get_applicant_history():
    conn = get_db_connection()
    applicants = conn.execute(
        "SELECT * FROM applicants ORDER BY datetime(created_at) DESC"
    ).fetchall()
    conn.close()
    return applicants


def get_job_skills(job):
    skills = json.loads(job["skill_requirements"] or "[]") if job["skill_requirements"] else []
    if skills:
        return skills
    return [
        {"name": job[f"skill{i}"], "priority": job[f"priority{i}"]}
        for i in range(1, 6)
        if job[f"skill{i}"]
    ]


def get_applicant_jobs():
    return [
        {
            "id": job["id"],
            "company_name": job["company_name"],
            "job_title": job["job_title"],
            "job_description": job["job_description"],
            "minimum_score": job["minimum_score"],
            "skills": get_job_skills(job),
        }
        for job in get_job_history()
    ]


init_db()


# ----------------------------
# HOME PAGE
# ----------------------------

@app.route("/")
def home():
    return render_template("index.html")


# ----------------------------
# COMPANY PAGE
# ----------------------------

@app.route("/company")
def company():
    return render_template("company.html", job=None, skills=[], jobs=get_job_history())


# ----------------------------
# COMPANY HISTORY PAGE
# ----------------------------

@app.route("/company_history")
def company_history():
    conn = get_db_connection()
    jobs = conn.execute(
        "SELECT * FROM jobs ORDER BY datetime(created_at) DESC"
    ).fetchall()
    conn.close()
    return render_template("company_history.html", jobs=jobs)


@app.route("/company_portal")
def company_portal():
    jobs = get_job_history()
    companies = sorted({job["company_name"] for job in jobs})
    company_name = request.args.get("company_name", "")
    selected_job_id = request.args.get("job_id", type=int)
    view = request.args.get("view", "requirements")
    company_jobs = [job for job in jobs if job["company_name"] == company_name]
    selected_job = next(
        (job for job in company_jobs if job["id"] == selected_job_id),
        company_jobs[0] if company_jobs else None,
    )
    applicants = []
    if selected_job and view == "applicants":
        conn = get_db_connection()
        applicants = conn.execute(
            """
            SELECT * FROM applicants
            WHERE applied_company = ?
              AND (applied_job_id = ? OR (applied_job_id IS NULL AND applied_job = ?))
            ORDER BY ats_score DESC, datetime(created_at) DESC
            """,
            (company_name, selected_job["id"], selected_job["job_title"]),
        ).fetchall()
        conn.close()

    return render_template(
        "company_portal.html",
        companies=companies,
        company_name=company_name,
        company_jobs=company_jobs,
        selected_job=selected_job,
        selected_skills=get_job_skills(selected_job) if selected_job else [],
        applicants=applicants,
        view=view,
    )


@app.route("/company_portal/compare", methods=["POST"])
def company_portal_compare():
    company_name = request.form["company_name"]
    job_id = int(request.form["job_id"])
    applicant_ids = [int(value) for value in request.form.getlist("applicant_id")]
    jobs = get_job_history()
    company_jobs = [job for job in jobs if job["company_name"] == company_name]
    selected_job = next((job for job in company_jobs if job["id"] == job_id), None)
    if selected_job is None:
        return redirect(url_for("company_portal"))

    conn = get_db_connection()
    applicants = conn.execute(
                """
                SELECT * FROM applicants
                WHERE applied_company = ?
                    AND (applied_job_id = ? OR (applied_job_id IS NULL AND applied_job = ?))
                    AND id IN ({})
                ORDER BY ats_score DESC
                """.format(
            ",".join("?" for _ in applicant_ids) or "NULL"
        ),
                [company_name, selected_job["id"], selected_job["job_title"], *applicant_ids],
    ).fetchall()
    conn.close()
    comparison_results = []
    for applicant in applicants:
        result = score_saved_applicant(applicant, selected_job)
        comparison_results.append({"applicant": applicant, "result": result})

    companies = sorted({job["company_name"] for job in jobs})
    return render_template(
        "company_portal.html",
        companies=companies,
        company_name=company_name,
        company_jobs=company_jobs,
        selected_job=selected_job,
        selected_skills=get_job_skills(selected_job),
        applicants=applicants,
        comparison_results=comparison_results,
        view="applicants",
    )


@app.route("/edit_job/<int:job_id>")
def edit_job(job_id):
    conn = get_db_connection()
    job = conn.execute(
        "SELECT * FROM jobs WHERE id = ?",
        (job_id,)
    ).fetchone()
    conn.close()
    if job is None:
        return redirect(url_for("company_history"))
    skills = get_job_skills(job)
    return render_template("company.html", job=job, skills=skills, jobs=get_job_history())


@app.route("/delete_job/<int:job_id>")
def delete_job(job_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("company_history"))


# ----------------------------
# APPLICANT PAGE
# ----------------------------

@app.route("/applicant")
def applicant():
    return render_template(
        "applicant.html",
        applicant=None,
        applicants=get_applicant_history(),
        jobs=get_applicant_jobs(),
    )


@app.route("/applicant_history")
def applicant_history():
    applicants = get_applicant_history()
    return render_template("applicant_history.html", applicants=applicants)


@app.route("/compare", methods=["GET", "POST"])
def compare():
    applicants = get_applicant_history()
    jobs = get_job_history()
    selected_applicant = None
    selected_job = None
    result = None

    if request.method == "POST":
        applicant_id = int(request.form["applicant_id"])
        job_id = int(request.form["job_id"])

        conn = get_db_connection()
        selected_applicant = conn.execute(
            "SELECT * FROM applicants WHERE id = ?",
            (applicant_id,)
        ).fetchone()
        selected_job = conn.execute(
            "SELECT * FROM jobs WHERE id = ?",
            (job_id,)
        ).fetchone()
        conn.close()

        if selected_applicant and selected_job:
            resume_text = extract_text(
                os.path.join(app.config["UPLOAD_FOLDER"], selected_applicant["resume_filename"])
            )
            job_text = selected_job["job_description"]

            vectorizer = TfidfVectorizer()
            vectors = vectorizer.fit_transform([resume_text, job_text])
            similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
            similarity_percentage = round(similarity * 100, 2)

            result = {
                "similarity": similarity_percentage,
                "prediction": "Suitable" if similarity_percentage >= selected_job["minimum_score"] else "Not Suitable"
            }

    return render_template(
        "compare.html",
        applicants=applicants,
        jobs=jobs,
        selected_applicant=selected_applicant,
        selected_job=selected_job,
        result=result,
        similarity=result["similarity"] if result else None,
        prediction=result["prediction"] if result else None
    )


@app.route("/view_result/<int:applicant_id>")
def view_result(applicant_id):
    conn = get_db_connection()
    applicant = conn.execute(
        "SELECT * FROM applicants WHERE id = ?",
        (applicant_id,)
    ).fetchone()
    conn.close()
    if applicant is None:
        return redirect(url_for("applicant"))

    return render_template(
        "result.html",
        name=applicant["applicant_name"],
        similarity=applicant["similarity_score"],
        skill_score=applicant["skill_score"],
        ats_score=applicant["ats_score"],
        prediction=applicant["prediction"],
        matched=[],
        missing=[]
    )


@app.route("/delete_applicant/<int:applicant_id>")
def delete_applicant(applicant_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM applicants WHERE id = ?", (applicant_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("applicant"))


@app.route("/edit_applicant/<int:applicant_id>")
def edit_applicant(applicant_id):
    return redirect(url_for("view_result", applicant_id=applicant_id))


# ----------------------------
# SAVE COMPANY DETAILS
# ----------------------------

company_data = {}


@app.route("/submit_job", methods=["POST"])
def submit_job():
    job_id = request.form.get("job_id")
    company_name = request.form["company_name"]
    job_title = request.form["job_title"]
    job_description = request.form["job_description"]
    skills = [
        {"name": name.strip(), "priority": int(priority)}
        for name, priority in zip(
            request.form.getlist("skill"),
            request.form.getlist("priority")
        )
        if name.strip() and priority
    ]
    if not skills:
        return "At least one required skill is needed.", 400

    legacy_skills = skills[:5] + [{"name": None, "priority": None}] * 5
    skill1, priority1 = legacy_skills[0]["name"], legacy_skills[0]["priority"]
    skill2, priority2 = legacy_skills[1]["name"], legacy_skills[1]["priority"]
    skill3, priority3 = legacy_skills[2]["name"], legacy_skills[2]["priority"]
    skill4, priority4 = legacy_skills[3]["name"], legacy_skills[3]["priority"]
    skill5, priority5 = legacy_skills[4]["name"], legacy_skills[4]["priority"]
    minimum_score = int(request.form["minimum_score"])
    created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    if job_id:
        conn.execute(
            """
            UPDATE jobs
            SET company_name = ?,
                job_title = ?,
                job_description = ?,
                skill1 = ?,
                priority1 = ?,
                skill2 = ?,
                priority2 = ?,
                skill3 = ?,
                priority3 = ?,
                skill4 = ?,
                priority4 = ?,
                skill5 = ?,
                priority5 = ?,
                skill_requirements = ?,
                minimum_score = ?
            WHERE id = ?
            """,
            (
                company_name,
                job_title,
                job_description,
                skill1,
                priority1,
                skill2,
                priority2,
                skill3,
                priority3,
                skill4,
                priority4,
                skill5,
                priority5,
                json.dumps(skills),
                minimum_score,
                job_id,
            ),
        )
        message = "Job Updated Successfully!"
    else:
        conn.execute(
            """
            INSERT INTO jobs (
                company_name,
                job_title,
                job_description,
                skill1,
                priority1,
                skill2,
                priority2,
                skill3,
                priority3,
                skill4,
                priority4,
                skill5,
                priority5,
                skill_requirements,
                minimum_score,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_name,
                job_title,
                job_description,
                skill1,
                priority1,
                skill2,
                priority2,
                skill3,
                priority3,
                skill4,
                priority4,
                skill5,
                priority5,
                json.dumps(skills),
                minimum_score,
                created_at,
            ),
        )
        message = "Job Posted Successfully!"
    conn.commit()
    conn.close()

    company_data["company"] = company_name
    company_data["job"] = job_title
    company_data["description"] = job_description
    company_data["minimum_score"] = minimum_score
    company_data["skills"] = {
        item["name"]: item["priority"] for item in skills
    }

    return render_template(
        "success.html",
        message=message
    )


# ----------------------------
# EXTRACT PDF TEXT
# ----------------------------

def extract_text(pdf_path):
    text_parts = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    extracted_text = "\n".join(text_parts).strip()
    if extracted_text:
        return extracted_text.lower()

    # Scanned resumes contain page images instead of an embedded text layer.
    ocr_parts = []
    with fitz.open(pdf_path) as pdf:
        for page in pdf:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
            ocr_parts.append(pytesseract.image_to_string(image))

    return "\n".join(ocr_parts).lower()


def score_saved_applicant(applicant, job):
    resume_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        applicant["resume_filename"],
    )
    resume_text = extract_text(resume_path)
    skills = {
        skill["name"]: skill["priority"] for skill in get_job_skills(job)
    }
    return predict_resume(
        job["job_description"],
        resume_text,
        skills,
        minimum_score=job["minimum_score"],
    )


# ----------------------------
# UPLOAD RESUME
# ----------------------------

@app.route("/upload_resume", methods=["POST"])
def upload_resume():

    name = request.form["name"]
    email = request.form["email"]
    phone = request.form["phone"]
    qualification = request.form["qualification"]
    experience = int(request.form["experience"])
    job_id = request.form.get("job_id")

    if not job_id:
        return "Please select a company and job before uploading a resume.", 400

    conn = get_db_connection()
    selected_job = conn.execute(
        "SELECT * FROM jobs WHERE id = ?",
        (job_id,)
    ).fetchone()
    conn.close()
    if selected_job is None:
        return "The selected job is no longer available.", 404

    resume = request.files["resume"]
    if not resume or not resume.filename:
        return "Please select a PDF resume.", 400

    if not resume.filename.lower().endswith(".pdf"):
        return "Only PDF resumes are accepted.", 400

    resume.seek(0, os.SEEK_END)
    resume_size = resume.tell()
    resume.seek(0)
    if resume_size > MAX_RESUME_SIZE:
        return "Resume file must be 5 MB or smaller.", 413

    safe_filename = secure_filename(resume.filename)
    if not safe_filename:
        return "Invalid resume filename.", 400

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        safe_filename
    )

    resume.save(filepath)

    resume_text = extract_text(filepath)
    job_text = selected_job["job_description"]
    minimum_score = selected_job["minimum_score"]
    selected_skills = {
        skill["name"]: skill["priority"] for skill in get_job_skills(selected_job)
    }
    result = predict_resume(
        job_text,
        resume_text,
        selected_skills,
        minimum_score=minimum_score,
    )

    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO applicants (
            applicant_name,
            email,
            phone,
            qualification,
            experience,
            resume_filename,
            similarity_score,
            skill_score,
            ats_score,
            prediction,
            applied_company,
            applied_job,
            applied_job_id,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            email,
            phone,
            qualification,
            experience,
            safe_filename,
            result["similarity"],
            result["skill_score"],
            result["ats_score"],
            result["prediction"],
            selected_job["company_name"],
            selected_job["job_title"],
            selected_job["id"],
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()

    return render_template(
        "result.html",
        name=name,
        similarity=result["similarity"],
        skill_score=result["skill_score"],
        ats_score=result["ats_score"],
        prediction=result["prediction"],
        matched=result["matched"],
        missing=result["missing"]
    )


# ----------------------------
# RUN APP
# ----------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)