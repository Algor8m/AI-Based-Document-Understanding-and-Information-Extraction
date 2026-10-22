
from pathlib import Path

import pytesseract
from PIL import Image
from image_processing.preprocessor import preprocess_image

IMAGE_PATH = Path.home() / "Downloads" / "examplev2.1.png"

if not IMAGE_PATH.exists():
    raise FileNotFoundError(
        f"Image not found: {IMAGE_PATH}\n"
        "Update IMAGE_PATH to the actual image location."
    )

image = Image.open(IMAGE_PATH)
prepared, operations = preprocess_image(image)

print("Original dimensions:", image.size)
print("Prepared dimensions:", prepared.size)
print("Preprocessing:", operations)

for psm in (3, 6, 11):
    print("\n" + "=" * 60)
    print(f"OCR RESULT — PSM {psm}")
    print("=" * 60)

    try:
        text = pytesseract.image_to_string(
            prepared,
            lang="eng",
            config=f"--psm {psm}",
        )
        print(text)
        print("\nExtracted characters:", len(text))
    except pytesseract.TesseractError as exc:
        print("OCR failed:", exc)
