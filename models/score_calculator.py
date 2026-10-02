import re


def _normalize_skill_name(skill):
    return str(skill or "").strip().lower().replace("c#", "csharp").replace("c++", "cpp").replace("node.js", "nodejs").replace("rest api", "restapi")


def _expand_candidate_skills(skill):
    candidate_skills = []
    for part in re.split(r"[,;|&/]+", str(skill)):
        for subpart in re.split(r"\s+(?:and|or)\s+", part):
            cleaned = subpart.strip().strip(" :()[]{}\n\t")
            if not cleaned:
                continue
            if ":" in cleaned:
                left, right = cleaned.split(":", 1)
                if left.strip().lower() in {"programming", "software", "skills", "requirements", "experience", "technical"}:
                    cleaned = right.strip()
            cleaned = cleaned.strip(" :()[]{}\n\t")
            if cleaned and cleaned.lower() not in {"programming", "software", "skills", "requirements", "experience", "technical"}:
                candidate_skills.append(cleaned)
    return candidate_skills or [str(skill).strip()]


def calculate_skill_score(company_skills, applicant_skills):
    normalized_applicant_skills = {
        _normalize_skill_name(skill) for skill in applicant_skills if skill
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

        candidate_skills = _expand_candidate_skills(skill)
        skill_matches = []
        skill_missing = []
        for candidate in candidate_skills:
            normalized_candidate = _normalize_skill_name(candidate)
            if normalized_candidate in normalized_applicant_skills:
                skill_matches.append(candidate)
            else:
                if candidate.lower() not in {"programming", "software", "skills", "requirements", "experience", "technical"}:
                    skill_missing.append(candidate)

        if skill_matches:
            matched.extend(skill_matches)
            obtained_priority += priority * (len(skill_matches) / max(len(candidate_skills), 1))
        else:
            missing.extend(skill_missing or [skill])

    score = (obtained_priority / total_priority) * 100 if total_priority else 0
    return round(score, 2), matched, missing