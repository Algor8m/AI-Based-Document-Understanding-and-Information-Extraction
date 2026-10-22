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
        raise ProcessingError(
            "OCR_ENGINE_UNAVAILABLE",
            "The pytesseract package is unavailable.",
            503,
        ) from None

    try:
        executable = os.getenv("TESSERACT_CMD")
        if executable:
            pytesseract.pytesseract.tesseract_cmd = str(Path(executable))
        elif os.name == "nt":
            default_win_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
            if default_win_path.exists():
                pytesseract.pytesseract.tesseract_cmd = str(default_win_path)

        # Verify that the Tesseract executable is available.
        pytesseract.get_tesseract_version()

        # PSM 3: automatic page segmentation.
        return pytesseract.image_to_string(
            image,
            lang=language,
            config="--psm 3",
        )

    except pytesseract.TesseractNotFoundError:
        raise ProcessingError(
            "OCR_ENGINE_UNAVAILABLE",
            "Tesseract OCR is unavailable. Install it and configure TESSERACT_CMD.",
            503,
        ) from None

    except pytesseract.TesseractError:
        raise ProcessingError(
            "OCR_CONFIGURATION_ERROR",
            "Tesseract could not process this image with the current configuration.",
            422,
        ) from None
