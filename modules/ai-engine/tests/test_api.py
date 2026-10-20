
import unittest

from fastapi.testclient import TestClient
from api import app


class TestDocumentAnalysisAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "running")

    def test_analyze_document(self):
        response = self.client.post(
            "/api/v1/analyze",
            json={
                "document_id": "test-001",
                "text": (
                    "Service Agreement\n"
                    "Date: 2026-10-20\n"
                    "Contact: test@example.com"
                ),
            },
        )

        self.assertEqual(response.status_code, 200)

        result = response.json()

        self.assertEqual(result["document_id"], "test-001")
        self.assertIn(
            "test@example.com",
            result["extracted_facts"]["emails"],
        )
        self.assertTrue(
            result["inferred_facts"]["has_contact_method"]
        )
        self.assertEqual(len(result["reasoning"]), 2)

    def test_empty_text_is_rejected(self):
        response = self.client.post(
            "/api/v1/analyze",
            json={
                "document_id": "test-002",
                "text": "",
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_missing_document_id_is_rejected(self):
        response = self.client.post(
            "/api/v1/analyze",
            json={"text": "Sample document"},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
