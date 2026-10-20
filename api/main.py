"""FastAPI routes for the image preparation module."""

import os
import logging
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from image_processing import ProcessingError, ProcessingOptions, prepare_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI(title="IVP+AI Document Preparation API", version="1.0.0")
MAX_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10")) * 1024 * 1024


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request, exc: RequestValidationError) -> JSONResponse:
    """Return FastAPI request errors in the same public error envelope."""
    return JSONResponse(status_code=422, content={"detail": {"error": {
        "code": "INVALID_REQUEST", "message": "The request data is invalid."
    }}})


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}


@app.get("/api/v1/info")
def info() -> dict[str, object]:
    """Report public contract and input format information."""
    return {"schema_version": "1.0", "supported_file_types": ["PNG", "JPEG"],
            "max_upload_size_mb": MAX_BYTES // (1024 * 1024)}


@app.post("/api/v1/documents/prepare")
async def prepare(file: UploadFile = File(...), document_id: str | None = Form(default=None)) -> dict:
    """Prepare one uploaded PNG or JPEG image and return the shared contract."""
    try:
        data = await file.read(MAX_BYTES + 1)
        result = prepare_document(data, file.filename or "upload", document_id,
                                  ProcessingOptions(max_file_size_bytes=MAX_BYTES))
        return result.to_dict()
    except ProcessingError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"error": {
            "code": exc.code, "message": exc.message, **({"details": exc.details} if exc.details else {})}}) from None
    except Exception:
        logger.exception("Unexpected document processing failure")
        raise HTTPException(status_code=500, detail={"error": {
            "code": "INTERNAL_SERVER_ERROR", "message": "Document processing failed unexpectedly."}}) from None


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    """Serve the demonstration frontend."""
    return FileResponse("frontend/index.html")


app.mount("/static", StaticFiles(directory="frontend"), name="static")
