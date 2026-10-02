import re
from functools import lru_cache

from models.text_processor import preprocess_text


KNOWN_SKILLS = [
    "python",
    "java",
    "c",
    "c++",
    "html",
    "css",
    "javascript",
    "react",
    "node.js",
    "sql",
    "mysql",
    "mongodb",
    "flask",
    "django",
    "git",
    "github",
    "docker",
    "aws",
    "machine learning",
    "deep learning",
    "tensorflow",
    "pandas",
    "numpy",
    "power bi",
    "excel",
    "opencv",
    "linux",
    "rest api"
]

SKILL_ALIASES = {
    "c#": "csharp",
    "csharp": "csharp",
    "c++": "cpp",
    "cpp": "cpp",
    "node.js": "nodejs",
    "node js": "nodejs",
    "rest api": "restapi",
    "restapi": "restapi",
    "machine learning": "machine learning",
    "deep learning": "deep learning",
}

GENERIC_SKILL_WORDS = {
    "programming",
    "software",
    "developer",
    "development",
    "experience",
    "skills",
    "requirement",
    "requirements",
    "technical",
    "professional",
    "working",
    "knowledge",
    "role",
    "job",
    "candidate",
    "background",
}


@lru_cache(maxsize=512)
def _normalize_skill_value(skill):
    value = preprocess_text(skill or "")
    if not value:
        return ""
    for alias, canonical in SKILL_ALIASES.items():
        value = re.sub(re.escape(alias), canonical, value)
    return value


def _skill_pattern(skill):
    tokens = re.findall(r"[a-z0-9+#]+", skill.lower())
    if not tokens:
        return None

    pattern = r"[\s./_-]*".join(re.escape(token) for token in tokens)
    return rf"(?<![a-z0-9]){pattern}(?![a-z0-9+#])"


def _expand_skill_entry(skill):
    if not skill:
        return []

    text = _normalize_skill_value(skill)
    if not text:
        return []

    candidates = []
    text_variants = []
    for candidate in sorted(KNOWN_SKILLS, key=lambda item: len(item), reverse=True):
        normalized_candidate = _normalize_skill_value(candidate)
        if not normalized_candidate:
            continue
        text_variants.append((candidate, normalized_candidate))

    for candidate, normalized_candidate in text_variants:
        if re.search(_skill_pattern(normalized_candidate), text):
            candidates.append(candidate)

    if candidates:
        return candidates

    # Split comma/semicolon-separated phrases like "Python, Java, C++" into actual skill names.
    parts = [part.strip() for part in re.split(r"[,;|&/]+", text) if part.strip()]
    for part in parts:
        cleaned = part.strip(" :()[]{}\n\t")
        if not cleaned or cleaned in GENERIC_SKILL_WORDS:
            continue
        candidates.append(cleaned)

    return sorted(set(candidates), key=lambda item: (item not in KNOWN_SKILLS, item))


def extract_skills(text, required_skills=None):
    cleaned_text = preprocess_text(text or "")
    if not cleaned_text:
        return []

    skills_to_check = required_skills or KNOWN_SKILLS
    found_skills = []

    for skill in skills_to_check:
        if not skill:
            continue

        expanded_skills = _expand_skill_entry(skill)
        if not expanded_skills:
            continue

        for matched_skill in expanded_skills:
            processed_skill = _normalize_skill_value(matched_skill)
            if not processed_skill:
                continue

            pattern = _skill_pattern(processed_skill)
            if pattern and re.search(pattern, cleaned_text, flags=re.IGNORECASE):
                canonical_skill = matched_skill.strip()
                if canonical_skill not in found_skills:
                    found_skills.append(canonical_skill)

    return found_skills