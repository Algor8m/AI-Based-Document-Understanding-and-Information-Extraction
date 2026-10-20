# IVP+AI — Image Processing and Document Preparation

This project module accepts PNG/JPEG images, validates their actual contents, optionally prepares them for recognition, uses Tesseract OCR, conservatively cleans returned text, and emits Prepared-Document JSON contract version `1.0`. It does not implement the Classical AI reasoning module.

## Windows setup

From PowerShell in this project directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install the **Tesseract OCR application separately**. A common Windows distribution is the UB Mannheim build: download and run its current installer from https://github.com/UB-Mannheim/tesseract/wiki. Add its install folder to PATH, or copy `.env.example` to `.env` and set `TESSERACT_CMD` to the full path of `tesseract.exe`. The app reads environment variables; `.env` is an example file and is not loaded automatically. For the current PowerShell window, for example:

```powershell
$env:TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'
$env:MAX_UPLOAD_SIZE_MB = '10'
```

Start the backend (from project root):

```powershell
python -m uvicorn api.main:app --reload
```

Open the website at http://127.0.0.1:8000/ and interactive API docs at http://127.0.0.1:8000/docs. The frontend is served by the backend. It cannot call the API if opened directly as a local file.

Run tests:

```powershell
python -m pytest -q
```

Tests mock OCR for deterministic pipeline and API coverage. `test_real_ocr_available` runs only if Tesseract is on PATH; otherwise pytest marks it skipped. `TESSERACT_CMD` can configure OCR for the application, but the optional test's skip detection checks PATH.

## Pipeline and contract

The pipeline is described in [Architecture](docs/ARCHITECTURE.md). The provisional contract is documented in [the schema](contracts/prepared_document.schema.json), with [success](contracts/examples/prepared_document_success.json) and [empty-text](contracts/examples/prepared_document_empty.json) examples. Empty OCR output remains an empty string and adds a `NO_TEXT_DETECTED` warning. Processing failures use structured errors and do not return fabricated output.

`metadata.image_width` and `metadata.image_height` describe the original uploaded image in pixels. Preprocessing works on an image copy and does not change those source dimensions. Orientation handling uses EXIF metadata only; it does not detect or correct sideways text based on image contents.

## Partner integration

Import `prepare_document` from `image_processing`; pass raw bytes and a filename without using the API or starting Uvicorn. See [API and integration instructions](docs/API.md). Coordinate the nested `source` fields, warning shape, optional ID, and metadata additions with your partner before calling the contract final.

## Repository collaboration

The repository is organized around separate modules, a REST API, and shared schemas. Keep the Classical AI reasoning module separate from this document-preparation output. Contributors should work on separate Git branches and integrate changes through pull requests.

## Configuration and troubleshooting

- `MAX_UPLOAD_SIZE_MB` sets the upload cap (default 10).
- `TESSERACT_CMD` sets the executable when it is not discoverable through PATH.
- `OCR_ENGINE_UNAVAILABLE` / HTTP 503 means the executable is absent, not that OCR found no text.
- `NO_TEXT_DETECTED` is a successful processing result with empty text.
- Check that a `.jpg` filename actually contains JPEG bytes (extension and content are both checked).
- The project uses EXIF-based orientation only; it does not detect sideways text or deskew scans.
- PDF and plain-text documents, confidence scores, and reasoning conclusions are outside this initial module.
