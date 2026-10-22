"""Public, framework-independent document preparation pipeline."""

from dataclasses import dataclass
import logging
from time import perf_counter
from uuid import uuid4

from PIL import Image

from .models import PreparedDocumentResult, ProcessingError
from .ocr_engine import extract_text_with_confidence
from .preprocessor import preprocess_image
from .text_cleaner import clean_text
from .validator import validate_image

logger = logging.getLogger(__name__)


@dataclass
class ProcessingOptions:
    """Options for one processing request."""
    max_file_size_bytes: int = 10 * 1024 * 1024
    preprocess: bool = True
    language: str = "eng"
    return_stages: bool = False


def prepare_document(
    input_data: bytes,
    filename: str,
    document_id: str | None = None,
    options: ProcessingOptions | None = None,
) -> PreparedDocumentResult:
    """Validate, preprocess, OCR, and package an image without starting a server."""
    opts = options or ProcessingOptions()
    started = perf_counter()

    # 1. Validation
    original, image_format = validate_image(input_data, filename, opts.max_file_size_bytes)
    width, height = original.size

    # 2. Preprocessing
    try:
        if opts.return_stages:
            image, operations, intermediate_stages = preprocess_image(
                original, opts.preprocess, return_stages=True
            )
        else:
            image, operations = preprocess_image(original, opts.preprocess, return_stages=False)
            intermediate_stages = []
    except Exception as exc:
        logger.error("Preprocessing failed: %s", exc)
        raise ProcessingError("PREPROCESSING_FAILED", "The image could not be prepared for OCR.", 500) from None

    # 3. OCR extraction with confidence
    raw_text, ocr_confidence, word_count = extract_text_with_confidence(image, opts.language)
    warnings: list[dict[str, str]] = []

    # 4. Fallback check: if preprocessed image yielded no text, check original image
    if not raw_text.strip() and opts.preprocess:
        logger.debug("Preprocessed image yielded empty OCR; attempting original image fallback")
        try:
            alt_text, alt_conf, alt_words = extract_text_with_confidence(original, opts.language)
            if alt_text.strip():
                raw_text = alt_text
                ocr_confidence = alt_conf
                word_count = alt_words
                operations.append("fallback_to_original")
                warnings.append({
                    "code": "PREPROCESSING_FALLBACK",
                    "message": "Preprocessed image yielded no text; successfully recovered text using original image.",
                })
        except Exception as exc:
            logger.debug("Fallback to original image encountered: %s", exc)

    # 5. Text cleaning
    text = clean_text(raw_text)

    # 6. Quality & warning assessment
    if not text:
        warnings.append({
            "code": "NO_TEXT_DETECTED",
            "message": "No readable text was detected in the image.",
        })
    elif ocr_confidence < 40.0:
        warnings.append({
            "code": "LOW_OCR_CONFIDENCE",
            "message": f"Average OCR confidence is low ({ocr_confidence}%). Results may be degraded.",
        })

    clean_id = document_id.strip() if document_id and document_id.strip() else f"doc-{uuid4()}"

    return PreparedDocumentResult(
        schema_version="1.0",
        document_id=clean_id,
        source={"type": "image", "filename": filename},
        text=text,
        metadata={
            "page_count": 1,
            "image_width": width,
            "image_height": height,
            "image_format": image_format,
            "ocr_engine": "tesseract",
            "ocr_confidence": ocr_confidence,
            "word_count": word_count,
            "preprocessing_operations": operations,
            "processing_duration_ms": round((perf_counter() - started) * 1000, 2),
        },
        warnings=warnings,
        intermediate_stages=intermediate_stages,
    )
