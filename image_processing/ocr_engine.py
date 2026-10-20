"""Tesseract OCR adapter, kept separate from the API and pipeline."""

import os
from pathlib import Path
from PIL import Image

from .models import ProcessingError


def extract_text(image: Image.Image, language: str = "eng") -> str:
    """Extract text with Tesseract; report a structured error if unavailable."""
    try:
        import pytesseract
    except ImportError:
        raise ProcessingError("OCR_ENGINE_UNAVAILABLE", "The pytesseract package is unavailable.", 503) from None
    try:
        executable = os.getenv("TESSERACT_CMD")
        if executable:
            pytesseract.pytesseract.tesseract_cmd = str(Path(executable))
        # Version check distinguishes a missing executable from an empty OCR result.
        pytesseract.get_tesseract_version()
        return pytesseract.image_to_string(image, lang=language, config="--psm 6")
    except pytesseract.TesseractNotFoundError:
        raise ProcessingError("OCR_ENGINE_UNAVAILABLE", "Tesseract OCR is unavailable. Install it and configure TESSERACT_CMD.", 503) from None
    except pytesseract.TesseractError as exc:
        raise ProcessingError("OCR_CONFIGURATION_ERROR", "Tesseract could not process this image with the current configuration.", 422) from None
