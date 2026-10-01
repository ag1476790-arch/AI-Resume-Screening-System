import os

import pdfplumber
import fitz


def extract_text(pdf_path):
    """
    Extract text from a PDF resume with fallback support.
    """
    if not pdf_path or not os.path.exists(pdf_path):
        return ""

    text_parts = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(layout=False) or page.extract_text(x_tolerance=1, y_tolerance=1)
                if page_text and page_text.strip():
                    text_parts.append(page_text)
    except Exception as e:
        print(f"pdfplumber extraction warning: {e}")

    extracted_text = "\n".join(text_parts).strip()
    if extracted_text:
        return extracted_text.lower()

    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                page_text = page.get_text("text")
                if page_text and page_text.strip():
                    text_parts.append(page_text)
    except Exception as e:
        print(f"PyMuPDF text extraction warning: {e}")

    extracted_text = "\n".join(text_parts).strip()
    if extracted_text:
        return extracted_text.lower()

    return ""