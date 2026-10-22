"""Generate reproducible test fixture images and ground truth JSON for IVP+AI acceptance testing."""

import json
from pathlib import Path
import random
from PIL import Image, ImageDraw, ImageFont

FIXTURES_DIR = Path(__file__).resolve().parent


def generate_fixtures():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    font_large = ImageFont.load_default(size=24)
    font_medium = ImageFont.load_default(size=20)

    # 1. Clear High-Resolution Invoice
    img1 = Image.new("RGB", (1000, 500), color="white")
    draw1 = ImageDraw.Draw(img1)
    text1 = (
        "ACME SUPPLIES INC\n"
        "INVOICE\n"
        "Invoice Number: INV-2026-101\n"
        "Invoice Date: 2026-10-22\n"
        "Amount Due: $4,250.00\n"
        "Contact: accounts@acme-supplies.com\n"
        "Phone: +1 (555) 234-5678\n"
        "Bill To: Global Distribution LLC"
    )
    draw1.text((50, 50), text1, font=font_large, fill="black")
    p1 = FIXTURES_DIR / "doc_01_clear_invoice.png"
    img1.save(p1, format="PNG")

    # 2. Noisy / Low-Resolution Invoice (< 1000px, slight noise)
    img2 = Image.new("RGB", (480, 220), color=(240, 240, 240))
    draw2 = ImageDraw.Draw(img2)
    text2 = (
        "INVOICE\n"
        "Invoice Number: INV-2026-088\n"
        "Invoice Date: 2026-08-15\n"
        "Amount Due: $750.00\n"
        "Contact: support@lowres-sample.com"
    )
    draw2.text((25, 25), text2, font=font_medium, fill=(20, 20, 20))
    random.seed(42)
    pixels = img2.load()
    for _ in range(300):
        rx = random.randint(0, 479)
        ry = random.randint(0, 219)
        c = random.randint(180, 250)
        pixels[rx, ry] = (c, c, c)
    p2 = FIXTURES_DIR / "doc_02_noisy_lowres_invoice.png"
    img2.save(p2, format="PNG")

    # 3. Skewed Invoice (6 degrees tilt)
    base_skew = Image.new("RGB", (1000, 550), color="white")
    draw_skew = ImageDraw.Draw(base_skew)
    text3 = (
        "SKEW LOGISTICS CORP\n"
        "INVOICE\n"
        "Invoice Number: INV-2026-202\n"
        "Invoice Date: 2026-11-10\n"
        "Amount Due: $1,800.00\n"
        "Contact: billing@skew-corp.com\n"
        "Total Payable: $1,800.00\n"
        "Payment terms: Net 30"
    )
    draw_skew.text((60, 60), text3, font=font_large, fill="black")
    img3 = base_skew.rotate(-6, resample=Image.Resampling.BILINEAR, fillcolor="white")
    p3 = FIXTURES_DIR / "doc_03_skewed_invoice.png"
    img3.save(p3, format="PNG")

    # 4. Rotated Invoice (90 degrees counter-clockwise)
    base_rot = Image.new("RGB", (1100, 700), color="white")
    draw_rot = ImageDraw.Draw(base_rot)
    lines_rot = [
        "ENTERPRISE BILLING STATEMENT",
        "INVOICE",
        "Invoice Number: INV-2026-303",
        "Invoice Date: 2026-12-05",
        "Amount Due: $9,200.00",
        "Bill To: Orion Innovations",
        "Contact: finance@enterprise-billing.com",
        "Scope of services completed per agreement terms.",
        "Payment instructions: Electronic wire transfer within 15 days.",
        "Thank you for choosing Enterprise Billing Solutions.",
    ]
    draw_rot.text((60, 60), "\n".join(lines_rot), font=font_large, fill="black")
    img4 = base_rot.rotate(90, expand=True)
    p4 = FIXTURES_DIR / "doc_04_rotated_invoice.png"
    img4.save(p4, format="PNG")

    # 5. Multiparagraph Service Agreement
    img5 = Image.new("RGB", (1100, 750), color="white")
    draw5 = ImageDraw.Draw(img5)
    text5 = (
        "PROFESSIONAL SERVICES AGREEMENT\n\n"
        "This agreement is made between Apex Tech Consulting and Beta Logistics Corp.\n"
        "Effective Date: 2026-09-01\n"
        "Contact: legal@apextech.com\n\n"
        "1. Scope of Services\n"
        "The service provider shall deliver cloud architecture, automated data pipelines,\n"
        "and ongoing system support. Both parties agree to adherence with project milestones.\n\n"
        "2. Terms of Service and Consideration\n"
        "The client agrees to the terms of service set forth herein.\n"
        "Total Payable: $15,000.00\n"
        "Invoices shall be rendered upon completion of each agreed milestone."
    )
    draw5.text((50, 40), text5, font=font_medium, fill="black")
    p5 = FIXTURES_DIR / "doc_05_multiparagraph_agreement.png"
    img5.save(p5, format="PNG")

    # 6. Blank document
    img6 = Image.new("RGB", (400, 400), color="white")
    p6 = FIXTURES_DIR / "doc_06_blank.png"
    img6.save(p6, format="PNG")

    # 7. Corrupt image file
    p7 = FIXTURES_DIR / "doc_07_corrupt.png"
    with open(p7, "wb") as f:
        f.write(b"NOT_A_VALID_PNG_CONTENT_1234567890")

    # Ground truth mapping with complete reference text
    ground_truth = {
        "doc_01_clear_invoice": {
            "filename": "doc_01_clear_invoice.png",
            "description": "Clear high-resolution business invoice",
            "reference_text": text1,
            "expected_document_type": "invoice",
            "expected_fields": {
                "invoice_number": "INV-2026-101",
                "invoice_date": "2026-10-22",
                "amount_due": "4250.00",
                "emails": ["accounts@acme-supplies.com"],
            },
        },
        "doc_02_noisy_lowres_invoice": {
            "filename": "doc_02_noisy_lowres_invoice.png",
            "description": "Low-resolution scanned invoice needing upscale & contrast",
            "reference_text": text2,
            "expected_document_type": "invoice",
            "expected_fields": {
                "invoice_number": "INV-2026-088",
                "invoice_date": "2026-08-15",
                "amount_due": "750.00",
                "emails": ["support@lowres-sample.com"],
            },
        },
        "doc_03_skewed_invoice": {
            "filename": "doc_03_skewed_invoice.png",
            "description": "Invoice skewed by -6 degrees needing deskewing",
            "reference_text": text3,
            "expected_document_type": "invoice",
            "expected_fields": {
                "invoice_number": "INV-2026-202",
                "invoice_date": "2026-11-10",
                "amount_due": "1800.00",
                "emails": ["billing@skew-corp.com"],
            },
        },
        "doc_04_rotated_invoice": {
            "filename": "doc_04_rotated_invoice.png",
            "description": "Invoice rotated 90 degrees needing visual orientation correction",
            "reference_text": "\n".join(lines_rot),
            "expected_document_type": "invoice",
            "expected_fields": {
                "invoice_number": "INV-2026-303",
                "invoice_date": "2026-12-05",
                "amount_due": "9200.00",
            },
        },
        "doc_05_multiparagraph_agreement": {
            "filename": "doc_05_multiparagraph_agreement.png",
            "description": "Multi-paragraph service agreement with sections",
            "reference_text": text5,
            "expected_document_type": "service_agreement",
            "expected_fields": {
                "contract_parties": ["Apex Tech Consulting", "Beta Logistics Corp"],
                "effective_date": "2026-09-01",
                "amount_due": "15000.00",
                "emails": ["legal@apextech.com"],
            },
        },
        "doc_06_blank": {
            "filename": "doc_06_blank.png",
            "description": "Blank white image with no readable text",
            "reference_text": "",
            "expected_document_type": "unknown",
            "expected_fields": {
                "invoice_number": None,
                "invoice_date": None,
                "amount_due": None,
                "emails": [],
            },
        },
        "doc_07_corrupt": {
            "filename": "doc_07_corrupt.png",
            "description": "Corrupt file payload with PNG extension",
            "reference_text": "",
            "expected_document_type": None,
            "expected_fields": {},
        },
    }

    gt_path = FIXTURES_DIR / "ground_truth.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    print("Fixtures and ground truth updated successfully at:", FIXTURES_DIR)


if __name__ == "__main__":
    generate_fixtures()
