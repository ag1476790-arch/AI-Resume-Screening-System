import re


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


def _skill_pattern(skill):
    tokens = re.findall(r"[a-z0-9+#]+", skill.lower())
    if not tokens:
        return None

    pattern = r"[\s./_-]*".join(re.escape(token) for token in tokens)
    return rf"(?<![a-z0-9]){pattern}(?![a-z0-9+#])"


def extract_skills(text, required_skills=None):
    skills_to_check = required_skills or KNOWN_SKILLS
    found_skills = []

    for skill in skills_to_check:
        if not skill:
            continue

        pattern = _skill_pattern(skill)
        if pattern and re.search(pattern, text or "", flags=re.IGNORECASE):
            found_skills.append(skill)

    return found_skills