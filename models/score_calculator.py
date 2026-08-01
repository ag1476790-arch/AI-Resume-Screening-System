def calculate_skill_score(company_skills, applicant_skills):

    total_priority = 0

    obtained_priority = 0

    matched = []

    missing = []

    for skill, priority in company_skills.items():

        total_priority += priority

        if skill.lower() in applicant_skills:

            obtained_priority += priority

            matched.append(skill)

        else:

            missing.append(skill)

    if total_priority == 0:

        score = 0

    else:

        score = (obtained_priority / total_priority) * 100

    return round(score, 2), matched, missing