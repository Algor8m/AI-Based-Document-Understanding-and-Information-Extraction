
import unittest

from src.extractor import extract_facts
from src.analyzer import analyze_document


class TestInvoiceExtraction(unittest.TestCase):
    def setUp(self):
        self.invoice_text = (
            "INVOICE\n"
            "Invoice Number: INV-2026-001\n"
            "Invoice Date: 2026-10-20\n"
            "Amount Due: INR 12,500.00\n"
            "Contact: billing@example.com"
        )

    def test_extract_invoice_fields(self):
        facts = extract_facts(self.invoice_text)

        self.assertEqual(
            facts["invoice_number"], "INV-2026-001"
        )
        self.assertEqual(
            facts["invoice_date"], "2026-10-20"
        )
        self.assertEqual(
            facts["amount_due"], "12500.00"
        )

    def test_missing_invoice_fields_return_none(self):
        facts = extract_facts(
            "This is a general document with no invoice details."
        )

        self.assertIsNone(facts["invoice_number"])
        self.assertIsNone(facts["invoice_date"])
        self.assertIsNone(facts["amount_due"])

    def test_invoice_fields_reach_analyzer_response(self):
        result = analyze_document(
            "invoice-test-001",
            self.invoice_text,
        )

        self.assertEqual(
            result["extracted_facts"]["invoice_number"],
            "INV-2026-001",
        )
        self.assertEqual(
            result["extracted_facts"]["invoice_date"],
            "2026-10-20",
        )
        self.assertEqual(
            result["extracted_facts"]["amount_due"],
            "12500.00",
        )


if __name__ == "__main__":
    unittest.main()
