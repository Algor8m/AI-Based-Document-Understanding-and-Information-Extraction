"""Full live end-to-end integration test with both services running live over HTTP."""

import io
import socket
import threading
import time
import unittest

from fastapi.testclient import TestClient
import httpx
from PIL import Image, ImageDraw, ImageFont
import uvicorn

import api.main as api_main
from api.main import app as gateway_app


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestLiveEndToEnd(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # 1. Import AI engine app
        import importlib.util
        from pathlib import Path

        ai_engine_path = Path("modules/ai-engine/api.py").resolve()
        spec = importlib.util.spec_from_file_location("ai_api_live", ai_engine_path)
        ai_api_live = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ai_api_live)
        cls.ai_app = ai_api_live.app

        # 2. Pick a free port and launch AI engine in a background thread
        cls.port = find_free_port()
        cls.ai_url = f"http://127.0.0.1:{cls.port}"

        config = uvicorn.Config(
            cls.ai_app,
            host="127.0.0.1",
            port=cls.port,
            log_level="error",
        )
        cls.server = uvicorn.Server(config)
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()

        # Wait until AI engine server responds
        start_time = time.time()
        while time.time() - start_time < 5.0:
            try:
                with httpx.Client(timeout=1.0) as client:
                    resp = client.get(f"{cls.ai_url}/")
                    if resp.status_code == 200:
                        break
            except Exception:
                time.sleep(0.05)

        # 3. Configure gateway API to talk to this live AI engine port
        cls.original_url = api_main.AI_ENGINE_URL
        api_main.AI_ENGINE_URL = cls.ai_url
        cls.gateway_client = TestClient(gateway_app)

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(timeout=2.0)
        api_main.AI_ENGINE_URL = cls.original_url

    def test_live_invoice_end_to_end(self):
        # Generate an invoice image with clean scalable font
        font = ImageFont.load_default(size=24)
        img = Image.new("RGB", (900, 400), color="white")
        draw = ImageDraw.Draw(img)
        draw.text(
            (40, 40),
            "INVOICE\n"
            "Invoice Number: INV-2026-999\n"
            "Invoice Date: 2026-10-21\n"
            "Amount Due: INR 54000.00\n"
            "Contact: accounts@enterprise.com",
            font=font,
            fill="black",
        )
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        resp = self.gateway_client.post(
            "/api/v1/documents/process",
            files={"file": ("live_invoice.png", buf.getvalue(), "image/png")},
            data={"document_id": "live-inv-001"},
        )

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()

        self.assertEqual(payload["document_id"], "live-inv-001")
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["processing"]["image_processing"], "success")
        self.assertEqual(payload["processing"]["ai_extraction"], "success")

        # Verify classification by the live AI engine
        self.assertEqual(payload["data"]["document_type"], "invoice")
        self.assertEqual(payload["data"]["classification"]["document_type"], "invoice")

        # Verify extracted facts by the live AI engine
        facts = payload["data"]["extracted_facts"]
        self.assertEqual(facts["invoice_number"], "INV-2026-999")
        self.assertEqual(facts["invoice_date"], "2026-10-21")
        self.assertEqual(facts["amount_due"], "54000.00")
        self.assertIn("accounts@enterprise.com", facts["emails"])

        # Verify rule reasoning by the live AI engine
        self.assertTrue(payload["data"]["inferred_facts"]["has_contact_method"])
        self.assertTrue(len(payload["data"]["reasoning"]) >= 2)

        # Verify real intermediate images were generated and retrievable
        stages = payload.get("intermediate_images", [])
        self.assertGreater(len(stages), 0)
        run_id = payload["run_id"]
        stage_resp = self.gateway_client.get(f"/api/v1/runs/{run_id}/stages/original.png")
        self.assertEqual(stage_resp.status_code, 200)
        self.assertEqual(stage_resp.headers["content-type"], "image/png")


if __name__ == "__main__":
    unittest.main()
