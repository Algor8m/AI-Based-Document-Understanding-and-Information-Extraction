"""Benchmark script calculating empirical CER, WER, field-level accuracy, and timings for IVP+AI."""

import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time
from typing import Any

from fastapi.testclient import TestClient
import httpx
import uvicorn

# Configure root path first
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import gateway API first
import api.main as api_main
from api.main import app as gateway_app

# Import AI Engine API
AI_ENGINE_DIR = ROOT_DIR / "modules" / "ai-engine"
if str(AI_ENGINE_DIR) not in sys.path:
    sys.path.append(str(AI_ENGINE_DIR))

ai_engine_path = (AI_ENGINE_DIR / "api.py").resolve()
spec = importlib.util.spec_from_file_location("ai_api_live", ai_engine_path)
ai_api_live = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai_api_live)
ai_app = ai_api_live.app

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute standard Levenshtein distance between two sequences."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def compute_cer(reference: str, hypothesis: str) -> float:
    """Compute Character Error Rate (CER)."""
    ref_norm = " ".join(reference.split())
    hyp_norm = " ".join(hypothesis.split())
    if not ref_norm:
        return 0.0 if not hyp_norm else 1.0
    dist = levenshtein_distance(ref_norm, hyp_norm)
    return min(1.0, dist / len(ref_norm))


def compute_wer(reference: str, hypothesis: str) -> float:
    """Compute Word Error Rate (WER)."""
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    dist = levenshtein_distance(ref_words, hyp_words)
    return min(1.0, dist / len(ref_words))


def run_benchmark():
    gt_path = FIXTURES_DIR / "ground_truth.json"
    with open(gt_path, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    # 1. Start real AI Engine in background thread
    port = find_free_port()
    ai_url = f"http://127.0.0.1:{port}"
    config = uvicorn.Config(ai_app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for AI server to be ready
    start_wait = time.time()
    while time.time() - start_wait < 5.0:
        try:
            with httpx.Client(timeout=0.5) as hclient:
                r = hclient.get(f"{ai_url}/")
                if r.status_code == 200:
                    break
        except Exception:
            time.sleep(0.05)

    # Point gateway to live AI engine
    orig_url = api_main.AI_ENGINE_URL
    api_main.AI_ENGINE_URL = ai_url
    client = TestClient(gateway_app)

    results = []
    total_evaluated_fields = 0
    correctly_extracted_fields = 0
    total_valid_docs = 0
    successful_runs = 0

    print("=" * 80)
    print("IVP+AI SYSTEM PERFORMANCE BENCHMARK (REAL PIPELINE + TESSERACT OCR + AI ENGINE)")
    print("=" * 80)

    try:
        for doc_id, doc_meta in ground_truth.items():
            filename = doc_meta["filename"]
            file_path = FIXTURES_DIR / filename
            if not file_path.exists():
                continue

            with open(file_path, "rb") as f:
                file_bytes = f.read()

            is_corrupt = "corrupt" in doc_id

            if not is_corrupt:
                total_valid_docs += 1

            t0 = time.perf_counter()
            resp = client.post(
                "/api/v1/documents/process",
                files={"file": (filename, file_bytes, "image/png")},
                data={"document_id": f"bench-{doc_id}"},
            )
            total_time_ms = round((time.perf_counter() - t0) * 1000, 2)

            record: dict[str, Any] = {
                "test_id": doc_id,
                "filename": filename,
                "description": doc_meta["description"],
                "status_code": resp.status_code,
                "total_time_ms": total_time_ms,
            }

            if is_corrupt:
                record["expected_rejection"] = True
                record["rejection_success"] = (resp.status_code in (400, 415))
                if record["rejection_success"]:
                    successful_runs += 1
                print(f"[{doc_id}] Corrupt file correctly rejected with code {resp.status_code}")
                results.append(record)
                continue

            if resp.status_code != 200:
                record["success"] = False
                record["error"] = resp.text
                print(f"[{doc_id}] FAILED with code {resp.status_code}: {resp.text}")
                results.append(record)
                continue

            payload = resp.json()
            record["success"] = True
            successful_runs += 1

            data = payload.get("data", {})
            prep = payload.get("prepared_document", {})
            ocr_text = prep.get("text", "")
            ocr_meta = prep.get("metadata", {})
            extracted_facts = data.get("extracted_facts", {})
            doc_type = data.get("document_type", "unknown")

            record["ocr_status"] = payload.get("processing", {}).get("image_processing")
            record["ai_status"] = payload.get("processing", {}).get("ai_extraction")
            record["ocr_confidence"] = ocr_meta.get("ocr_confidence", 0.0)
            record["preprocessing_operations"] = ocr_meta.get("preprocessing_operations", [])
            record["ocr_duration_ms"] = ocr_meta.get("processing_duration_ms", 0.0)

            # CER & WER on complete reference text
            ref_text = doc_meta.get("reference_text", "")
            if ref_text:
                cer = compute_cer(ref_text, ocr_text)
                wer = compute_wer(ref_text, ocr_text)
                record["cer"] = round(cer, 4)
                record["wer"] = round(wer, 4)
            else:
                record["cer"] = 0.0 if not ocr_text else 1.0
                record["wer"] = 0.0 if not ocr_text else 1.0

            # Field evaluation
            expected_fields = doc_meta.get("expected_fields", {})
            field_matches = {}
            for field_name, expected_val in expected_fields.items():
                actual_val = extracted_facts.get(field_name)
                total_evaluated_fields += 1
                if expected_val is None:
                    matched = actual_val is None or actual_val == "" or actual_val == []
                elif isinstance(expected_val, list):
                    matched = all(item in (actual_val or []) for item in expected_val)
                else:
                    matched = str(actual_val).strip().lower() == str(expected_val).strip().lower()

                field_matches[field_name] = {
                    "expected": expected_val,
                    "actual": actual_val,
                    "matched": matched,
                }
                if matched:
                    correctly_extracted_fields += 1

            record["field_matches"] = field_matches
            record["document_type_matched"] = (doc_type == doc_meta.get("expected_document_type"))

            print(f"[{doc_id}] Success: DocType={doc_type} (expected {doc_meta.get('expected_document_type')}) | "
                  f"OCR Conf={record['ocr_confidence']}% | CER={record.get('cer', 0.0)} | Time={total_time_ms}ms")
            results.append(record)

    finally:
        server.should_exit = True
        thread.join(timeout=2.0)
        api_main.AI_ENGINE_URL = orig_url

    field_accuracy = round((correctly_extracted_fields / total_evaluated_fields) * 100, 2) if total_evaluated_fields else 0.0
    e2e_success_rate = round((successful_runs / (total_valid_docs + 1)) * 100, 2)

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_documents_tested": len(results),
        "total_valid_documents": total_valid_docs,
        "total_evaluated_fields": total_evaluated_fields,
        "correctly_extracted_fields": correctly_extracted_fields,
        "field_level_accuracy_pct": field_accuracy,
        "end_to_end_success_rate_pct": e2e_success_rate,
        "results": results,
    }

    out_file = FIXTURES_DIR.parent / "benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("-" * 80)
    print("BENCHMARK SUMMARY:")
    print(f"  Total Valid Documents: {total_valid_docs}")
    print(f"  End-to-End Success Rate: {e2e_success_rate}%")
    print(f"  Field-Level Accuracy: {field_accuracy}% ({correctly_extracted_fields}/{total_evaluated_fields})")
    print(f"  Detailed Results Saved: {out_file}")
    print("=" * 80)
    return summary


if __name__ == "__main__":
    run_benchmark()
