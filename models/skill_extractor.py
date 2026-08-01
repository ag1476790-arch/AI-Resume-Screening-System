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


def extract_skills(text):

    text = text.lower()

    found_skills = []

    for skill in KNOWN_SKILLS:

        if skill in text:

            found_skills.append(skill)

    return found_skills