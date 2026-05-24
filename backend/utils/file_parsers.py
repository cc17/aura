from __future__ import annotations

import io

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".doc"}

# Magic byte signatures for binary formats
_PDF_MAGIC = b"%PDF"
_DOCX_MAGIC = b"PK\x03\x04"  # ZIP container (DOCX/XLSX/PPTX)


def extract_text(filename: str, data: bytes) -> str:
    """Extract plain text from an uploaded file.

    Args:
        filename: Original filename (used to determine format).
        data: Raw file bytes (caller must enforce MAX_FILE_SIZE before calling).

    Returns:
        Extracted text content.

    Raises:
        ValueError: If the file is too large, format is unsupported, or magic bytes mismatch.
    """
    if len(data) > MAX_FILE_SIZE:
        raise ValueError(f"File too large ({len(data)} bytes). Maximum is {MAX_FILE_SIZE} bytes.")

    ext = _get_extension(filename)

    if ext in (".txt", ".md"):
        return data.decode("utf-8", errors="replace")
    elif ext == ".pdf":
        if not data.startswith(_PDF_MAGIC):
            raise ValueError("File does not appear to be a valid PDF.")
        return _extract_pdf(data)
    elif ext in (".docx", ".doc"):
        if not data.startswith(_DOCX_MAGIC):
            raise ValueError("File does not appear to be a valid DOCX.")
        return _extract_docx(data)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def _get_extension(filename: str) -> str:
    dot = filename.rfind(".")
    if dot == -1:
        return ""
    return filename[dot:].lower()


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def _extract_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs)
