"""Public, framework-independent document preparation pipeline."""

from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4

from PIL import Image

from .models import PreparedDocumentResult, ProcessingError
from .ocr_engine import extract_text
from .preprocessor import preprocess_image
from .text_cleaner import clean_text
from .validator import validate_image


@dataclass
class ProcessingOptions:
    """Options for one processing request."""
    max_file_size_bytes: int = 10 * 1024 * 1024
    preprocess: bool = True
    language: str = "eng"


def prepare_document(input_data: bytes, filename: str, document_id: str | None = None,
                     options: ProcessingOptions | None = None) -> PreparedDocumentResult:
    """Validate, preprocess, OCR, and package an image without starting a server."""
    opts = options or ProcessingOptions()
    started = perf_counter()
    original, image_format = validate_image(input_data, filename, opts.max_file_size_bytes)
    width, height = original.size
    try:
        image, operations = preprocess_image(original, opts.preprocess)
    except Exception:
        raise ProcessingError("PREPROCESSING_FAILED", "The image could not be prepared for OCR.", 500) from None
    text = clean_text(extract_text(image, opts.language))
    warnings: list[dict[str, str]] = []
    if not text:
        warnings.append({"code": "NO_TEXT_DETECTED", "message": "No readable text was detected in the image."})
    return PreparedDocumentResult(
        schema_version="1.0", document_id=document_id or f"doc-{uuid4()}",
        source={"type": "image", "filename": filename}, text=text,
        metadata={"page_count": 1, "image_width": width, "image_height": height,
                  "image_format": image_format, "ocr_engine": "tesseract",
                  "preprocessing_operations": operations,
                  "processing_duration_ms": round((perf_counter() - started) * 1000, 2)},
        warnings=warnings,
    )
