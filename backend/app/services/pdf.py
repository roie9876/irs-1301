import subprocess
import tempfile
import os

import fitz


class EncryptedPdfError(Exception):
    """Raised when a PDF is encrypted and no/wrong password was provided."""
    pass


def _is_garbled(text: str) -> bool:
    """Detect garbled text from PDFs with broken font encoding.

    Heuristics:
    1. Most characters are non-printable control chars (custom font encoding).
    2. Most lines are 1-3 chars (per-character positioning).
    """
    if len(text) > 20:
        printable = sum(1 for ch in text if ch.isprintable() or ch in '\n\r\t')
        if printable / len(text) < 0.5:
            return True
    lines = [line for line in text.split("\n") if line.strip()]
    if len(lines) < 20:
        return False
    short_lines = sum(1 for line in lines if len(line.strip()) <= 3)
    return short_lines / len(lines) > 0.5


def _ocr_page(page) -> str:
    """Render a PDF page to image and OCR with tesseract."""
    pix = page.get_pixmap(dpi=300)
    img_path = tempfile.mktemp(suffix=".png")
    try:
        pix.save(img_path)
        result = subprocess.run(
            ["tesseract", img_path, "stdout", "-l", "heb+eng", "--psm", "6"],
            capture_output=True, text=True, timeout=60,
        )
        return result.stdout
    finally:
        if os.path.exists(img_path):
            os.unlink(img_path)


def extract_text_from_pdf(file_path: str, password: str = "") -> str:
    """Extract text from a PDF file using PyMuPDF, with OCR fallback."""
    doc = None
    try:
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            if not password or not doc.authenticate(password):
                raise EncryptedPdfError("הקובץ מוגן בסיסמה")

        # First try native text extraction
        pages = []
        for i in range(len(doc)):
            page = doc.load_page(i)
            pages.append(page.get_text("text"))
        text = "\n--- PAGE BREAK ---\n".join(pages)

        # If text looks garbled (per-character positioning) or has
        # almost no real content (scanned PDF), try OCR
        content = text.replace("--- PAGE BREAK ---", "").strip()
        if _is_garbled(text) or len(content) < 30:
            ocr_pages = []
            for i in range(len(doc)):
                page = doc.load_page(i)
                ocr_pages.append(_ocr_page(page))
            text = "\n--- PAGE BREAK ---\n".join(ocr_pages)

        if len(text) > 50_000:
            raise ValueError("PDF text too large")
        return text
    finally:
        if doc:
            doc.close()


def render_pdf_page_to_image(file_path: str, page_num: int = 0) -> bytes:
    """Render a PDF page as a PNG image in memory."""
    doc = fitz.open(file_path)
    try:
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=200)
        return pix.tobytes("png")
    finally:
        doc.close()
