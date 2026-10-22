"""Tests for the image preparation and root API endpoints."""

import io
import json
import unittest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
import jsonschema

from api.main import app


class TestDocumentPreparationAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        with open("contracts/prepared_document.schema.json") as f:
            cls.schema = json.load(f)

    def test_health(self):
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_info(self):
        resp = self.client.get("/api/v1/info")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["schema_version"], "1.0")
        self.assertIn("PNG", data["supported_file_types"])
        self.assertIn("JPEG", data["supported_file_types"])
        self.assertIn("prepare", data["endpoints"])
        self.assertIn("process", data["endpoints"])

    def test_prepare_success_schema_compliance(self):
        img = Image.new("RGB", (600, 200), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), "Sample Document Text", fill="black")
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        resp = self.client.post(
            "/api/v1/documents/prepare",
            files={"file": ("sample.png", buf.getvalue(), "image/png")},
            data={"document_id": "doc-prep-001"},
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["document_id"], "doc-prep-001")
        self.assertIn("Sample", payload["text"])

        # Validate against JSON schema
        jsonschema.validate(instance=payload, schema=self.schema)

    def test_prepare_blank_image(self):
        img = Image.new("RGB", (200, 200), color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        resp = self.client.post(
            "/api/v1/documents/prepare",
            files={"file": ("blank.png", buf.getvalue(), "image/png")},
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["text"], "")
        self.assertEqual(len(payload["warnings"]), 1)
        self.assertEqual(payload["warnings"][0]["code"], "NO_TEXT_DETECTED")
        jsonschema.validate(instance=payload, schema=self.schema)

    def test_prepare_unsupported_file(self):
        resp = self.client.post(
            "/api/v1/documents/prepare",
            files={"file": ("file.txt", b"plain text", "text/plain")},
        )
        self.assertEqual(resp.status_code, 415)
        self.assertEqual(resp.json()["detail"]["error"]["code"], "UNSUPPORTED_FILE_FORMAT")

    def test_prepare_corrupt_file(self):
        resp = self.client.post(
            "/api/v1/documents/prepare",
            files={"file": ("corrupt.png", b"not a png", "image/png")},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"]["error"]["code"], "INVALID_IMAGE")


if __name__ == "__main__":
    unittest.main()
