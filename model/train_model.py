import pandas as pd
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# -----------------------------
# Load Dataset
# -----------------------------

df = pd.read_csv("../dataset/resume_dataset.csv")

print("Dataset Loaded Successfully!")
print(df.head())

# -----------------------------
# Build TF-IDF Vocabulary
# -----------------------------

all_text = list(df["Resume"]) + list(df["Job_Description"])

vectorizer = TfidfVectorizer(stop_words="english")

vectorizer.fit(all_text)

print("\nTF-IDF Vocabulary Created Successfully!")

# -----------------------------
# Save Vectorizer
# -----------------------------

joblib.dump(vectorizer, "vectorizer.pkl")

print("\nVectorizer Saved Successfully!")

# -----------------------------
# Test Cosine Similarity
# -----------------------------

print("\nSample Similarity Scores")
print("-" * 40)

for i in range(len(df)):

    resume_vector = vectorizer.transform([df.loc[i, "Resume"]])

    job_vector = vectorizer.transform([df.loc[i, "Job_Description"]])

    similarity = cosine_similarity(
        resume_vector,
        job_vector
    )[0][0]

    print(f"Applicant {i+1}")
    print(f"Similarity : {similarity*100:.2f}%")
    print("-" * 40)