from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from models.skill_extractor import extract_skills
from models.score_calculator import calculate_skill_score


def predict_resume(job_description,
                   resume_text,
                   company_skills):

    # -----------------------------
    # TF-IDF
    # -----------------------------

    vectorizer = TfidfVectorizer()

    vectors = vectorizer.fit_transform([
        job_description.lower(),
        resume_text.lower()
    ])

    similarity = cosine_similarity(
        vectors[0:1],
        vectors[1:2]
    )[0][0]

    similarity_percentage = round(
        similarity * 100,
        2
    )

    # -----------------------------
    # Skill Matching
    # -----------------------------

    applicant_skills = extract_skills(resume_text)

    skill_score, matched, missing = calculate_skill_score(
        company_skills,
        applicant_skills
    )

    # -----------------------------
    # Final ATS Score
    # -----------------------------

    ats_score = round(
        (0.7 * similarity_percentage) +
        (0.3 * skill_score),
        2
    )

    if ats_score >= 75:

        prediction = "Suitable"

    else:

        prediction = "Not Suitable"

    return {

        "similarity": similarity_percentage,

        "skill_score": skill_score,

        "ats_score": ats_score,

        "matched": matched,

        "missing": missing,

        "prediction": prediction

    }