def extract_text_from_pdf(file_path: str) -> str:
    from PyPDF2 import PdfReader
    reader = PdfReader(file_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_text_from_docx(file_path: str) -> str:
    from docx import Document
    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text(file_path: str, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    elif filename.lower().endswith((".docx", ".doc")):
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {filename}")
