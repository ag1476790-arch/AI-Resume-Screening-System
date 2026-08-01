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

1. Push your repository to GitHub.
2. Create a free account at https://render.com and connect your GitHub repo.
3. Render will pick up `render.yaml` or use these commands:

	- Build command: `pip install -r requirements.txt`
	- Start command: `gunicorn --bind 0.0.0.0 $PORT app:app`

Azure App Service (quick):

1. Create a resource group and run `az webapp up` from the repo root.
2. Ensure `requirements.txt`, `Procfile`, and `runtime.txt` are present (they are included).

Important: On hosted platforms the local SQLite file and local `uploads/` are not durable. For production, use managed storage (Blob/S3) and a hosted database.

## Pushing to GitHub
1. Create an empty repo on GitHub.
2. Add remote and push:

```bash
git remote add origin https://github.com/<your-username>/<your-repo>.git
git branch -M main
git push -u origin main
```

## License
Choose a license for your project (MIT is common). Add a `LICENSE` file if you want to make this public.

---
If you want, I can (a) push this repo to your GitHub (if you provide the repo URL), (b) walk you through Render deployment step-by-step, or (c) prepare a small note explaining how to migrate `jobs.db` and `uploads/` to cloud storage.
