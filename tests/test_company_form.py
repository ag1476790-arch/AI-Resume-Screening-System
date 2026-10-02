import io
import os
import sqlite3
import tempfile
import unittest
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock, patch

import app as app_module
from models import text_processor

app = app_module.app


class CompanyFormTest(unittest.TestCase):
    def test_company_form_allows_pdf_uploads(self):
        with app.test_client() as client:
            response = client.get('/company')
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertIn('enctype="multipart/form-data"', html)
            self.assertIn('name="job_description_file"', html)
            self.assertIn('id="extractSkills"', html)

    def test_applicant_portal_hides_redundant_resume_compare_action(self):
        with app.test_client() as client:
            response = client.get('/applicant')

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertNotIn('Compare Resume to Job', html)
        self.assertIn('View / Edit Resume History', html)

    def test_job_cannot_be_saved_without_skill_priority(self):
        with app.test_client() as client:
            response = client.post(
                '/submit_job',
                data={
                    'company_name': 'Acme',
                    'job_title': 'Developer',
                    'job_description': 'Python developer',
                    'skill': ['python'],
                    'priority': [''],
                    'minimum_score': '50',
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            'Enter a priority for every required skill.',
            response.get_data(as_text=True),
        )

    def test_job_post_shows_confirmation_and_stylesheet(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test_jobs.db')
            original_db_path = app_module.DB_PATH
            try:
                app_module.DB_PATH = db_path
                app_module.init_db()
                with app.test_client() as client:
                    response = client.post(
                        '/submit_job',
                        data={
                            'company_name': 'Acme',
                            'job_title': 'Developer',
                            'job_description': 'Python developer',
                            'skill': ['python'],
                            'priority': ['5'],
                            'minimum_score': '50',
                        },
                    )

                    self.assertEqual(response.status_code, 200)
                    html = response.get_data(as_text=True)
                    self.assertIn('Job posted successfully', html)
                    self.assertIn('View Company Portal', html)
                    self.assertIn('Post Another Job', html)
                    self.assertIn('/static/css/success.css', html)
                    stylesheet_response = client.get('/static/css/success.css')
                    self.assertEqual(stylesheet_response.status_code, 200)
                    stylesheet_response.close()
            finally:
                app_module.DB_PATH = original_db_path

    def test_extract_job_skills_from_description(self):
        with patch('app.extract_skills', return_value=['python', 'aws']):
            with app.test_client() as client:
                response = client.post(
                    '/extract_job_skills',
                    data={'job_description': 'Python and AWS experience required'},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['skills'], ['python', 'aws'])

    def test_extract_job_skills_from_uploaded_pdf(self):
        with patch('app.extract_uploaded_pdf_text', return_value='python developer'), \
             patch('app.extract_skills', return_value=['python']):
            with app.test_client() as client:
                response = client.post(
                    '/extract_job_skills',
                    data={
                        'job_description_file': (
                            io.BytesIO(b'%PDF-1.4'), 'job.pdf'
                        ),
                    },
                    content_type='multipart/form-data',
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['skills'], ['python'])

    def test_suitable_candidate_sees_submission_confirmation(self):
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

                    self.assertEqual(response.status_code, 200)
                    html = response.get_data(as_text=True)
                    self.assertIn('Resume submitted successfully', html)
                    self.assertIn('Your application for Python Developer at Acme', html)
                    self.assertIn('href="/"', html)
                    self.assertIn('Submit Another Resume', html)
                    self.assertNotIn('company_portal?company_name=Acme', html)
        finally:
            app_module.DB_PATH = original_db_path
            app.config['UPLOAD_FOLDER'] = original_upload_folder

    def test_company_portal_compares_all_applicants_and_shows_reasons(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test_jobs.db')
            original_db_path = app_module.DB_PATH
            original_upload_folder = app.config['UPLOAD_FOLDER']

            try:
                app_module.DB_PATH = db_path
                app.config['UPLOAD_FOLDER'] = temp_dir
                app_module.init_db()
                conn = sqlite3.connect(db_path)
                conn.execute(
                    """INSERT INTO jobs (
                        company_name, job_title, job_description,
                        skill1, priority1, skill2, priority2,
                        minimum_score, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    ('Acme', 'Developer', 'Python and AWS developer',
                     'python', 5, 'aws', 3, 50, '2026-01-01 00:00:00'),
                )
                for name, created_at in (
                    ('Maya Candidate', '2026-01-02 00:00:00'),
                    ('Noah Candidate', '2026-01-01 00:00:00'),
                ):
                    conn.execute(
                        """INSERT INTO applicants (
                            applicant_name, email, resume_filename,
                            ats_score, prediction, applied_company,
                            applied_job, applied_job_id, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (name, f'{name.split()[0].lower()}@example.com',
                         f'{name.split()[0].lower()}.pdf', 10, 'Not Suitable',
                         'Acme', 'Developer', 1, created_at),
                    )
                conn.commit()
                conn.close()

                score_results = {
                    'Maya Candidate': {
                        'similarity': 60.0, 'skill_score': 80.0,
                        'ats_score': 66.0, 'prediction': 'Suitable',
                        'matched': ['python'], 'missing': ['aws'],
                    },
                    'Noah Candidate': {
                        'similarity': 20.0, 'skill_score': 25.0,
                        'ats_score': 21.5, 'prediction': 'Not Suitable',
                        'matched': ['python'], 'missing': ['aws'],
                    },
                }
                scoring_barrier = Barrier(2, timeout=3)

                def score_concurrently(applicant, job):
                    scoring_barrier.wait()
                    return score_results[applicant['applicant_name']]

                with patch(
                    'app.score_saved_applicant',
                    side_effect=score_concurrently,
                ) as score_mock:
                    with app.test_client() as client:
                        response = client.post(
                            '/company_portal/compare',
                            data={'company_name': 'Acme', 'job_id': '1'},
                        )

                self.assertEqual(score_mock.call_count, 2)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn('Maya Candidate', html)
                self.assertIn('Noah Candidate', html)
                self.assertIn('Passed: ATS score 66.00% meets the 50% minimum.', html)
                self.assertIn('Failed: ATS score 21.50% is below the 50% minimum.', html)
                self.assertIn('Missing required skills: aws', html)

                conn = sqlite3.connect(db_path)
                saved_results = conn.execute(
                    'SELECT applicant_name, ats_score, prediction FROM applicants'
                ).fetchall()
                conn.close()
                self.assertIn(('Maya Candidate', 66.0, 'Suitable'), saved_results)
                self.assertIn(('Noah Candidate', 21.5, 'Not Suitable'), saved_results)
            finally:
                app_module.DB_PATH = original_db_path
                app.config['UPLOAD_FOLDER'] = original_upload_folder

    def test_predict_resume_handles_compound_skill_lists(self):
        result = app_module.predict_resume(
            'We need Python, Java, JavaScript, C++, and SQL experience.',
            'Worked with Python, Java, JavaScript, and SQL for backend projects.',
            {'Programming: Python, Java, JavaScript, C++, SQL': 5},
            minimum_score=75,
        )

        self.assertGreater(result['skill_score'], 0)
        self.assertGreater(len(result['matched']), 0)
        self.assertIn('python', [skill.lower() for skill in result['matched']])

    def test_preprocessing_caches_nltk_resources_and_stop_words(self):
        text_processor.ensure_nltk_data.cache_clear()
        text_processor._english_stop_words.cache_clear()
        try:
            stop_words_mock = Mock(return_value=['the'])
            with patch.dict(
                text_processor.__dict__,
                {'stopwords': SimpleNamespace(words=stop_words_mock)}
            ), patch('models.text_processor.nltk.data.find', return_value=True) as find_resource, \
                 patch('models.text_processor.word_tokenize', return_value=['python', 'developer']), \
                 patch('models.text_processor.PorterStemmer'), \
                 patch('models.text_processor.WordNetLemmatizer'):
                first = text_processor.preprocess_text(
                    'Python developer', use_stemming=False,
                    use_lemmatization=False
                )
                second = text_processor.preprocess_text(
                    'Python developer', use_stemming=False,
                    use_lemmatization=False
                )

            self.assertEqual(first, 'python developer')
            self.assertEqual(second, first)
            self.assertEqual(find_resource.call_count, 5)
            self.assertEqual(stop_words_mock.call_count, 1)
        finally:
            text_processor.ensure_nltk_data.cache_clear()
            text_processor._english_stop_words.cache_clear()

    def test_unreadable_resume_is_not_saved_or_scored(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test_jobs.db')
            original_db_path = app_module.DB_PATH
            original_upload_folder = app.config['UPLOAD_FOLDER']

            try:
                app_module.DB_PATH = db_path
                app.config['UPLOAD_FOLDER'] = temp_dir
                app_module.init_db()
                conn = sqlite3.connect(db_path)
                conn.execute(
                    """INSERT INTO jobs (
                        company_name, job_title, job_description,
                        minimum_score, created_at
                    ) VALUES (?, ?, ?, ?, ?)""",
                    ('Acme', 'Developer', 'Python developer', 75,
                     '2026-01-01 00:00:00'),
                )
                conn.commit()
                conn.close()

                with patch('app.extract_text', return_value=''), \
                     patch('app.is_tesseract_available', return_value=False), \
                     patch('app.predict_resume') as predict_resume:
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
                                'resume': (
                                    io.BytesIO(b'%PDF-1.4'), 'alice.pdf'
                                ),
                            },
                            content_type='multipart/form-data'
                        )

                self.assertEqual(response.status_code, 503)
                self.assertIn('Tesseract', response.get_data(as_text=True))
                predict_resume.assert_not_called()
                self.assertFalse(os.path.exists(os.path.join(temp_dir, 'alice.pdf')))
                conn = sqlite3.connect(db_path)
                applicant_count = conn.execute(
                    'SELECT COUNT(*) FROM applicants'
                ).fetchone()[0]
                conn.close()
                self.assertEqual(applicant_count, 0)
            finally:
                app_module.DB_PATH = original_db_path
                app.config['UPLOAD_FOLDER'] = original_upload_folder


if __name__ == '__main__':
    unittest.main()
