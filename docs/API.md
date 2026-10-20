# API and partner integration

Run the server, then open `/docs` for generated OpenAPI docs. `GET /api/v1/health` returns application status; `GET /api/v1/info` returns schema version, supported image formats, and size limit. Upload to `POST /api/v1/documents/prepare` with multipart field `file` and optional form field `document_id`.

Errors have this shape: `{"detail":{"error":{"code":"...","message":"..."}}}`. The status indicates malformed/empty input (400), oversized input (413), unsupported extension (415), invalid OCR config (422), missing Tesseract (503), or unexpected server failure (500).

## Calling from the partner's Python module

```python
from image_processing import prepare_document

result = prepare_document(image_bytes, "attendance.png", document_id="student-doc-42")
prepared_payload = result.to_dict()
```

The core accepts `bytes`, a filename string, optional ID, and optional `ProcessingOptions`. It imports no FastAPI request or upload classes. Catch `ProcessingError` and use its `code`, `message`, and `status_code` if needed. The partner should consume only the prepared output and keep reasoning data in its own response model.
