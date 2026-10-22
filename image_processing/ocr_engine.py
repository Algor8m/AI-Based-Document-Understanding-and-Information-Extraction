"""Tesseract OCR adapter with confidence scoring, fallback modes, and structured error handling."""

import logging
import os
from pathlib import Path
from PIL import Image

from .models import ProcessingError

logger = logging.getLogger(__name__)


def _configure_tesseract(pytesseract_module) -> None:
    """Ensure the Tesseract executable path is configured."""
    executable = os.getenv("TESSERACT_CMD")
    if executable:
        pytesseract_module.pytesseract.tesseract_cmd = str(Path(executable))
    elif os.name == "nt":
        default_win_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if default_win_path.exists():
            pytesseract_module.pytesseract.tesseract_cmd = str(default_win_path)

    # Verify executable availability
    pytesseract_module.get_tesseract_version()


def extract_text_with_confidence(
    image: Image.Image,
    language: str = "eng",
    psm: int = 3,
) -> tuple[str, float, int]:
    """Extract text along with empirical OCR word confidence and word count.

    Returns:
        tuple of (cleaned_raw_text, average_word_confidence_0_to_100, word_count)
    """
    try:
        import pytesseract
    except ImportError:
        raise ProcessingError(
            "OCR_ENGINE_UNAVAILABLE",
            "The pytesseract package is unavailable.",
            503,
        ) from None

    try:
        _configure_tesseract(pytesseract)

        # Primary extraction using image_to_data for word-level confidence and reading order
        data = pytesseract.image_to_data(
            image,
            lang=language,
            config=f"--psm {psm}",
            output_type=pytesseract.Output.DICT,
        )

        valid_confs = []
        words = []
        for word, conf in zip(data.get("text", []), data.get("conf", [])):
            try:
                c = int(conf)
            except (ValueError, TypeError):
                continue
            if c >= 0 and str(word).strip():
                valid_confs.append(c)
                words.append(str(word).strip())

        raw_text = pytesseract.image_to_string(
            image,
            lang=language,
            config=f"--psm {psm}",
        )

        # Fallback: if PSM 3 produced no text or empty words on a non-trivial image, try PSM 6
        if not raw_text.strip() and psm == 3:
            logger.debug("Primary PSM 3 produced empty text; attempting PSM 6 fallback")
            alt_data = pytesseract.image_to_data(
                image,
                lang=language,
                config="--psm 6",
                output_type=pytesseract.Output.DICT,
            )
            alt_confs = []
            alt_words = []
            for word, conf in zip(alt_data.get("text", []), alt_data.get("conf", [])):
                try:
                    c = int(conf)
                except (ValueError, TypeError):
                    continue
                if c >= 0 and str(word).strip():
                    alt_confs.append(c)
                    alt_words.append(str(word).strip())

            alt_text = pytesseract.image_to_string(
                image,
                lang=language,
                config="--psm 6",
            )
            if alt_text.strip():
                raw_text = alt_text
                valid_confs = alt_confs
                words = alt_words

        mean_confidence = round(sum(valid_confs) / len(valid_confs), 2) if valid_confs else 0.0
        return raw_text, mean_confidence, len(words)

    except pytesseract.TesseractNotFoundError:
        raise ProcessingError(
            "OCR_ENGINE_UNAVAILABLE",
            "Tesseract OCR is unavailable. Install it and configure TESSERACT_CMD.",
            503,
        ) from None

    except pytesseract.TesseractError as exc:
        raise ProcessingError(
            "OCR_CONFIGURATION_ERROR",
            f"Tesseract failed during execution: {str(exc).strip()}",
            422,
        ) from None


def extract_text(image: Image.Image, language: str = "eng") -> str:
    """Extract text with Tesseract; report a structured error if unavailable."""
    text, _, _ = extract_text_with_confidence(image, language=language)
    return text
