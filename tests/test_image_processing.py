"""Unit tests for the image processing module."""

import io
import unittest
from PIL import Image, ImageDraw

from image_processing import ProcessingError, ProcessingOptions, prepare_document
from image_processing.validator import validate_image
from image_processing.preprocessor import preprocess_image
from image_processing.text_cleaner import clean_text


class TestValidator(unittest.TestCase):

    def test_empty_bytes_rejected(self):
        with self.assertRaises(ProcessingError) as ctx:
            validate_image(b"", "doc.png", 1024 * 1024)
        self.assertEqual(ctx.exception.code, "EMPTY_INPUT")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_oversized_file_rejected(self):
        with self.assertRaises(ProcessingError) as ctx:
            validate_image(b"x" * 100, "doc.png", 50)
        self.assertEqual(ctx.exception.code, "FILE_TOO_LARGE")
        self.assertEqual(ctx.exception.status_code, 413)

    def test_unsupported_extension_rejected(self):
        with self.assertRaises(ProcessingError) as ctx:
            validate_image(b"some content", "doc.pdf", 1024 * 1024)
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_FILE_FORMAT")
        self.assertEqual(ctx.exception.status_code, 415)

    def test_corrupt_image_rejected(self):
        with self.assertRaises(ProcessingError) as ctx:
            validate_image(b"not an image data", "doc.png", 1024 * 1024)
        self.assertEqual(ctx.exception.code, "INVALID_IMAGE")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_extension_mismatch_rejected(self):
        # Create a real JPEG but name it .png
        img = Image.new("RGB", (100, 100), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        jpeg_bytes = buf.getvalue()

        with self.assertRaises(ProcessingError) as ctx:
            validate_image(jpeg_bytes, "doc.png", 1024 * 1024)
        self.assertEqual(ctx.exception.code, "INVALID_IMAGE")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_valid_png_and_jpeg_accepted(self):
        # PNG
        img_png = Image.new("RGB", (50, 50), color="red")
        buf_png = io.BytesIO()
        img_png.save(buf_png, format="PNG")
        image, fmt = validate_image(buf_png.getvalue(), "test.png", 1024 * 1024)
        self.assertEqual(fmt, "PNG")
        self.assertEqual(image.size, (50, 50))

        # JPEG
        img_jpg = Image.new("RGB", (50, 50), color="green")
        buf_jpg = io.BytesIO()
        img_jpg.save(buf_jpg, format="JPEG")
        image, fmt = validate_image(buf_jpg.getvalue(), "test.jpg", 1024 * 1024)
        self.assertEqual(fmt, "JPEG")
        self.assertEqual(image.size, (50, 50))


class TestPreprocessor(unittest.TestCase):

    def test_preprocessor_converts_to_grayscale_and_upscales_small_image(self):
        img = Image.new("RGB", (100, 100), color="yellow")
        processed, ops = preprocess_image(img, enabled=True)
        self.assertEqual(processed.mode, "L")
        self.assertIn("grayscale", ops)
        self.assertIn("upscale", ops)
        self.assertGreater(processed.width, 100)

    def test_preprocessor_disabled(self):
        img = Image.new("RGB", (100, 100), color="yellow")
        processed, ops = preprocess_image(img, enabled=False)
        self.assertEqual(processed.mode, "RGB")
        self.assertEqual(ops, [])


class TestTextCleaner(unittest.TestCase):

    def test_clean_text_normalizes_whitespace_and_newlines(self):
        dirty = "\r\n  Line 1   \r\n\r\n\r\n\r\n   Line 2   \r\n"
        cleaned = clean_text(dirty)
        self.assertEqual(cleaned, "Line 1\n\nLine 2")

    def test_clean_text_empty(self):
        self.assertEqual(clean_text("   \r\n   \n   "), "")


class TestDocumentProcessor(unittest.TestCase):

    def test_prepare_blank_image_returns_warning(self):
        img = Image.new("RGB", (200, 200), color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        result = prepare_document(buf.getvalue(), "blank.png", document_id="doc-blank-001")
        self.assertEqual(result.document_id, "doc-blank-001")
        self.assertEqual(result.text, "")
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(result.warnings[0]["code"], "NO_TEXT_DETECTED")
        self.assertEqual(result.schema_version, "1.0")
        self.assertEqual(result.metadata["image_format"], "PNG")
        self.assertGreaterEqual(result.metadata["processing_duration_ms"], 0)

    def test_prepare_readable_image(self):
        img = Image.new("RGB", (600, 200), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((30, 30), "Hello Document 123", fill="black")
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        result = prepare_document(buf.getvalue(), "readable.png")
        self.assertIn("Hello", result.text)
        self.assertIn("Document", result.text)
        self.assertEqual(result.warnings, [])


if __name__ == "__main__":
    unittest.main()
