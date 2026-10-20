"""Optional conservative image preprocessing for OCR."""

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def preprocess_image(image: Image.Image, enabled: bool = True) -> tuple[Image.Image, list[str]]:
    """Apply EXIF orientation and gentle grayscale/contrast cleanup when enabled."""
    if not enabled:
        return image.copy(), []
    result = ImageOps.exif_transpose(image).copy()
    operations = ["exif_orientation"]
    result = ImageOps.grayscale(result)
    result = ImageOps.autocontrast(result)
    result = result.filter(ImageFilter.MedianFilter(size=3))
    result = ImageEnhance.Contrast(result).enhance(1.15)
    operations.extend(["grayscale", "autocontrast", "median_denoise", "contrast_adjustment"])
    return result, operations
