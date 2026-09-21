def calculate_skill_score(company_skills, applicant_skills):
    normalized_applicant_skills = {
        skill.strip().lower() for skill in applicant_skills if skill
    }
    total_priority = 0
    obtained_priority = 0
    matched = []
    missing = []

    for skill, raw_priority in company_skills.items():
        if not skill:
            continue

        priority = int(raw_priority or 0)
        total_priority += priority
        normalized_skill = skill.strip().lower()

        if normalized_skill in normalized_applicant_skills:
            obtained_priority += priority
            matched.append(skill)
        else:
            missing.append(skill)

    score = (obtained_priority / total_priority) * 100 if total_priority else 0
    return round(score, 2), matched, missing