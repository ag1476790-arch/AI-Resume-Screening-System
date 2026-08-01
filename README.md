# AI Resume Screening System

Lightweight Flask application that screens applicant resumes against company job descriptions using TF‑IDF and cosine similarity, and stores job/applicant records in SQLite.

## Features
- Upload and parse PDF resumes (pdfplumber)
- Compute TF‑IDF vectors and cosine similarity between resume and job description
- Store companies (jobs) and applicants in SQLite with history, edit and delete actions
- Simple web UI for company and applicant portals plus a comparison view

## Repo structure
- `app.py` - Flask application and routes
- `template/` - Jinja2 HTML templates
- `static/` - CSS / JS / images
- `uploads/resumes/` - uploaded PDF resumes (local)
- `jobs.db` - SQLite database used by the app
- `requirements.txt`, `Procfile`, `render.yaml` - deployment helpers

## Prerequisites
- Python 3.11+
- Recommended virtual environment (venv)

## Install & run locally

1. Create and activate a venv

```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.\\.venv\\Scripts\\activate  # Windows PowerShell
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app (development)

```bash
python app.py
# opens at http://127.0.0.1:5000
```

Notes: The app uses a local SQLite database (`jobs.db`) and stores uploaded resumes under `uploads/resumes/`.

## Web routes (quick reference)
- `/` — Home
- `/company` — Company portal (create job)
- `/company_history` — Company job history
- `/applicant` — Applicant portal (upload resume)
- `/applicant_history` — Applicant overview / suitability
- `/compare` — Compare a stored applicant resume with a stored job

## Deployment

Render (recommended free option):


## License
