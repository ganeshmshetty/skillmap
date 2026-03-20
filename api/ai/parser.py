"""
Text extraction from file bytes. Member B can call these before passing text to analyze().
"""
import io

def parse_pdf(file_bytes: bytes) -> str:
    import pdfplumber
    text = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text.append(extracted)
    return "\n".join(text)

def parse_docx(file_bytes: bytes) -> str:
    import docx
    doc = docx.Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

def parse_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore")

def extract_text(file_bytes: bytes, filename: str) -> str:
    """Auto-detect format and extract text."""
    fname = filename.lower()
    if fname.endswith(".pdf"):
        return parse_pdf(file_bytes)
    elif fname.endswith(".docx"):
        return parse_docx(file_bytes)
    else:
        return parse_txt(file_bytes)