import fitz


class EncryptedPdfError(Exception):
    """Raised when a PDF is encrypted and no/wrong password was provided."""
    pass


def extract_text_from_pdf(file_path: str, password: str = "") -> str:
    """Extract text from a PDF file using PyMuPDF."""
    doc = None
    try:
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            if not password or not doc.authenticate(password):
                raise EncryptedPdfError("הקובץ מוגן בסיסמה")
        pages = []
        for i in range(len(doc)):
            page = doc.load_page(i)
            pages.append(page.get_text("text"))
        text = "\n--- PAGE BREAK ---\n".join(pages)
        if len(text) > 50_000:
            raise ValueError("PDF text too large")
        return text
    finally:
        if doc:
            doc.close()
