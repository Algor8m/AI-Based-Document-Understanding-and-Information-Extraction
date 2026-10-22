# IVP+AI — REST API Documentation

## Overview

The IVP+AI Document Processing System provides a modular REST API for automated document ingestion, image preprocessing, OCR extraction, rule-based classification, and factual reasoning.

The system comprises two modular REST services communicating over HTTP:
1. **Document Processing Gateway API (`api.main:app`, default port 8000)**: Coordinates image validation, preprocessing, OCR text extraction, and calls the AI Engine. Also serves the demonstration web frontend.
2. **AI Engine Service (`modules/ai-engine/api.py`, default port 8001)**: Receives document text, executes keyword-based document classification, extracts structured facts, evaluates forward-chaining IF-THEN rules, and returns reasoning conclusions.

---

## Service Configuration & Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AI_ENGINE_URL` | `http://127.0.0.1:8001` | Base URL of the AI Engine REST service |
| `AI_ENGINE_TIMEOUT_SECONDS` | `10.0` | HTTP request timeout when calling the AI engine |
| `MAX_UPLOAD_SIZE_MB` | `10` | Maximum file size allowed for document uploads (MB) |
| `TESSERACT_CMD` | Auto-detected | Path to `tesseract.exe` (defaults to standard Windows path `C:\Program Files\Tesseract-OCR\tesseract.exe` if not set) |

---

## Gateway Endpoints (`http://127.0.0.1:8000`)

### 1. `POST /api/v1/documents/process` (Primary Layer 1 Pipeline)
**Purpose:** End-to-end document processing pipeline.
**Content-Type:** `multipart/form-data`

**Request Parameters:**
- `file` (UploadFile, required): The document image (PNG or JPEG, up to 10 MB).
- `document_id` (str, optional): Custom unique document identifier. If omitted, a UUID is automatically generated.

**Success Response (`200 OK`):**
```json
{
  "request_id": "req-9c878fb6-7cc0-496e-a342-998f45a0b7d4",
  "document_id": "inv-2026-001",
  "status": "success",
  "data": {
    "document_type": "invoice",
    "classification": {
      "document_type": "invoice",
      "classification_method": "keyword_rules",
      "confidence": "medium"
    },
    "extracted_facts": {
      "emails": ["billing@example.com"],
      "phone_numbers": [],
      "dates": ["2026-10-20"],
      "text_length": 116,
      "invoice_number": "INV-2026-001",
      "invoice_date": "2026-10-20",
      "amount_due": "12500.00"
    },
    "inferred_facts": {
      "document_type": "invoice",
      "has_email": true,
      "contact_information_present": true,
      "has_contact_method": true
    },
    "reasoning": [
      {
        "rule": "EmailContactRule",
        "conclusion": {"contact_information_present": true},
        "explanation": "The document contains an email address."
      },
      {
        "rule": "ContactMethodRule",
        "conclusion": {"has_contact_method": true},
        "explanation": "The document has a contact method."
      }
    ]
  },
  "prepared_document": {
    "schema_version": "1.0",
    "document_id": "inv-2026-001",
    "source": {
      "type": "image",
      "filename": "invoice.png"
    },
    "text": "INVOICE\nInvoice Number: INV-2026-001\n...",
    "metadata": {
      "page_count": 1,
      "image_width": 900,
      "image_height": 400,
      "image_format": "PNG",
      "ocr_engine": "tesseract",
      "preprocessing_operations": ["exif_orientation", "grayscale", "autocontrast", "contrast_adjustment"],
      "processing_duration_ms": 115.4
    },
    "warnings": []
  },
  "processing": {
    "image_processing": "success",
    "ai_extraction": "success"
  },
  "warnings": [],
  "errors": []
}
```

---

### 2. `POST /api/v1/documents/prepare` (Image Preparation Only)
**Purpose:** Preprocess an image and extract OCR text without invoking AI analysis.
**Content-Type:** `multipart/form-data`
**Response:** Conforms to `contracts/prepared_document.schema.json`.

---

### 3. `GET /api/v1/health`
**Purpose:** Gateway health check.
**Response (`200 OK`):**
```json
{"status": "ok"}
```

---

### 4. `GET /api/v1/info`
**Purpose:** Reports contract version, supported file formats, size limit, and active endpoints.
**Response (`200 OK`):**
```json
{
  "schema_version": "1.0",
  "supported_file_types": ["PNG", "JPEG"],
  "max_upload_size_mb": 10,
  "ai_engine_url": "http://127.0.0.1:8001",
  "endpoints": {
    "prepare": "/api/v1/documents/prepare",
    "process": "/api/v1/documents/process",
    "health": "/api/v1/health",
    "info": "/api/v1/info"
  }
}
```

---

## AI Engine Endpoints (`http://127.0.0.1:8001`)

### 1. `POST /api/v1/analyze`
**Purpose:** Analyze document text, extract entities, classify document type, and evaluate reasoning rules.
**Content-Type:** `application/json`

**Request:**
```json
{
  "document_id": "doc-001",
  "text": "Service Agreement\nDate: 2026-10-20\nContact: test@example.com"
}
```

**Response (`200 OK`):**
```json
{
  "document_id": "doc-001",
  "status": "completed",
  "extracted_facts": {
    "emails": ["test@example.com"],
    "phone_numbers": [],
    "dates": ["2026-10-20"],
    "text_length": 62,
    "invoice_number": null,
    "invoice_date": null,
    "amount_due": null
  },
  "inferred_facts": {
    "document_type": "service_agreement",
    "has_email": true,
    "contact_information_present": true,
    "has_contact_method": true
  },
  "reasoning": [
    {
      "rule": "EmailContactRule",
      "conclusion": {"contact_information_present": true},
      "explanation": "The document contains an email address."
    },
    {
      "rule": "ContactMethodRule",
      "conclusion": {"has_contact_method": true},
      "explanation": "The document has a contact method."
    }
  ],
  "classification": {
    "document_type": "service_agreement",
    "classification_method": "keyword_rules",
    "confidence": "medium"
  }
}
```

---

## Standard Error Response Format

All API errors return a consistent JSON envelope:

```json
{
  "detail": {
    "error": {
      "code": "ERROR_CODE",
      "message": "Human-readable error explanation.",
      "details": {}
    }
  }
}
```

### Common Error Codes & HTTP Statuses

| Code | HTTP Status | Description |
|---|---|---|
| `EMPTY_INPUT` | `400 Bad Request` | Uploaded file contains 0 bytes |
| `INVALID_IMAGE` | `400 Bad Request` | File data is not decodable as a valid image |
| `FILE_TOO_LARGE` | `413 Payload Too Large` | Image exceeds configured size limit (10 MB) |
| `UNSUPPORTED_FILE_FORMAT` | `415 Unsupported Media Type` | File extension is not `.png`, `.jpg`, or `.jpeg` |
| `INVALID_REQUEST` | `422 Unprocessable Content` | Request validation failure (missing fields) |
| `INTERNAL_SERVER_ERROR` | `500 Internal Server Error` | Unexpected server failure |
| `AI_SERVICE_UNAVAILABLE` | `502 Bad Gateway` | AI Engine unreachable over HTTP |
| `AI_SERVICE_ERROR` | `502 Bad Gateway` | AI Engine returned an error response |
| `AI_SERVICE_INVALID_RESPONSE` | `502 Bad Gateway` | AI Engine returned non-JSON payload |
| `OCR_ENGINE_UNAVAILABLE` | `503 Service Unavailable` | Tesseract executable or pytesseract missing |
| `AI_SERVICE_TIMEOUT` | `504 Gateway Timeout` | AI Engine call timed out |
