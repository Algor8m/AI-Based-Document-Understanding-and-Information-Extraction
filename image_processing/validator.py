"""Input format, size, and image readability checks."""

from io import BytesIO
from PIL import Image, UnidentifiedImageError

from .models import ProcessingError

SUPPORTED_EXTENSIONS = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG"}


def validate_image(data: bytes, filename: str, max_bytes: int) -> tuple[Image.Image, str]:
    """Validate uploaded bytes and return a decoded Pillow image and format."""
    if not data:
        raise ProcessingError("EMPTY_INPUT", "The uploaded file is empty.", 400)
    if len(data) > max_bytes:
        raise ProcessingError("FILE_TOO_LARGE", "The file exceeds the configured upload size limit.", 413,
                              {"max_bytes": max_bytes})
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    expected = SUPPORTED_EXTENSIONS.get(ext)
    if not expected:
        raise ProcessingError("UNSUPPORTED_FILE_FORMAT", "Only PNG and JPEG images are supported.", 415)
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise ProcessingError("INVALID_IMAGE", "The uploaded file is not a readable image.", 400) from None
    actual = (image.format or "").upper()
    if actual not in {"PNG", "JPEG"} or actual != expected:
        raise ProcessingError("INVALID_IMAGE", "The file extension does not match a supported image format.", 400)
    return image, actual
