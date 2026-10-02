import io
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import app as app_module

app = app_module.app


class CompanyFormTest(unittest.TestCase):
    def test_company_form_allows_pdf_uploads(self):
        with app.test_client() as client:
            response = client.get('/company')
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertIn('enctype="multipart/form-data"', html)
            self.assertIn('name="job_description_file"', html)

    def test_suitable_candidate_redirects_to_company_portal(self):
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test_jobs.db')
        original_db_path = app_module.DB_PATH
        original_upload_folder = app.config['UPLOAD_FOLDER']

        try:
            app_module.DB_PATH = db_path
            app.config['UPLOAD_FOLDER'] = temp_dir
            app_module.init_db()

            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                INSERT INTO jobs (
                    company_name, job_title, job_description, skill1, priority1,
                    skill2, priority2, skill3, priority3, skill4, priority4,
                    skill5, priority5, minimum_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    'Acme', 'Python Developer', 'python developer',
                    'python', 5, 'flask', 4, 'sql', 3, 'rest', 2, 'aws', 1,
                    75, '2026-01-01 00:00:00'
                ),
            )
            conn.commit()
            conn.close()

            with patch('app.extract_text', return_value='python flask sql rest api'), \
                 patch('app.predict_resume', return_value={
                     'similarity': 92.0,
                     'skill_score': 90.0,
                     'ats_score': 93.0,
                     'prediction': 'Suitable',
                     'matched': ['python', 'flask'],
                     'missing': []
                 }):
                with app.test_client() as client:
                    response = client.post(
                        '/upload_resume',
                        data={
                            'name': 'Alice Candidate',
                            'email': 'alice@example.com',
                            'phone': '123456',
                            'qualification': 'B.Tech',
                            'experience': 3,
                            'job_id': '1',
                            'resume': (io.BytesIO(b'%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF'), 'alice.pdf'),
                        },
                        content_type='multipart/form-data'
                    )

                    self.assertEqual(response.status_code, 302)
                    self.assertIn('/company_portal?company_name=Acme&job_id=1&view=applicants', response.location)
        finally:
            app.DB_PATH = original_db_path
            app.config['UPLOAD_FOLDER'] = original_upload_folder


if __name__ == '__main__':
    unittest.main()
