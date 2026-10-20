# IVP+AI — AI Engine REST API Contract

## 1. Overview

The AI Engine receives extracted document text from the image-processing module, identifies basic facts, applies rules and forward chaining, and returns structured JSON.

## 2. Endpoint

- **Method:** `POST`
- **Path:** `/api/v1/analyze`
- **Content-Type:** `application/json`
- **Response:** `application/json`

Local development URL: `http://127.0.0.1:8000/api/v1/analyze`

## 3. Request Format

```json
{
  "document_id": "demo-001",
  "text": "Service Agreement\nDate: 2026-10-20\nContact: example@example.com"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `document_id` | String | Yes | Identifier assigned to the document |
| `text` | String | Yes | Text extracted from the document, typically by OCR |

Both fields must be non-empty. The text must be supplied as a JSON string.


## 4. Successful Response

HTTP status: `200 OK`

```json
{
  "document_id": "invoice-001",
  "status": "completed",
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
      "conclusion": {
        "contact_information_present": true
      },
      "explanation": "The document contains an email address."
    },
    {
      "rule": "ContactMethodRule",
      "conclusion": {
        "has_contact_method": true
      },
      "explanation": "The document has a contact method."
    }
  ],
  "classification": {
    "document_type": "invoice",
    "classification_method": "keyword_rules",
    "confidence": "medium"
  }
}
```

The values above illustrate the response structure. Actual extracted values and text length depend on the submitted text.

### Classification fields

- `classification.document_type`: `service_agreement`, `invoice`, or `general_document`.
- `classification.classification_method`: currently `keyword_rules`.
- `classification.confidence`: heuristic label, either `low` or `medium`; it is not a calibrated probability.

### Invoice extraction fields

- `extracted_facts.invoice_number`: invoice identifier detected from a recognized invoice-number label, or `null` if not detected.
- `extracted_facts.invoice_date`: date detected after an `Invoice Date` label, or `null` if not detected.
- `extracted_facts.amount_due`: amount detected after an amount-due or balance-due label, returned as a string without currency symbols or thousands separators, or `null` if not detected.

Invoice extraction currently uses label-based pattern matching. It may not detect fields in every invoice format.

## 5. Error Responses

- **422 Unprocessable Entity:** Missing required fields, invalid field types, or empty values rejected by validation.
- **500 Internal Server Error:** Unexpected analysis failure.

Error responses may use FastAPI's standard JSON error format.

## 6. Processing Responsibilities

The AI Engine is responsible for:

1. Accepting document text.
2. Extracting basic facts such as emails, phone numbers, and dates.
3. Classifying documents using keyword-based rules.
4. Loading facts into its knowledge base.
5. Evaluating IF–THEN rules.
6. Applying forward chaining.
7. Returning extracted facts, inferred facts, document classification, and reasoning in structured JSON.

The image-processing module is responsible for document image input, preprocessing, and OCR, then submitting the resulting text to this API.

## 7. Integration Requirements

- The caller must send valid JSON using the field names defined above.
- The caller must not depend on internal Python classes or file paths.
- The API response is the integration boundary between the two modules.
- The local URL is for development; deployments must use the configured host and port.
- Any future changes to request or response fields must be coordinated between module owners.

## 8. Current Limitations

The current implementation demonstrates basic contact-information extraction and rule-based inference. It does not yet provide comprehensive legal-document understanding, clause extraction, or production-grade OCR integration.