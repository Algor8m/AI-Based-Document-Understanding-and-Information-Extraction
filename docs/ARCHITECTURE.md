# Architecture and module responsibilities

The request path is `Upload → validator → optional preprocessor → Tesseract adapter → conservative text cleaner → PreparedDocumentResult → API JSON`. `image_processing.prepare_document()` is the public callable entry point and does not need a web server. The API owns HTTP status mapping and never duplicates pipeline steps. The frontend only submits a real multipart request and renders the response.

## Python module guide

- `image_processing/validator.py`: checks empty bytes, size, extension, actual decoded format, and image readability.
- `image_processing/preprocessor.py`: applies EXIF orientation and conservative grayscale, contrast, and median-filter steps; can be disabled.
- `image_processing/ocr_engine.py`: isolates the pytesseract/Tesseract dependency and returns structured engine errors.
- `image_processing/text_cleaner.py`: normalizes line breaks and excess blank space while retaining punctuation and digits.
- `image_processing/models.py`: defines the output model and safe processing error type.
- `image_processing/document_processor.py`: coordinates the steps and builds contract v1.0.
- `api/main.py`: FastAPI health, info, upload, and demo frontend routes.
- `tests/`: deterministic core/API checks with OCR mocked, plus an optional real Tesseract check.

## Contract coordination

`contracts/prepared_document.schema.json` is the provisional validation proposal. It preserves the requested top-level field names and types. `source` has `type` and `filename`; warnings use `code` and `message`. Metadata includes the requested image facts plus preprocessing operations and measured duration. Please agree these nested fields and whether the partner needs a caller-supplied ID before freezing the contract. No facts, rules, or conclusions belong here.

## Known limitations

Only single PNG/JPEG images are supported. OCR quality depends on image quality and installed Tesseract language data. Orientation uses EXIF metadata; there is no visual/skew rotation detection. No confidence score is generated. Preprocessing is deliberately modest. API multipart transport requires the small `python-multipart` package.
