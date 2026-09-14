"""Tesseract OCR engine wrapper.

Isolates every third-party OCR/image dependency (pytesseract, Pillow,
OpenCV, PyMuPDF) behind one function, `run_ocr`, so the rest of the app
never imports them directly and OCR failures never crash the API — they
come back as a `OCRResult` with `engine_available=False` and an error
message, which `document_service` turns into `status=HUMAN_REVIEW`.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass

logger = logging.getLogger("app.ocr")


@dataclass
class OCRResult:
    text: str
    mean_confidence: float | None  # 0-100, Tesseract's own per-word confidence average
    engine_available: bool
    error: str | None = None


def is_tesseract_available() -> bool:
    """Cheap check for the integrations status panel (PROMPT 3 §44) —
    does not run OCR, just confirms the `tesseract` binary is reachable."""
    try:
        import pytesseract

        from app.core.config import get_settings

        tesseract_cmd = get_settings().tesseract_cmd
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _preprocess_image(pil_image):
    """Grayscale + threshold to improve OCR accuracy on photographed receipts.

    Falls back to the untouched image if OpenCV is unavailable or the
    conversion fails — preprocessing is a quality improvement, not a
    requirement for OCR to run.
    """
    try:
        import cv2
        import numpy as np

        array = np.array(pil_image.convert("RGB"))
        gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        from PIL import Image

        return Image.fromarray(thresh)
    except Exception:  # pragma: no cover - best-effort enhancement only
        logger.debug("OCR preprocessing skipped", exc_info=True)
        return pil_image


def _ocr_single_image(pil_image, language: str) -> tuple[str, float | None]:
    import pytesseract

    processed = _preprocess_image(pil_image)
    text = pytesseract.image_to_string(processed, lang=language)

    mean_confidence: float | None = None
    try:
        data = pytesseract.image_to_data(processed, lang=language, output_type=pytesseract.Output.DICT)
        confidences = [float(c) for c in data.get("conf", []) if c not in ("-1", -1)]
        if confidences:
            mean_confidence = sum(confidences) / len(confidences)
    except Exception:  # pragma: no cover - confidence is a bonus signal
        logger.debug("Could not compute OCR confidence", exc_info=True)

    return text, mean_confidence


def _images_from_pdf(content: bytes):
    import fitz  # PyMuPDF

    images = []
    with fitz.open(stream=content, filetype="pdf") as doc:
        for page in doc:
            pixmap = page.get_pixmap(dpi=200)
            images.append(pixmap.tobytes("png"))
    from PIL import Image

    return [Image.open(io.BytesIO(png_bytes)) for png_bytes in images]


def run_ocr(content: bytes, mime_type: str, *, language: str = "por") -> OCRResult:
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - dependency always declared in requirements
        return OCRResult(text="", mean_confidence=None, engine_available=False, error=str(exc))

    from app.core.config import get_settings

    tesseract_cmd = get_settings().tesseract_cmd
    if tesseract_cmd:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    try:
        if mime_type == "application/pdf":
            pages = _images_from_pdf(content)
        else:
            pages = [Image.open(io.BytesIO(content))]
    except Exception as exc:
        logger.warning("Failed to decode document for OCR: %s", exc)
        return OCRResult(text="", mean_confidence=None, engine_available=True, error=str(exc))

    texts: list[str] = []
    confidences: list[float] = []
    try:
        for page_image in pages:
            text, confidence = _ocr_single_image(page_image, language)
            texts.append(text)
            if confidence is not None:
                confidences.append(confidence)
    except Exception as exc:
        # Covers pytesseract.TesseractNotFoundError and any other OCR failure.
        logger.warning("OCR engine unavailable or failed: %s", exc)
        return OCRResult(text="", mean_confidence=None, engine_available=False, error=str(exc))

    full_text = "\n".join(t for t in texts if t)
    mean_confidence = sum(confidences) / len(confidences) if confidences else None
    return OCRResult(text=full_text, mean_confidence=mean_confidence, engine_available=True, error=None)
