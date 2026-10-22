"""FastAPI routes for the image preparation and document processing system."""

import logging
import os
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx

from image_processing import ProcessingError, ProcessingOptions, prepare_document
from image_processing.run_storage import get_stage_image_path, save_run_stages

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="IVP+AI Document Understanding & Processing API",
    version="1.0.0",
    description="Layer 1 Document Processing and Information Extraction REST API",
)

# Narrow CORS configuration for local origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10")) * 1024 * 1024
AI_ENGINE_URL = os.getenv("AI_ENGINE_URL", "http://127.0.0.1:8001")
AI_ENGINE_TIMEOUT_SECONDS = float(os.getenv("AI_ENGINE_TIMEOUT_SECONDS", "10.0"))


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request, exc: RequestValidationError) -> JSONResponse:
    """Return FastAPI request errors in the public error envelope."""
    return JSONResponse(
        status_code=422,
        content={"detail": {"error": {
            "code": "INVALID_REQUEST",
            "message": "The request data is invalid.",
        }}},
    )


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}


@app.get("/api/v1/info")
def info() -> dict[str, object]:
    """Report public contract, endpoints, and input format information."""
    return {
        "schema_version": "1.0",
        "supported_file_types": ["PNG", "JPEG"],
        "max_upload_size_mb": MAX_BYTES // (1024 * 1024),
        "ai_engine_url": AI_ENGINE_URL,
        "endpoints": {
            "prepare": "/api/v1/documents/prepare",
            "process": "/api/v1/documents/process",
            "health": "/api/v1/health",
            "info": "/api/v1/info",
            "stage_image": "/api/v1/runs/{run_id}/stages/{stage_name}",
        },
    }


@app.get("/api/v1/runs/{run_id}/stages/{stage_name}")
def get_stage_image(run_id: str, stage_name: str) -> FileResponse:
    """Serve a verified intermediate stage image for a specific run."""
    try:
        img_path = get_stage_image_path(run_id, stage_name)
        return FileResponse(img_path, media_type="image/png")
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": {
                "code": "IMAGE_NOT_FOUND",
                "message": str(exc),
            }},
        ) from None


@app.post("/api/v1/documents/prepare")
async def prepare(
    file: UploadFile = File(...),
    document_id: str | None = Form(default=None),
) -> dict:
    """Prepare one uploaded PNG or JPEG image and return the shared PreparedDocument contract."""
    try:
        data = await file.read(MAX_BYTES + 1)
        result = prepare_document(
            data,
            file.filename or "upload",
            document_id,
            ProcessingOptions(max_file_size_bytes=MAX_BYTES, return_stages=False),
        )
        return result.to_dict()
    except ProcessingError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error": {
                "code": exc.code,
                "message": exc.message,
                **({"details": exc.details} if exc.details else {}),
            }},
        ) from None
    except Exception:
        logger.exception("Unexpected document preparation failure")
        raise HTTPException(
            status_code=500,
            detail={"error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Document processing failed unexpectedly.",
            }},
        ) from None


@app.post("/api/v1/documents/process")
async def process_document(
    file: UploadFile = File(...),
    document_id: str | None = Form(default=None),
) -> dict:
    """Execute end-to-end document processing:

    Upload -> Validation -> Preprocessing -> OCR -> Clean Text -> PreparedDocument -> AI Analysis -> Normalized JSON.
    """
    request_id = f"req-{uuid4()}"
    run_id = str(uuid4())

    # Step 1-4: Image validation, preprocessing, OCR, text cleaning -> PreparedDocument
    try:
        data = await file.read(MAX_BYTES + 1)
        prepared = prepare_document(
            data,
            file.filename or "upload",
            document_id,
            ProcessingOptions(max_file_size_bytes=MAX_BYTES, return_stages=True),
        )
    except ProcessingError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error": {
                "code": exc.code,
                "message": exc.message,
                **({"details": exc.details} if exc.details else {}),
            }},
        ) from None
    except Exception:
        logger.exception("Unexpected error in image preparation stage")
        raise HTTPException(
            status_code=500,
            detail={"error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Document processing failed unexpectedly during image preparation.",
            }},
        ) from None

    # Save real intermediate stage images to run storage
    try:
        stage_metadata = save_run_stages(run_id, prepared.intermediate_stages)
    except Exception as exc:
        logger.warning("Could not persist intermediate images: %s", exc)
        stage_metadata = []

    original_url = stage_metadata[0]["image_url"] if stage_metadata else None
    ocr_input_stage = next((s for s in stage_metadata if s.get("is_ocr_input")), None)
    processed_url = ocr_input_stage["image_url"] if ocr_input_stage else (stage_metadata[-1]["image_url"] if stage_metadata else None)

    # Step 5: Check if OCR text was detected
    if not prepared.text or not prepared.text.strip():
        # Empty OCR text - handle safely without calling AI engine
        return {
            "request_id": request_id,
            "document_id": prepared.document_id,
            "run_id": run_id,
            "status": "success",
            "data": {
                "document_type": "unknown",
                "classification": {
                    "document_type": "unknown",
                    "classification_method": "none",
                    "confidence": "none",
                },
                "extracted_facts": {
                    "emails": [],
                    "phone_numbers": [],
                    "dates": [],
                    "text_length": 0,
                    "invoice_number": None,
                    "invoice_date": None,
                    "amount_due": None,
                },
                "inferred_facts": {},
                "reasoning": [],
            },
            "prepared_document": prepared.to_dict(),
            "intermediate_images": stage_metadata,
            "original_image_url": original_url,
            "processed_image_url": processed_url,
            "stages_completed_count": len(stage_metadata),
            "processing": {
                "image_processing": "success",
                "ai_extraction": "skipped",
            },
            "warnings": prepared.warnings,
            "errors": [],
        }

    # Step 6: Call AI engine /api/v1/analyze via REST
    ai_url = f"{AI_ENGINE_URL.rstrip('/')}/api/v1/analyze"
    try:
        async with httpx.AsyncClient(timeout=AI_ENGINE_TIMEOUT_SECONDS) as client:
            ai_resp = await client.post(
                ai_url,
                json={
                    "document_id": prepared.document_id,
                    "text": prepared.text,
                },
            )
    except httpx.ConnectTimeout:
        raise HTTPException(
            status_code=504,
            detail={"error": {
                "code": "AI_SERVICE_TIMEOUT",
                "message": f"Connection timed out reaching AI engine at {ai_url}.",
            }},
        ) from None
    except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout):
        raise HTTPException(
            status_code=504,
            detail={"error": {
                "code": "AI_SERVICE_TIMEOUT",
                "message": "AI analysis service timed out during processing.",
            }},
        ) from None
    except (httpx.ConnectError, httpx.NetworkError):
        raise HTTPException(
            status_code=502,
            detail={"error": {
                "code": "AI_SERVICE_UNAVAILABLE",
                "message": f"Could not connect to AI analysis service at {ai_url}.",
            }},
        ) from None
    except Exception:
        logger.exception("Unexpected error communicating with AI engine")
        raise HTTPException(
            status_code=502,
            detail={"error": {
                "code": "AI_SERVICE_ERROR",
                "message": "Failed to communicate with AI analysis service.",
            }},
        ) from None

    if ai_resp.status_code != 200:
        logger.error("AI service returned error status %d: %s", ai_resp.status_code, ai_resp.text)
        raise HTTPException(
            status_code=502,
            detail={"error": {
                "code": "AI_SERVICE_ERROR",
                "message": f"AI service returned error code {ai_resp.status_code}.",
            }},
        )

    try:
        ai_data = ai_resp.json()
    except Exception:
        raise HTTPException(
            status_code=502,
            detail={"error": {
                "code": "AI_SERVICE_INVALID_RESPONSE",
                "message": "AI service returned non-JSON response.",
            }},
        )

    # Step 7: Build normalized result
    doc_type = (
        ai_data.get("classification", {}).get("document_type")
        or ai_data.get("inferred_facts", {}).get("document_type")
        or "unknown"
    )

    return {
        "request_id": request_id,
        "document_id": prepared.document_id,
        "run_id": run_id,
        "status": "success",
        "data": {
            "document_type": doc_type,
            "classification": ai_data.get("classification", {}),
            "extracted_facts": ai_data.get("extracted_facts", {}),
            "inferred_facts": ai_data.get("inferred_facts", {}),
            "reasoning": ai_data.get("reasoning", []),
        },
        "prepared_document": prepared.to_dict(),
        "intermediate_images": stage_metadata,
        "original_image_url": original_url,
        "processed_image_url": processed_url,
        "stages_completed_count": len(stage_metadata),
        "processing": {
            "image_processing": "success",
            "ai_extraction": "success",
        },
        "warnings": prepared.warnings,
        "errors": [],
    }


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    """Serve the demonstration frontend."""
    return FileResponse("frontend/index.html")


app.mount("/static", StaticFiles(directory="frontend"), name="static")
