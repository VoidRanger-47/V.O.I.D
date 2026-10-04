# pdf_utils.py
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

def pdf_to_text(pdf_path, ocr_dpi=300):
    """
    Extract text from PDF. Try text-layer first (pdfplumber), if none found use OCR.
    Returns a single big string.
    """
    text_parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception:
        # if pdfplumber fails, we'll fallback to OCR below
        pass

    joined = "\n".join(text_parts).strip()
    if joined:
        return joined

    # fallback to OCR if no text found
    images = convert_from_path(pdf_path, dpi=ocr_dpi)
    ocr_text = []
    for img in images:
        try:
            ocr_text.append(pytesseract.image_to_string(img))
        except Exception:
            # if pytesseract fails on this page, ignore it
            pass
    return "\n".join(ocr_text)

def save_text(text, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
