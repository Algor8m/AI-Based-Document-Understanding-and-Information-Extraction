from pathlib import Path
import sys
import unittest

AI_ENGINE_DIR = Path(__file__).resolve().parent.parent
if str(AI_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_DIR))

from src.document_classifier import classify_document
from src.analyzer import analyze_document


class TestDocumentClassifier(unittest.TestCase):

    def test_service_agreement(self):
        result = classify_document(
            "Service Agreement: Terms of Service"
        )
        self.assertEqual(
            result["document_type"],
            "service_agreement",
        )

    def test_invoice(self):
        result = classify_document(
            "Invoice Number: INV-101. Amount Due: 500"
        )
        self.assertEqual(result["document_type"], "invoice")

    def test_general_document(self):
        result = classify_document("Notes from the meeting")
        self.assertEqual(
            result["document_type"],
            "general_document",
        )

    def test_classifier_is_integrated_into_analyzer(self):
        result = analyze_document(
            "invoice-001",
            "Invoice Number: INV-101. Amount Due: 500",
        )

        self.assertEqual(
            result["classification"]["document_type"],
            "invoice",
        )
        self.assertEqual(
            result["inferred_facts"]["document_type"],
            "invoice",
        )
    
    def test_invoice_keyword_variations(self):
        examples = [
            "Invoice for consulting services",
            "Bill to: ABC Company. Total Payable: 500",
            "Payment due for invoice 123",
        ]

        for text in examples:
            with self.subTest(text=text):
                result = classify_document(text)
                self.assertEqual(
                    result["document_type"],
                    "invoice",
                )

    def test_service_agreement_keyword_variations(self):
        examples = [
            "Contract for services between two parties",
            "Scope of work and service provider responsibilities",
            "Terms of service for the customer",
        ]

        for text in examples:
            with self.subTest(text=text):
                result = classify_document(text)
                self.assertEqual(
                    result["document_type"],
                    "service_agreement",
                )

    def test_ambiguous_document_returns_general(self):
        text = (
            "Invoice and service agreement: "
            "amount due and scope of services"
        )

        result = classify_document(text)

        self.assertEqual(
            result["document_type"],
            "general_document",
        )
        self.assertEqual(result["confidence"], "low")


if __name__ == "__main__":
    unittest.main()
