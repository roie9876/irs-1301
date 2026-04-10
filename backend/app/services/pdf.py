import fitz


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file using PyMuPDF."""
    doc = None
    try:
        doc = fitz.open(file_path)
        pages = []
        for i in range(len(doc)):
            page = doc.load_page(i)
            pages.append(page.get_text("text"))
        text = "\n--- PAGE BREAK ---\n".join(pages)
        if len(text) > 15_000:
            raise ValueError("PDF text too large — likely not a Form 106")
        return text
    finally:
        if doc:
            doc.close()
