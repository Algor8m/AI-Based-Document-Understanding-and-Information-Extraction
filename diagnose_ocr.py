
from pathlib import Path

from PIL import Image
import pytesseract

from image_processing.preprocessor import preprocess_image
from image_processing.ocr_engine import extract_text
from image_processing.text_cleaner import clean_text

image_path = Path.home() / "Downloads" / "examplev2.1.png"
original = Image.open(image_path)

prepared, operations = preprocess_image(original)

# Compare OCR directly on the prepared image with the production OCR function.
raw_text = pytesseract.image_to_string(
    prepared,
    lang="eng",
    config="--psm 3",
)
engine_text = extract_text(prepared)
cleaned_text = clean_text(engine_text)

print("Original dimensions:", original.size)
print("Prepared dimensions:", prepared.size)
print("Preprocessing:", operations)
print("Raw OCR characters:", len(raw_text))
print("Engine OCR characters:", len(engine_text))
print("Cleaned characters:", len(cleaned_text))
print("\nLast 300 characters of raw OCR:")
print(repr(raw_text[-300:]))
print("\nLast 300 characters after cleaning:")
print(repr(cleaned_text[-300:]))
