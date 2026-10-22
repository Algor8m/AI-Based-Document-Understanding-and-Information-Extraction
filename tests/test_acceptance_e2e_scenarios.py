"""Acceptance test suite executing the 14 required E2E acceptance scenarios (E2E-01 to E2E-14)."""

import importlib.util
import io
import json
from pathlib import Path
import socket
import sys
import threading
import time
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import httpx
import jsonschema
from PIL import Image, ImageDraw, ImageFont
import uvicorn

# Configure root paths
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import api.main as api_main
from api.main import app as gateway_app

AI_ENGINE_DIR = ROOT_DIR / "modules" / "ai-engine"
if str(AI_ENGINE_DIR) not in sys.path:
    sys.path.append(str(AI_ENGINE_DIR))

spec = importlib.util.spec_from_file_location("ai_api_live", AI_ENGINE_DIR / "api.py")
ai_api_live = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai_api_live)
ai_app = ai_api_live.app

FIXTURES_DIR = ROOT_DIR / "tests" / "fixtures"


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestEndToEndAcceptanceScenarios(unittest.TestCase):
    """Verifies all 14 acceptance criteria against the real pipeline and live AI engine."""

    @classmethod
    def setUpClass(cls):
        with open("contracts/prepared_document.schema.json", "r", encoding="utf-8") as f:
            cls.schema = json.load(f)

        with open(FIXTURES_DIR / "ground_truth.json", "r", encoding="utf-8") as f:
            cls.ground_truth = json.load(f)

        # Launch live AI Engine in background thread on a free port
        cls.port = find_free_port()
        cls.ai_url = f"http://127.0.0.1:{cls.port}"
        config = uvicorn.Config(ai_app, host="127.0.0.1", port=cls.port, log_level="error")
        cls.server = uvicorn.Server(config)
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()

        # Wait until AI engine responds
        start_wait = time.time()
        while time.time() - start_wait < 5.0:
            try:
                with httpx.Client(timeout=0.5) as client:
                    if client.get(f"{cls.ai_url}/").status_code == 200:
                        break
            except Exception:
                time.sleep(0.05)

        cls.original_ai_url = api_main.AI_ENGINE_URL
        api_main.AI_ENGINE_URL = cls.ai_url
        cls.client = TestClient(gateway_app)

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(timeout=2.0)
        api_main.AI_ENGINE_URL = cls.original_ai_url

    def _read_fixture(self, key: str) -> bytes:
        filename = self.ground_truth[key]["filename"]
        with open(FIXTURES_DIR / filename, "rb") as f:
            return f.read()

    # E2E-01: Clear, readable document
    def test_e2e_01_clear_readable_document(self):
        img_bytes = self._read_fixture("doc_01_clear_invoice")
        resp = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("invoice_clear.png", img_bytes, "image/png")},
            data={"document_id": "e2e-01-doc"},
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["processing"]["image_processing"], "success")
        self.assertEqual(payload["processing"]["ai_extraction"], "success")

        prep = payload["prepared_document"]
        self.assertIn("INVOICE", prep["text"])
        self.assertIn("INV-2026-101", prep["text"])
        self.assertGreater(prep["metadata"]["ocr_confidence"], 80.0)

        facts = payload["data"]["extracted_facts"]
        self.assertEqual(facts["invoice_number"], "INV-2026-101")
        self.assertEqual(facts["invoice_date"], "2026-10-22")
        self.assertEqual(facts["amount_due"], "4250.00")
        self.assertIn("accounts@acme-supplies.com", facts["emails"])

    # E2E-02: Noisy or low-resolution scan
    def test_e2e_02_noisy_or_low_resolution_scan(self):
        img_bytes = self._read_fixture("doc_02_noisy_lowres_invoice")
        resp = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("invoice_lowres.png", img_bytes, "image/png")},
            data={"document_id": "e2e-02-doc"},
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["status"], "success")

        # Verify upscaling was automatically performed on low-res input
        ops = payload["prepared_document"]["metadata"]["preprocessing_operations"]
        self.assertIn("upscale", ops)
        self.assertIn("autocontrast", ops)

        facts = payload["data"]["extracted_facts"]
        self.assertEqual(facts["invoice_number"], "INV-2026-088")
        self.assertEqual(facts["invoice_date"], "2026-08-15")
        self.assertEqual(facts["amount_due"], "750.00")

    # E2E-03: Skewed or rotated document
    def test_e2e_03_skewed_and_rotated_document(self):
        # 1. Skewed document
        skew_bytes = self._read_fixture("doc_03_skewed_invoice")
        resp_skew = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("invoice_skewed.png", skew_bytes, "image/png")},
            data={"document_id": "e2e-03-skew"},
        )
        self.assertEqual(resp_skew.status_code, 200)
        payload_skew = resp_skew.json()
        ops_skew = payload_skew["prepared_document"]["metadata"]["preprocessing_operations"]
        self.assertIn("deskew", ops_skew)
        self.assertEqual(payload_skew["data"]["extracted_facts"]["invoice_number"], "INV-2026-202")

        # 2. Rotated document (90 degrees)
        rot_bytes = self._read_fixture("doc_04_rotated_invoice")
        resp_rot = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("invoice_rotated.png", rot_bytes, "image/png")},
            data={"document_id": "e2e-03-rot"},
        )
        self.assertEqual(resp_rot.status_code, 200)
        payload_rot = resp_rot.json()
        ops_rot = payload_rot["prepared_document"]["metadata"]["preprocessing_operations"]
        self.assertIn("orientation_correction", ops_rot)
        self.assertEqual(payload_rot["data"]["extracted_facts"]["invoice_number"], "INV-2026-303")
        self.assertEqual(payload_rot["data"]["extracted_facts"]["amount_due"], "9200.00")

    # E2E-04: Document containing multiple paragraphs or sections
    def test_e2e_04_multiple_paragraphs_and_sections(self):
        agreement_bytes = self._read_fixture("doc_05_multiparagraph_agreement")
        resp = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("agreement.png", agreement_bytes, "image/png")},
            data={"document_id": "e2e-04-paragraphs"},
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        text = payload["prepared_document"]["text"]

        # Ensure distinct sections were preserved and not merged into a single run-on block
        self.assertIn("PROFESSIONAL SERVICES AGREEMENT", text)
        self.assertIn("1. Scope of Services", text)
        self.assertIn("2. Terms of Service and Consideration", text)
        # Paragraph boundary preserved
        self.assertIn("\n\n", text)

    # E2E-05: Supported invoice or structured business document
    def test_e2e_05_supported_invoice_structured_document(self):
        img_bytes = self._read_fixture("doc_01_clear_invoice")
        resp = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("invoice_biz.png", img_bytes, "image/png")},
            data={"document_id": "e2e-05-inv"},
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()

        self.assertEqual(payload["data"]["document_type"], "invoice")
        facts = payload["data"]["extracted_facts"]
        self.assertEqual(facts["invoice_number"], "INV-2026-101")
        self.assertEqual(facts["invoice_date"], "2026-10-22")
        self.assertEqual(facts["amount_due"], "4250.00")

        # Source evidence is captured
        evidence = payload["data"].get("field_evidence", {})
        self.assertIn("invoice_number", evidence)
        self.assertIn("INV-2026-101", evidence["invoice_number"])

    # E2E-06: Supported agreement or multiparagraph document
    def test_e2e_06_supported_agreement_without_invented_facts(self):
        agreement_bytes = self._read_fixture("doc_05_multiparagraph_agreement")
        resp = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("agreement.png", agreement_bytes, "image/png")},
            data={"document_id": "e2e-06-agree"},
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()

        self.assertEqual(payload["data"]["document_type"], "service_agreement")
        facts = payload["data"]["extracted_facts"]
        self.assertIn("legal@apextech.com", facts["emails"])
        self.assertEqual(facts["effective_date"], "2026-09-01")
        self.assertEqual(facts["contract_parties"], ["Apex Tech Consulting", "Beta Logistics Corp"])

        # Invoice number was NOT on this agreement; must remain null, never fabricated
        self.assertIsNone(facts["invoice_number"])

    # E2E-07: Empty or nearly blank image
    def test_e2e_07_empty_or_nearly_blank_image(self):
        blank_bytes = self._read_fixture("doc_06_blank")
        resp = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("blank.png", blank_bytes, "image/png")},
            data={"document_id": "e2e-07-blank"},
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["processing"]["ai_extraction"], "skipped")
        self.assertEqual(payload["data"]["document_type"], "unknown")
        self.assertEqual(payload["prepared_document"]["text"], "")
        self.assertTrue(any(w["code"] == "NO_TEXT_DETECTED" for w in payload["warnings"]))

    # E2E-08: Corrupt or unsupported file
    def test_e2e_08_corrupt_or_unsupported_file(self):
        # Unsupported file extension
        resp_unsupported = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("document.pdf", b"%PDF-1.4...", "application/pdf")},
        )
        self.assertEqual(resp_unsupported.status_code, 415)
        self.assertEqual(resp_unsupported.json()["detail"]["error"]["code"], "UNSUPPORTED_FILE_FORMAT")

        # Corrupt image payload
        corrupt_bytes = self._read_fixture("doc_07_corrupt")
        resp_corrupt = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("corrupt.png", corrupt_bytes, "image/png")},
        )
        self.assertEqual(resp_corrupt.status_code, 400)
        self.assertEqual(resp_corrupt.json()["detail"]["error"]["code"], "INVALID_IMAGE")

    # E2E-09: AI returns malformed or incomplete output
    def test_e2e_09_ai_malformed_output_normalized_safely(self):
        img_bytes = self._read_fixture("doc_01_clear_invoice")
        # Mock AI returning partial incomplete dictionary
        mock_incomplete = httpx.Response(
            status_code=200,
            json={
                "document_id": "doc-e2e-09",
                # missing classification, missing inferred_facts, partial extracted_facts
                "extracted_facts": {"invoice_number": "INV-MOCK-09"},
            },
            request=httpx.Request("POST", "http://testserver/api/v1/analyze"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_incomplete
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("invoice.png", img_bytes, "image/png")},
                data={"document_id": "doc-e2e-09"},
            )

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["status"], "success")
        # Verified that missing keys were normalized with safe defaults without crashing
        self.assertEqual(payload["data"]["extracted_facts"]["invoice_number"], "INV-MOCK-09")
        self.assertEqual(payload["data"]["extracted_facts"]["emails"], [])
        self.assertEqual(payload["data"]["classification"]["document_type"], "unknown")

    # E2E-10: OCR or AI service unavailable
    def test_e2e_10_service_unavailable_handled(self):
        img_bytes = self._read_fixture("doc_01_clear_invoice")
        with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
            resp = self.client.post(
                "/api/v1/documents/process",
                files={"file": ("invoice.png", img_bytes, "image/png")},
            )
        self.assertEqual(resp.status_code, 502)
        err = resp.json()["detail"]["error"]
        self.assertEqual(err["code"], "AI_SERVICE_UNAVAILABLE")

    # E2E-11: Large input or processing limits
    def test_e2e_11_large_input_rejected_safely(self):
        # Exceeds 10 MB limit
        large_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * (11 * 1024 * 1024)
        resp = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("too_large.png", large_bytes, "image/png")},
        )
        self.assertEqual(resp.status_code, 413)
        self.assertEqual(resp.json()["detail"]["error"]["code"], "FILE_TOO_LARGE")

    # E2E-12: Repeated uploads and consecutive requests
    def test_e2e_12_repeated_uploads_isolation(self):
        img1 = self._read_fixture("doc_01_clear_invoice")
        img2 = self._read_fixture("doc_05_multiparagraph_agreement")

        resp1 = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("doc1.png", img1, "image/png")},
            data={"document_id": "run-doc-01"},
        )
        resp2 = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("doc2.png", img2, "image/png")},
            data={"document_id": "run-doc-02"},
        )

        p1 = resp1.json()
        p2 = resp2.json()

        self.assertEqual(p1["document_id"], "run-doc-01")
        self.assertEqual(p1["data"]["document_type"], "invoice")

        self.assertEqual(p2["document_id"], "run-doc-02")
        self.assertEqual(p2["data"]["document_type"], "service_agreement")

        # Distinct run IDs and separate storage runs
        self.assertNotEqual(p1["run_id"], p2["run_id"])
        self.assertNotEqual(p1["prepared_document"]["text"], p2["prepared_document"]["text"])

    # E2E-13: Frontend-to-backend integration
    def test_e2e_13_frontend_to_backend_integration(self):
        # Frontend UI page
        resp_ui = self.client.get("/")
        self.assertEqual(resp_ui.status_code, 200)
        self.assertIn("IVP+AI", resp_ui.text)

        # Health endpoint
        resp_health = self.client.get("/api/v1/health")
        self.assertEqual(resp_health.status_code, 200)
        self.assertEqual(resp_health.json(), {"status": "ok"})

        # Intermediate stage retrieval for a processed image
        img_bytes = self._read_fixture("doc_01_clear_invoice")
        resp_proc = self.client.post(
            "/api/v1/documents/process",
            files={"file": ("inv.png", img_bytes, "image/png")},
        )
        run_id = resp_proc.json()["run_id"]
        stage_resp = self.client.get(f"/api/v1/runs/{run_id}/stages/original.png")
        self.assertEqual(stage_resp.status_code, 200)
        self.assertEqual(stage_resp.headers["content-type"], "image/png")

    # E2E-14: Regression test of existing functionality
    def test_e2e_14_regression_protection(self):
        resp_info = self.client.get("/api/v1/info")
        self.assertEqual(resp_info.status_code, 200)
        info = resp_info.json()
        self.assertEqual(info["schema_version"], "1.0")
        self.assertIn("PNG", info["supported_file_types"])

        img_bytes = self._read_fixture("doc_01_clear_invoice")
        resp_prep = self.client.post(
            "/api/v1/documents/prepare",
            files={"file": ("inv.png", img_bytes, "image/png")},
        )
        self.assertEqual(resp_prep.status_code, 200)
        # Contract schema validation
        jsonschema.validate(instance=resp_prep.json(), schema=self.schema)


if __name__ == "__main__":
    unittest.main()
