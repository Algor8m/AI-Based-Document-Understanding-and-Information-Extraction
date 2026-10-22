"""Image preprocessing for improved OCR accuracy, orientation handling, and deskewing."""

import logging
from typing import Any
from PIL import Image, ImageEnhance, ImageOps

logger = logging.getLogger(__name__)

# Images smaller than this are enlarged before OCR.
MIN_IMAGE_DIMENSION = 1000
DEFAULT_SCALE = 3


def estimate_skew_angle(image: Image.Image) -> int:
    """Estimate skew angle (-15 to 15 degrees) using projection profile variance.

    Returns the correction angle in degrees (0 if document is upright or variance is negligible).
    """
    gray = image if image.mode == "L" else image.convert("L")
    w, h = gray.size
    if w < 50 or h < 50:
        return 0

    # Downsample thumbnail for fast horizontal projection variance calculation
    target_w = 200
    scale = target_w / w
    target_h = max(20, int(h * scale))
    thumb = gray.resize((target_w, target_h), Image.Resampling.NEAREST)
    tw, th = thumb.size

    best_angle = 0
    base_var = -1.0
    best_var = -1.0

    for a in range(-15, 16):
        rot = thumb.rotate(a, resample=Image.Resampling.NEAREST, fillcolor=255)
        raw = rot.tobytes()
        row_sums = [sum(raw[y * tw : (y + 1) * tw]) for y in range(th)]
        mean = sum(row_sums) / th
        var = sum((x - mean) ** 2 for x in row_sums)
        if a == 0:
            base_var = var
        if var > best_var:
            best_var = var
            best_angle = a

    # Apply only if variance improvement is significant (> 8% over 0 degrees)
    if best_angle != 0 and base_var > 0 and (best_var - base_var) / base_var > 0.08:
        return best_angle
    return 0


def detect_orientation_angle(image: Image.Image) -> int:
    """Detect visual 90/180/270 degree rotation using Tesseract OSD.

    Returns degrees to rotate clockwise/counter-clockwise, or 0 if upright / inconclusive.
    """
    try:
        import pytesseract

        # OSD requires sufficient characters; specify DPI to prevent warning noise
        osd = pytesseract.image_to_osd(image, config="--dpi 300", output_type=pytesseract.Output.DICT)
        rotate_deg = int(osd.get("rotate", 0))
        if rotate_deg in (90, 180, 270):
            return rotate_deg
    except Exception as exc:
        logger.debug("Tesseract OSD could not determine orientation: %s", exc)

    return 0


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

    # Handle transparent background by compositing onto a white canvas
    if image.mode in ("RGBA", "LA"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        alpha = image.split()[-1]
        background.paste(image.convert("RGB"), mask=alpha)
        result = background
    elif image.mode == "P":
        result = image.convert("RGB")
    else:
        result = image.copy()

    # Step 1: EXIF Transpose
    result = ImageOps.exif_transpose(result).copy()
    operations = ["exif_orientation"]
    stages.append({
        "stage": "exif_orientation",
        "title": "EXIF Orientation",
        "description": "Normalized rotation based on image EXIF metadata",
        "dimensions": [result.width, result.height],
        "image": result.copy(),
        "is_ocr_input": False,
    })

    # Step 2: Visual Orientation (OSD 90/180/270 deg)
    osd_rotate = detect_orientation_angle(result)
    if osd_rotate in (90, 180, 270):
        # Rotate back to upright: if detected rotate is 90, rotate by -90 (expand frame)
        result = result.rotate(-osd_rotate, expand=True)
        operations.append("orientation_correction")
        stages.append({
            "stage": "orientation_correction",
            "title": "Visual Orientation Correction",
            "description": f"Rotated by {360 - osd_rotate}° via Tesseract OSD to restore upright reading orientation",
            "dimensions": [result.width, result.height],
            "image": result.copy(),
            "is_ocr_input": False,
        })

    # Step 3: Skew Detection & Correction
    skew_angle = estimate_skew_angle(result)
    if skew_angle != 0:
        result = result.rotate(skew_angle, resample=Image.Resampling.BILINEAR, fillcolor=255, expand=False)
        operations.append("deskew")
        stages.append({
            "stage": "deskew",
            "title": "Document Deskewing",
            "description": f"Rotated by {skew_angle}° via projection profile variance to level text baselines",
            "dimensions": [result.width, result.height],
            "image": result.copy(),
            "is_ocr_input": False,
        })

    # Step 4: Convert to grayscale to simplify text recognition
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

    # Step 5: Upscale small images to improve recognition of fine text
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

    # Step 6: Improve contrast without applying a destructive denoising filter
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

    # Step 7: Subtle contrast adjustment
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
