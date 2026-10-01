import re
from collections import Counter

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer, WordNetLemmatizer
    from nltk.tokenize import word_tokenize
except Exception:  # pragma: no cover - dependency guard
    nltk = None
    stopwords = None
    PorterStemmer = None
    WordNetLemmatizer = None
    word_tokenize = None


def ensure_nltk_data():
    if nltk is None:
        return False

    resources = [
        ("tokenizers/punkt", "punkt"),
        ("tokenizers/punkt_tab", "punkt_tab"),
        ("corpora/stopwords", "stopwords"),
        ("corpora/wordnet", "wordnet"),
        ("corpora/omw-1.4", "omw-1.4"),
    ]

    for resource_path, package_name in resources:
        try:
            nltk.data.find(resource_path)
        except LookupError:
            nltk.download(package_name, quiet=True)
    return True


def normalize_text(text):
    if not text:
        return ""

    cleaned = re.sub(r"<[^>]+>", " ", str(text))
    cleaned = cleaned.lower()
    cleaned = cleaned.replace("\xa0", " ")
    cleaned = re.sub(r"[^a-z0-9\s+#./-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def preprocess_text(text, use_stemming=True, use_lemmatization=True):
    normalized = normalize_text(text)
    if not normalized:
        return ""

    if nltk is None or word_tokenize is None or stopwords is None:
        return normalized

    ensure_nltk_data()

    tokens = word_tokenize(normalized)
    stop_words = set(stopwords.words("english"))
    lemmatizer = WordNetLemmatizer()
    stemmer = PorterStemmer()

    processed_tokens = []
    for token in tokens:
        if not token or len(token) <= 1:
            continue
        if token in stop_words:
            continue

        if use_lemmatization:
            token = lemmatizer.lemmatize(token)
        if use_stemming:
            token = stemmer.stem(token)

        if token:
            processed_tokens.append(token)

    return " ".join(processed_tokens)


def extract_keywords(text, limit=25):
    processed = preprocess_text(text)
    if not processed:
        return []

    words = re.findall(r"[a-z0-9+#./-]+", processed)
    counts = Counter(words)
    return [word for word, _ in counts.most_common(limit)]
