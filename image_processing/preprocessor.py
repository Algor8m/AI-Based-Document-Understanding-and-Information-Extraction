"""Image preprocessing for improved OCR accuracy."""

from typing import Any
from PIL import Image, ImageEnhance, ImageOps

# Images smaller than this are enlarged before OCR.
MIN_IMAGE_DIMENSION = 1000
DEFAULT_SCALE = 3


def preprocess_image(
    image: Image.Image,
    enabled: bool = True,
    return_stages: bool = False,
) -> tuple[Image.Image, list[str]] | tuple[Image.Image, list[str], list[dict[str, Any]]]:
    """Prepare an image for OCR using conservative enhancement.

    If return_stages is True, returns (processed_image, operation_names, intermediate_stages).
    Otherwise returns (processed_image, operation_names).
    """
    stages: list[dict[str, Any]] = [
        {
            "stage": "original",
            "title": "Original Image",
            "description": "Uploaded image as received before any processing",
            "dimensions": [image.width, image.height],
            "image": image.copy(),
            "is_ocr_input": not enabled,
        }
    ]

    if not enabled:
        if return_stages:
            return image.copy(), [], stages
        return image.copy(), []

    result = ImageOps.exif_transpose(image).copy()
    operations = ["exif_orientation"]
    stages.append({
        "stage": "exif_orientation",
        "title": "EXIF Orientation",
        "description": "Normalized rotation based on image EXIF metadata",
        "dimensions": [result.width, result.height],
        "image": result.copy(),
        "is_ocr_input": False,
    })

    # Convert to grayscale to simplify text recognition.
    if result.mode != "L":
        result = ImageOps.grayscale(result)
        operations.append("grayscale")
        stages.append({
            "stage": "grayscale",
            "title": "Grayscale Conversion",
            "description": "Single-channel intensity mapping for character edge isolation",
            "dimensions": [result.width, result.height],
            "image": result.copy(),
            "is_ocr_input": False,
        })

    # Upscale small images to improve recognition of fine text.
    longest_dimension = max(result.size)

    if longest_dimension < MIN_IMAGE_DIMENSION:
        scale = min(
            DEFAULT_SCALE,
            MIN_IMAGE_DIMENSION / longest_dimension,
        )
        new_size = (
            max(1, round(result.width * scale)),
            max(1, round(result.height * scale)),
        )
        result = result.resize(new_size, Image.Resampling.LANCZOS)
        operations.append("upscale")
        stages.append({
            "stage": "upscale",
            "title": "Bicubic / Lanczos Upscaling",
            "description": f"Resized by {round(scale, 2)}x to reach {MIN_IMAGE_DIMENSION}px minimum dimension for OCR",
            "dimensions": [result.width, result.height],
            "image": result.copy(),
            "is_ocr_input": False,
        })

    # Improve contrast without applying a destructive denoising filter.
    result = ImageOps.autocontrast(result)
    operations.append("autocontrast")
    stages.append({
        "stage": "autocontrast",
        "title": "Autocontrast Normalization",
        "description": "Histogram stretch to maximize luminance dynamic range",
        "dimensions": [result.width, result.height],
        "image": result.copy(),
        "is_ocr_input": False,
    })

    result = ImageEnhance.Contrast(result).enhance(1.15)
    operations.append("contrast_adjustment")
    stages.append({
        "stage": "contrast_adjustment",
        "title": "Contrast Enhancement",
        "description": "Subtle 1.15x contrast boost to sharpen character boundaries",
        "dimensions": [result.width, result.height],
        "image": result.copy(),
        "is_ocr_input": False,
    })

    # Mark the final stage as the input to OCR
    for s in stages:
        s["is_ocr_input"] = False
    stages[-1]["is_ocr_input"] = True

    if return_stages:
        return result, operations, stages
    return result, operations
