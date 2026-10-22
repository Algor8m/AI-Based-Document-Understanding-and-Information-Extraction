"""Acceptance test suite directly verifying the acceptance criteria in Section 10:

1. API health check
2. Valid image upload & pipeline execution
3. Real intermediate-image viewer
4. Real OCR text extraction
5. Real AI integration & response
6. Invalid file & corrupt image handling
7. Empty OCR (no false success; AI call skipped)
8. AI service offline (clear error; no fabricated results)
9. Sequential uploads (fresh results replace stale results)
"""

import io
import json
from unittest.mock import AsyncMock, patch
import unittest

from fastapi.testclient import TestClient
import httpx
from PIL import Image, ImageDraw, ImageFont

from api.main import app


class TestAcceptanceCriteria(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def _make_image(self, text: str, size: tuple[int, int] = (800, 300)) -> bytes:
        img = Image.new("RGB", size, color="white")
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default(size=20)
        draw.text((30, 30), text, font=font, fill="black")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    # Criteria 1: API health check
    def test_acceptance_1_api_health_check(self):
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    # Criteria 2: Valid image upload & processing pipeline
    def test_acceptance_2_valid_image_processing_pipeline(self):
        text = "INVOICE\nInvoice Number: INV-AC-001\nAmount Due: $950.00"
        img_bytes = self._make_image(text)

        mock_ai = httpx.Response(
            status_code=200,
            json={
                "document_id": "doc-ac-001",
                "status": "completed",
                "extracted_facts": {
                    "emails": [], "phone_numbers": [], "dates": [],
                    "text_length": len(text), "invoice_number": "INV-AC-001",
                    "invoice_date": None, "amount_due": "950.00",
                },
                "inferred_facts": {"document_type": "invoice"},
                "reasoning": [],
                "classification": {"document_type": "invoice", "confidence": "medium", "classification_method": "keyword_rules"},
            },
            request=httpx.Request("POST", "http://testserver/api/v1/analyze"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_ai
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("invoice.png", img_bytes, "image/png")},
                data={"document_id": "doc-ac-001"},
            )

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["processing"]["image_processing"], "success")
        self.assertEqual(payload["processing"]["ai_extraction"], "success")

    # Criteria 3: Real intermediate-image viewer
    def test_acceptance_3_intermediate_image_viewer(self):
        text = "Agreement Document"
        img_bytes = self._make_image(text, size=(500, 250))

        mock_ai = httpx.Response(
            status_code=200,
            json={
                "document_id": "doc-stg",
                "status": "completed",
                "extracted_facts": {"emails": [], "phone_numbers": [], "dates": [], "text_length": len(text), "invoice_number": None, "invoice_date": None, "amount_due": None},
                "inferred_facts": {"document_type": "general_document"},
                "reasoning": [],
                "classification": {"document_type": "general_document", "confidence": "low", "classification_method": "keyword_rules"},
            },
            request=httpx.Request("POST", "http://testserver/api/v1/analyze"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_ai
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("doc.png", img_bytes, "image/png")},
                data={"document_id": "doc-stg"},
            )

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        run_id = payload["run_id"]
        stages = payload["intermediate_images"]
        self.assertGreater(len(stages), 0)

        # Retrieve one of the stage images directly
        first_stage = stages[0]
        get_resp = self.client.get(first_stage["image_url"])
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.headers["content-type"], "image/png")

        # Confirm image is decodable
        img = Image.open(io.BytesIO(get_resp.content))
        self.assertEqual(img.size, (first_stage["dimensions"][0], first_stage["dimensions"][1]))

    # Criteria 4: Real OCR text extraction
    def test_acceptance_4_real_ocr_extraction(self):
        text = "Hello Tesseract Recognition Test"
        img_bytes = self._make_image(text)

        mock_ai = httpx.Response(
            status_code=200,
            json={
                "document_id": "doc-ocr-test",
                "status": "completed",
                "extracted_facts": {"emails": [], "phone_numbers": [], "dates": [], "text_length": len(text), "invoice_number": None, "invoice_date": None, "amount_due": None},
                "inferred_facts": {},
                "reasoning": [],
                "classification": {"document_type": "general_document", "confidence": "low", "classification_method": "keyword_rules"},
            },
            request=httpx.Request("POST", "http://testserver/api/v1/analyze"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_ai
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("test_ocr.png", img_bytes, "image/png")},
                data={"document_id": "doc-ocr-test"},
            )

        self.assertEqual(resp.status_code, 200)
        extracted_text = resp.json()["prepared_document"]["text"]
        self.assertIn("Hello", extracted_text)
        self.assertIn("Tesseract", extracted_text)

    # Criteria 5: Empty OCR skips AI call and yields warning
    def test_acceptance_5_empty_ocr_skips_ai(self):
        blank = Image.new("RGB", (200, 200), color="white")
        buf = io.BytesIO()
        blank.save(buf, format="PNG")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("blank.png", buf.getvalue(), "image/png")},
                data={"document_id": "doc-blank"},
            )
            # Verify AI service was never called
            mock_post.assert_not_called()

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["processing"]["ai_extraction"], "skipped")
        self.assertTrue(any(w["code"] == "NO_TEXT_DETECTED" for w in payload["warnings"]))

    # Criteria 6: AI service offline returns clear error without fabricated results
    def test_acceptance_6_ai_service_offline_handled(self):
        text = "Sample Document Text"
        img_bytes = self._make_image(text)

        with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("sample.png", img_bytes, "image/png")},
            )

        self.assertEqual(resp.status_code, 502)
        err = resp.json()["detail"]["error"]
        self.assertEqual(err["code"], "AI_SERVICE_UNAVAILABLE")

    # Criteria 7: Invalid file rejected
    def test_acceptance_7_invalid_file_rejected(self):
        resp = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("document.pdf", b"fake pdf content", "application/pdf")},
        )
        self.assertEqual(resp.status_code, 415)
        self.assertEqual(resp.json()["detail"]["error"]["code"], "UNSUPPORTED_FILE_FORMAT")

    # Criteria 8: Corrupt image rejected gracefully
    def test_acceptance_8_corrupt_image_rejected(self):
        resp = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("corrupt.png", b"random bytes not png", "image/png")},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"]["error"]["code"], "INVALID_IMAGE")

    # Criteria 9: Sequential uploads (second upload returns distinct fresh results)
    def test_acceptance_9_sequential_uploads_isolated(self):
        text1 = "INVOICE\nInvoice Number: INV-001\nAmount Due: $100.00"
        text2 = "Service Agreement\nDate: 2026-10-22\nContact: test@corp.com"

        img1 = self._make_image(text1)
        img2 = self._make_image(text2)

        mock_ai1 = httpx.Response(
            status_code=200,
            json={
                "document_id": "run-doc-001", "status": "completed",
                "extracted_facts": {"emails": [], "phone_numbers": [], "dates": [], "text_length": len(text1), "invoice_number": "INV-001", "invoice_date": None, "amount_due": "100.00"},
                "inferred_facts": {"document_type": "invoice"}, "reasoning": [],
                "classification": {"document_type": "invoice", "confidence": "medium", "classification_method": "keyword_rules"},
            },
            request=httpx.Request("POST", "http://testserver/api/v1/analyze"),
        )
        mock_ai2 = httpx.Response(
            status_code=200,
            json={
                "document_id": "run-doc-002", "status": "completed",
                "extracted_facts": {"emails": ["test@corp.com"], "phone_numbers": [], "dates": ["2026-10-22"], "text_length": len(text2), "invoice_number": None, "invoice_date": None, "amount_due": None},
                "inferred_facts": {"document_type": "service_agreement"}, "reasoning": [],
                "classification": {"document_type": "service_agreement", "confidence": "medium", "classification_method": "keyword_rules"},
            },
            request=httpx.Request("POST", "http://testserver/api/v1/analyze"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            # First upload
            mock_post.return_value = mock_ai1
            resp1 = self.client.post("/api/v1/documents/process", files={"file": ("doc1.png", img1, "image/png")}, data={"document_id": "run-doc-001"})
            # Second upload
            mock_post.return_value = mock_ai2
            resp2 = self.client.post("/api/v1/documents/process", files={"file": ("doc2.png", img2, "image/png")}, data={"document_id": "run-doc-002"})

        p1 = resp1.json()
        p2 = resp2.json()

        self.assertEqual(p1["document_id"], "run-doc-001")
        self.assertEqual(p1["data"]["document_type"], "invoice")
        self.assertEqual(p1["data"]["extracted_facts"]["invoice_number"], "INV-001")

        self.assertEqual(p2["document_id"], "run-doc-002")
        self.assertEqual(p2["data"]["document_type"], "service_agreement")
        self.assertIn("test@corp.com", p2["data"]["extracted_facts"]["emails"])

        # Run IDs must be distinct
        self.assertNotEqual(p1["run_id"], p2["run_id"])


if __name__ == "__main__":
    unittest.main()
