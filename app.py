from flask import Flask, render_template, request, redirect, url_for
import os
import sqlite3
import pdfplumber
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__, template_folder="template", static_folder="static")

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads/resumes")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_PATH = os.environ.get("DB_PATH", "jobs.db")

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


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
            created_at TEXT NOT NULL
        )
        """
    )
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
            created_at TEXT NOT NULL
        )
        """
    )
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
    return render_template("company.html", job=None, jobs=get_job_history())


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
    return render_template("company.html", job=job, jobs=get_job_history())


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
    return render_template("applicant.html", applicant=None, applicants=get_applicant_history())


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
    conn = get_db_connection()
    applicant = conn.execute(
        "SELECT * FROM applicants WHERE id = ?",
        (applicant_id,)
    ).fetchone()
    conn.close()
    if applicant is None:
        return redirect(url_for("applicant"))
    return render_template("applicant.html", applicant=applicant, applicants=get_applicant_history())


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
    skill1 = request.form.get("skill1")
    priority1 = request.form.get("priority1") or None
    skill2 = request.form.get("skill2")
    priority2 = request.form.get("priority2") or None
    skill3 = request.form.get("skill3")
    priority3 = request.form.get("priority3") or None
    skill4 = request.form.get("skill4")
    priority4 = request.form.get("priority4") or None
    skill5 = request.form.get("skill5")
    priority5 = request.form.get("priority5") or None
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
                minimum_score,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    return render_template(
        "success.html",
        message=message
    )


# ----------------------------
# EXTRACT PDF TEXT
# ----------------------------

def extract_text(pdf_path):

    text = ""

    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:

                text += page_text + " "

    return text.lower()


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

    resume = request.files["resume"]

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        resume.filename
    )

    resume.save(filepath)

    resume_text = extract_text(filepath)
    job_text = company_data.get("description", "")

    vectorizer = TfidfVectorizer()

    vectors = vectorizer.fit_transform([
        resume_text,
        job_text
    ])

    similarity = cosine_similarity(
        vectors[0:1],
        vectors[1:2]
    )[0][0]

    similarity_percentage = round(
        similarity * 100,
        2
    )

    ats_score = similarity_percentage
    skill_score = similarity_percentage
    minimum_score = int(company_data.get("minimum_score", 0)) if company_data.get("minimum_score") else 0
    prediction = "Suitable" if similarity_percentage >= minimum_score else "Not Suitable"

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
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            email,
            phone,
            qualification,
            experience,
            resume.filename,
            similarity_percentage,
            skill_score,
            ats_score,
            prediction,
            company_data.get("company", ""),
            company_data.get("job", ""),
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()

    return render_template(
        "result.html",
        name=name,
        similarity=similarity_percentage,
        skill_score=skill_score,
        ats_score=ats_score,
        prediction=prediction,
        matched=[],
        missing=[]
    )


# ----------------------------
# RUN APP
# ----------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)