"""Core pipeline tests; OCR is mocked except for the opt-in installed-engine check."""

from io import BytesIO
import json
import shutil

import pytest
from jsonschema import validate
from PIL import Image

from image_processing import ProcessingError, ProcessingOptions, prepare_document
from image_processing.ocr_engine import extract_text
from image_processing.text_cleaner import clean_text
from image_processing.validator import validate_image


def test_png_jpeg_and_readable_image(monkeypatch, png_bytes, jpeg_bytes):
    monkeypatch.setattr("image_processing.document_processor.extract_text", lambda *_: " Attendance: 85% \r\nMarks: 90 ")
    for data, name, fmt in [(png_bytes, "a.png", "PNG"), (jpeg_bytes, "b.jpg", "JPEG")]:
        result = prepare_document(data, name, "stable-id")
        assert result.source["filename"] == name
        assert result.document_id == "stable-id"
        assert result.metadata["image_format"] == fmt
        assert result.text == "Attendance: 85%\nMarks: 90"
        assert result.warnings == []


def test_schema_and_json_serializable(monkeypatch, png_bytes):
    monkeypatch.setattr("image_processing.document_processor.extract_text", lambda *_: "sample")
    result = prepare_document(png_bytes, "sample.png")
    instance = json.loads(json.dumps(result.to_dict()))
    schema = json.loads(open("contracts/prepared_document.schema.json", encoding="utf-8").read())
    validate(instance=instance, schema=schema)
    assert instance["document_id"].startswith("doc-")


def test_empty_ocr_warning(monkeypatch, png_bytes):
    monkeypatch.setattr("image_processing.document_processor.extract_text", lambda *_: " \n\r\n ")
    result = prepare_document(png_bytes, "blank.png")
    assert result.text == ""
    assert result.warnings == [{"code": "NO_TEXT_DETECTED", "message": "No readable text was detected in the image."}]


def test_preprocessing_can_be_disabled(monkeypatch, png_bytes):
    monkeypatch.setattr("image_processing.document_processor.extract_text", lambda *_: "ok")
    result = prepare_document(png_bytes, "x.png", options=ProcessingOptions(preprocess=False))
    assert result.metadata["preprocessing_operations"] == []


def test_poor_contrast_rotated_upload_dimensions_and_cleanup(monkeypatch):
    image = Image.new("L", (60, 20), 230)
    # expand=True makes the uploaded raster bounds swap; this does not test auto-rotation.
    image = image.rotate(90, expand=True)
    out = BytesIO(); image.save(out, format="PNG")
    monkeypatch.setattr("image_processing.document_processor.extract_text", lambda *_: "A, 42%\n\n\nB")
    result = prepare_document(out.getvalue(), "rotated.png")
    assert result.text == "A, 42%\n\nB"
    assert result.metadata["image_width"] == 20
    assert result.metadata["image_height"] == 60
    assert "autocontrast" in result.metadata["preprocessing_operations"]


@pytest.mark.parametrize("data,name,limit,code", [
    (b"", "empty.png", 100, "EMPTY_INPUT"),
    (b"not-an-image", "bad.png", 100, "INVALID_IMAGE"),
    (b"data", "file.gif", 100, "UNSUPPORTED_FILE_FORMAT"),
    (b"x" * 101, "large.png", 100, "FILE_TOO_LARGE"),
])
def test_validation_failures(data, name, limit, code):
    with pytest.raises(ProcessingError) as caught:
        validate_image(data, name, limit)
    assert caught.value.code == code
    assert caught.value.message


def test_extension_content_mismatch(png_bytes):
    with pytest.raises(ProcessingError, match="extension"):
        validate_image(png_bytes, "looks.jpg", 10000)


def test_text_cleanup_preserves_punctuation_and_numbers():
    assert clean_text("  Amount: $12.50\r\n\r\n\r\nStatus!  ") == "Amount: $12.50\n\nStatus!"


def test_ocr_unavailable(monkeypatch):
    import pytesseract
    monkeypatch.setattr(pytesseract, "get_tesseract_version", lambda: (_ for _ in ()).throw(pytesseract.TesseractNotFoundError()))
    with pytest.raises(ProcessingError) as caught:
        extract_text(Image.new("RGB", (5, 5)))
    assert caught.value.code == "OCR_ENGINE_UNAVAILABLE"


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="requires installed Tesseract executable")
def test_real_ocr_available(png_bytes):
    result = prepare_document(png_bytes, "sample.png")
    assert isinstance(result.text, str)
