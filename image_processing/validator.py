"""Input format, signature, size, dimension, and image readability checks."""

from io import BytesIO
from PIL import Image, UnidentifiedImageError

from .models import ProcessingError

SUPPORTED_EXTENSIONS = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG"}

# Magic byte signatures
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC_PREFIX = b"\xff\xd8\xff"

MIN_DIMENSION = 10
MAX_DIMENSION = 10000
MAX_TOTAL_PIXELS = 25_000_000  # 25 MP safe limit


def validate_image(data: bytes, filename: str, max_bytes: int) -> tuple[Image.Image, str]:
    """Validate uploaded bytes, signatures, dimensions, and return a decoded Pillow image and format."""
    if not data:
        raise ProcessingError("EMPTY_INPUT", "The uploaded file is empty.", 400)

    if len(data) > max_bytes:
        raise ProcessingError(
            "FILE_TOO_LARGE",
            "The file exceeds the configured upload size limit.",
            413,
            {"max_bytes": max_bytes, "actual_bytes": len(data)},
        )

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    expected = SUPPORTED_EXTENSIONS.get(ext)
    if not expected:
        raise ProcessingError("UNSUPPORTED_FILE_FORMAT", "Only PNG and JPEG images are supported.", 415)

    # Magic byte signature check
    if expected == "PNG" and not data.startswith(PNG_MAGIC):
        raise ProcessingError(
            "INVALID_IMAGE",
            "The file header does not match the PNG file signature.",
            400,
        )
    elif expected == "JPEG" and not data.startswith(JPEG_MAGIC_PREFIX):
        raise ProcessingError(
            "INVALID_IMAGE",
            "The file header does not match the JPEG file signature.",
            400,
        )

    try:
        image = Image.open(BytesIO(data))
        # Ensure image is completely loaded to detect truncated data
        image.load()
    except Image.DecompressionBombError:
        raise ProcessingError(
            "FILE_TOO_LARGE",
            "The image dimensions exceed the safe decompression limit.",
            413,
        ) from None
    except (UnidentifiedImageError, OSError, ValueError):
        raise ProcessingError("INVALID_IMAGE", "The uploaded file is not a readable image.", 400) from None

    # Dimension validation
    width, height = image.size
    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        raise ProcessingError(
            "INVALID_IMAGE",
            f"Image dimensions ({width}x{height}) are too small to contain a readable document (minimum {MIN_DIMENSION}x{MIN_DIMENSION} pixels).",
            400,
            {"width": width, "height": height, "min_dimension": MIN_DIMENSION},
        )

    if width > MAX_DIMENSION or height > MAX_DIMENSION or (width * height) > MAX_TOTAL_PIXELS:
        raise ProcessingError(
            "FILE_TOO_LARGE",
            f"Image dimensions ({width}x{height}) exceed the maximum allowable size ({MAX_DIMENSION}x{MAX_DIMENSION} pixels).",
            413,
            {"width": width, "height": height, "max_dimension": MAX_DIMENSION},
        )

    actual = (image.format or "").upper()
    if actual not in {"PNG", "JPEG"} or actual != expected:
        raise ProcessingError("INVALID_IMAGE", "The file extension does not match a supported image format.", 400)

    return image, actual
