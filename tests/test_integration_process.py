"""Integration tests for the complete Layer 1 document processing pipeline:

POST /api/v1/documents/process
"""

import io
import json
from unittest.mock import AsyncMock, patch
import unittest

from fastapi.testclient import TestClient
import httpx
import jsonschema
from PIL import Image, ImageDraw

from api.main import app


class TestDocumentProcessingIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        with open("contracts/prepared_document.schema.json") as f:
            cls.schema = json.load(f)

    def _create_image(self, text: str, size: tuple[int, int] = (800, 300)) -> bytes:
        img = Image.new("RGB", size, color="white")
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), text, fill="black")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    # 1. A valid invoice with recognizable fields
    def test_1_valid_invoice(self):
        invoice_text = (
            "INVOICE\n"
            "Invoice Number: INV-2026-001\n"
            "Invoice Date: 2026-10-20\n"
            "Amount Due: $12,500.00\n"
            "Contact: billing@example.com"
        )
        img_bytes = self._create_image(invoice_text)

        # Mock AI engine response for deterministic unit testing
        mock_ai_response = httpx.Response(
            status_code=200,
            json={
                "document_id": "test-inv-001",
                "status": "completed",
                "extracted_facts": {
                    "emails": ["billing@example.com"],
                    "phone_numbers": [],
                    "dates": ["2026-10-20"],
                    "text_length": len(invoice_text),
                    "invoice_number": "INV-2026-001",
                    "invoice_date": "2026-10-20",
                    "amount_due": "12500.00",
                },
                "inferred_facts": {
                    "document_type": "invoice",
                    "has_email": True,
                    "contact_information_present": True,
                    "has_contact_method": True,
                },
                "reasoning": [
                    {
                        "rule": "EmailContactRule",
                        "conclusion": {"contact_information_present": True},
                        "explanation": "The document contains an email address.",
                    },
                    {
                        "rule": "ContactMethodRule",
                        "conclusion": {"has_contact_method": True},
                        "explanation": "The document has a contact method.",
                    },
                ],
                "classification": {
                    "document_type": "invoice",
                    "classification_method": "keyword_rules",
                    "confidence": "medium",
                },
            },
            request=httpx.Request("POST", "http://testserver/api/v1/analyze"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_ai_response
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("invoice.png", img_bytes, "image/png")},
                data={"document_id": "test-inv-001"},
            )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["document_id"], "test-inv-001")
        self.assertEqual(data["processing"]["image_processing"], "success")
        self.assertEqual(data["processing"]["ai_extraction"], "success")

        # Verify extracted facts
        extracted = data["data"]["extracted_facts"]
        self.assertEqual(extracted["invoice_number"], "INV-2026-001")
        self.assertEqual(extracted["invoice_date"], "2026-10-20")
        self.assertEqual(extracted["amount_due"], "12500.00")
        self.assertIn("billing@example.com", extracted["emails"])
        self.assertEqual(data["data"]["document_type"], "invoice")

    # 2. A poor-quality or partially unreadable document
    def test_2_poor_quality_or_partially_unreadable_document(self):
        # Image with degraded/noisy low-contrast text
        img = Image.new("RGB", (300, 100), color=(200, 200, 200))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "x. .?", fill=(195, 195, 195))
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        mock_ai_response = httpx.Response(
            status_code=200,
            json={
                "document_id": "poor-quality-doc",
                "status": "completed",
                "extracted_facts": {
                    "emails": [], "phone_numbers": [], "dates": [],
                    "text_length": 5, "invoice_number": None,
                    "invoice_date": None, "amount_due": None,
                },
                "inferred_facts": {"has_email": False},
                "reasoning": [],
                "classification": {
                    "document_type": "general_document",
                    "classification_method": "keyword_rules",
                    "confidence": "low",
                },
            },
            request=httpx.Request("POST", "http://testserver/api/v1/analyze"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_ai_response
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("poor.png", buf.getvalue(), "image/png")},
                data={"document_id": "poor-quality-doc"},
            )

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["document_id"], "poor-quality-doc")
        self.assertEqual(payload["status"], "success")

    # 3. A document with missing fields
    def test_3_document_with_missing_fields(self):
        text = "INVOICE\nBill To: John Doe\nContact: help@example.com"
        img_bytes = self._create_image(text)

        mock_ai_response = httpx.Response(
            status_code=200,
            json={
                "document_id": "missing-fields-doc",
                "status": "completed",
                "extracted_facts": {
                    "emails": ["help@example.com"],
                    "phone_numbers": [],
                    "dates": [],
                    "text_length": len(text),
                    "invoice_number": None,
                    "invoice_date": None,
                    "amount_due": None,
                },
                "inferred_facts": {
                    "document_type": "invoice",
                    "has_email": True,
                    "contact_information_present": True,
                    "has_contact_method": True,
                },
                "reasoning": [],
                "classification": {
                    "document_type": "invoice",
                    "classification_method": "keyword_rules",
                    "confidence": "medium",
                },
            },
            request=httpx.Request("POST", "http://testserver/api/v1/analyze"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_ai_response
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("invoice_partial.png", img_bytes, "image/png")},
                data={"document_id": "missing-fields-doc"},
            )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]["extracted_facts"]
        self.assertIsNone(data["invoice_number"])
        self.assertIsNone(data["invoice_date"])
        self.assertIsNone(data["amount_due"])
        self.assertEqual(data["emails"], ["help@example.com"])

    # 4. An unknown document type
    def test_4_unknown_document_type(self):
        text = "Minutes from the weekly meeting.\nAgenda: Roadmap planning."
        img_bytes = self._create_image(text)

        mock_ai_response = httpx.Response(
            status_code=200,
            json={
                "document_id": "general-doc-001",
                "status": "completed",
                "extracted_facts": {
                    "emails": [], "phone_numbers": [], "dates": [],
                    "text_length": len(text),
                    "invoice_number": None, "invoice_date": None, "amount_due": None,
                },
                "inferred_facts": {"has_email": False},
                "reasoning": [],
                "classification": {
                    "document_type": "general_document",
                    "classification_method": "keyword_rules",
                    "confidence": "low",
                },
            },
            request=httpx.Request("POST", "http://testserver/api/v1/analyze"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_ai_response
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("general.png", img_bytes, "image/png")},
                data={"document_id": "general-doc-001"},
            )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(data["document_type"], "general_document")
        self.assertEqual(data["classification"]["confidence"], "low")

    # 5. An invalid or unsupported file
    def test_5_invalid_or_unsupported_file(self):
        # 5a. Unsupported file extension
        resp1 = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("doc.txt", b"Plain text file", "text/plain")},
        )
        self.assertEqual(resp1.status_code, 415)
        self.assertEqual(resp1.json()["detail"]["error"]["code"], "UNSUPPORTED_FILE_FORMAT")

        # 5b. Empty file
        resp2 = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("empty.png", b"", "image/png")},
        )
        self.assertEqual(resp2.status_code, 400)
        self.assertEqual(resp2.json()["detail"]["error"]["code"], "EMPTY_INPUT")

        # 5c. Corrupt image
        resp3 = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("corrupt.png", b"corrupted byte sequence", "image/png")},
        )
        self.assertEqual(resp3.status_code, 400)
        self.assertEqual(resp3.json()["detail"]["error"]["code"], "INVALID_IMAGE")

    # 6. Empty OCR text
    def test_6_empty_ocr_text(self):
        blank = Image.new("RGB", (200, 200), color="white")
        buf = io.BytesIO()
        blank.save(buf, format="PNG")

        resp = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("blank.png", buf.getvalue(), "image/png")},
            data={"document_id": "doc-blank-test"},
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["document_id"], "doc-blank-test")
        self.assertEqual(payload["processing"]["image_processing"], "success")
        self.assertEqual(payload["processing"]["ai_extraction"], "skipped")
        self.assertEqual(payload["data"]["document_type"], "unknown")
        self.assertEqual(payload["prepared_document"]["text"], "")
        self.assertTrue(any(w["code"] == "NO_TEXT_DETECTED" for w in payload["warnings"]))

    # 7. AI service failure or invalid AI response
    def test_7a_ai_service_unreachable(self):
        text = "Hello world document"
        img_bytes = self._create_image(text)

        with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("doc.png", img_bytes, "image/png")},
            )
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()["detail"]["error"]["code"], "AI_SERVICE_UNAVAILABLE")

    def test_7b_ai_service_timeout(self):
        text = "Hello world document"
        img_bytes = self._create_image(text)

        with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectTimeout("Timed out")):
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("doc.png", img_bytes, "image/png")},
            )
        self.assertEqual(resp.status_code, 504)
        self.assertEqual(resp.json()["detail"]["error"]["code"], "AI_SERVICE_TIMEOUT")

    def test_7c_ai_service_server_error(self):
        text = "Hello world document"
        img_bytes = self._create_image(text)

        mock_500 = httpx.Response(
            status_code=500,
            text="Internal Server Error",
            request=httpx.Request("POST", "http://testserver/api/v1/analyze"),
        )
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_500
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("doc.png", img_bytes, "image/png")},
            )
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()["detail"]["error"]["code"], "AI_SERVICE_ERROR")

    def test_7d_ai_service_invalid_json(self):
        text = "Hello world document"
        img_bytes = self._create_image(text)

        mock_invalid = httpx.Response(
            status_code=200,
            content=b"not valid json <xml></xml>",
            headers={"content-type": "application/json"},
            request=httpx.Request("POST", "http://testserver/api/v1/analyze"),
        )
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_invalid
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("doc.png", img_bytes, "image/png")},
            )
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()["detail"]["error"]["code"], "AI_SERVICE_INVALID_RESPONSE")

    # 8. Successful contract-compliant JSON output
    def test_8_contract_compliant_json_output(self):
        text = "Service Agreement\nDate: 2026-10-20\nContact: team@example.com"
        img_bytes = self._create_image(text)

        mock_ai_response = httpx.Response(
            status_code=200,
            json={
                "document_id": "contract-doc-888",
                "status": "completed",
                "extracted_facts": {
                    "emails": ["team@example.com"],
                    "phone_numbers": [],
                    "dates": ["2026-10-20"],
                    "text_length": len(text),
                    "invoice_number": None,
                    "invoice_date": None,
                    "amount_due": None,
                },
                "inferred_facts": {
                    "document_type": "service_agreement",
                    "has_email": True,
                    "contact_information_present": True,
                    "has_contact_method": True,
                },
                "reasoning": [
                    {
                        "rule": "EmailContactRule",
                        "conclusion": {"contact_information_present": True},
                        "explanation": "The document contains an email address.",
                    }
                ],
                "classification": {
                    "document_type": "service_agreement",
                    "classification_method": "keyword_rules",
                    "confidence": "medium",
                },
            },
            request=httpx.Request("POST", "http://testserver/api/v1/analyze"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_ai_response
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("contract.png", img_bytes, "image/png")},
                data={"document_id": "contract-doc-888"},
            )

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()

        # Check top-level contract keys
        for key in ["request_id", "document_id", "status", "data", "prepared_document", "processing", "warnings", "errors"]:
            self.assertIn(key, payload)

        self.assertEqual(payload["document_id"], "contract-doc-888")
        self.assertEqual(payload["status"], "success")

        # Validate prepared_document against the schema
        jsonschema.validate(instance=payload["prepared_document"], schema=self.schema)

    # 9. Intermediate stage images retrieval and verification
    def test_9_intermediate_images_generated_and_retrievable(self):
        text = "Invoice Number: INV-STAGE-001\nTotal Due: $500.00"
        img_bytes = self._create_image(text, size=(400, 200))

        mock_ai_response = httpx.Response(
            status_code=200,
            json={
                "document_id": "doc-stage-test",
                "status": "completed",
                "extracted_facts": {
                    "emails": [], "phone_numbers": [], "dates": [],
                    "text_length": len(text), "invoice_number": "INV-STAGE-001",
                    "invoice_date": None, "amount_due": "500.00",
                },
                "inferred_facts": {"document_type": "invoice"},
                "reasoning": [],
                "classification": {"document_type": "invoice", "confidence": "medium", "classification_method": "keyword_rules"},
            },
            request=httpx.Request("POST", "http://testserver/api/v1/analyze"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_ai_response
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("small_doc.png", img_bytes, "image/png")},
                data={"document_id": "doc-stage-test"},
            )

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()

        stages = payload.get("intermediate_images", [])
        self.assertGreater(len(stages), 1)

        # Check required stage names
        stage_names = [s["stage"] for s in stages]
        self.assertIn("original", stage_names)
        self.assertIn("exif_orientation", stage_names)
        self.assertIn("grayscale", stage_names)
        self.assertIn("upscale", stage_names)  # small image upscaled
        self.assertIn("autocontrast", stage_names)
        self.assertIn("contrast_adjustment", stage_names)

        # Check OCR input flag
        self.assertTrue(any(s.get("is_ocr_input") for s in stages))

        # Retrieve the original image via endpoint
        run_id = payload["run_id"]
        img_resp = self.client.get(f"/api/v1/runs/{run_id}/stages/original.png")
        self.assertEqual(img_resp.status_code, 200)
        self.assertEqual(img_resp.headers["content-type"], "image/png")

        # Verify decoded Pillow image
        retrieved_img = Image.open(io.BytesIO(img_resp.content))
        self.assertEqual(retrieved_img.size, (400, 200))

    # 10. Intermediate image error handling (not found and traversal protection)
    def test_10_stage_image_not_found_and_traversal(self):
        # Non-existent run
        resp = self.client.get("/api/v1/runs/00000000-0000-0000-0000-000000000000/stages/original.png")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"]["error"]["code"], "IMAGE_NOT_FOUND")

        # Invalid stage name
        resp2 = self.client.get("/api/v1/runs/00000000-0000-0000-0000-000000000000/stages/../../etc/passwd")
        self.assertIn(resp2.status_code, [404, 422])


if __name__ == "__main__":
    unittest.main()
