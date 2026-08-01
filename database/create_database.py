import sqlite3

# ==========================
# COMPANY DATABASE
# ==========================

company_conn = sqlite3.connect("company.db")

company_cursor = company_conn.cursor()

company_cursor.execute("""
CREATE TABLE IF NOT EXISTS company_jobs(

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

    minimum_score INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

)
""")

company_conn.commit()

company_conn.close()


# ==========================
# APPLICANT DATABASE
# ==========================

applicant_conn = sqlite3.connect("applicant.db")

applicant_cursor = applicant_conn.cursor()

applicant_cursor.execute("""
CREATE TABLE IF NOT EXISTS applicants(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    applicant_name TEXT NOT NULL,

    email TEXT,

    phone TEXT,

    qualification TEXT,

    experience INTEGER,

    resume_name TEXT,

    similarity_score REAL,

    skill_score REAL,

    ats_score REAL,

    prediction TEXT,

    applied_company TEXT,

    applied_job TEXT,

    applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP

)
""")

applicant_conn.commit()

applicant_conn.close()

print("Databases Created Successfully!")