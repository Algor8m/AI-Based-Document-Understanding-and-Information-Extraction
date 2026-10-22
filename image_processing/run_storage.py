"""Secure, controlled storage for document processing runs and intermediate images."""

import os
from pathlib import Path
import re
import shutil
import time
from typing import Any

from PIL import Image

RUNS_DIR = Path(os.getenv("IVP_RUNS_DIR", "data/runs")).resolve()
UUID_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
STAGE_FILENAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]+\.png$")


def init_storage() -> Path:
    """Ensure the runs storage directory exists."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    return RUNS_DIR


def save_run_stages(
    run_id: str,
    stages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Save intermediate Pillow images to disk in a run-specific directory."""
    if not UUID_REGEX.match(run_id):
        raise ValueError(f"Invalid run_id format: {run_id}")

    init_storage()
    run_path = (RUNS_DIR / run_id).resolve()
    run_path.mkdir(parents=True, exist_ok=True)

    stage_metadata: list[dict[str, Any]] = []

    for stage_info in stages:
        stage_name = stage_info["stage"]
        safe_filename = f"{stage_name}.png"
        img_path = run_path / safe_filename

        img: Image.Image = stage_info["image"]
        # Save as PNG
        img.save(img_path, format="PNG")

        stage_metadata.append({
            "stage": stage_name,
            "title": stage_info.get("title", stage_name),
            "description": stage_info.get("description", ""),
            "dimensions": stage_info.get("dimensions", [img.width, img.height]),
            "image_url": f"/api/v1/runs/{run_id}/stages/{safe_filename}",
            "is_ocr_input": bool(stage_info.get("is_ocr_input", False)),
        })

    # Trigger opportunistic cleanup of old runs
    cleanup_old_runs()

    return stage_metadata


def get_stage_image_path(run_id: str, filename: str) -> Path:
    """Locate and validate an intermediate stage image with strict path traversal checks."""
    if not UUID_REGEX.match(run_id):
        raise ValueError("Invalid run identifier format.")

    if not STAGE_FILENAME_REGEX.match(filename):
        raise ValueError("Invalid stage filename format.")

    run_dir = (RUNS_DIR / run_id).resolve()
    target_path = (run_dir / filename).resolve()

    # Verify target path is strictly inside run_dir
    try:
        target_path.relative_to(run_dir)
    except ValueError:
        raise ValueError("Path traversal attempt detected.")

    if not target_path.is_file():
        raise FileNotFoundError(f"Stage image {filename} not found for run {run_id}.")

    return target_path


def cleanup_old_runs(max_age_seconds: int = 7200, max_runs: int = 100) -> int:
    """Prune runs older than max_age_seconds or when total runs exceed max_runs."""
    if not RUNS_DIR.exists():
        return 0

    removed = 0
    now = time.time()

    try:
        run_dirs = [d for d in RUNS_DIR.iterdir() if d.is_dir() and UUID_REGEX.match(d.name)]
        # Sort by last modification time (oldest first)
        run_dirs.sort(key=lambda d: d.stat().st_mtime)

        for d in run_dirs:
            age = now - d.stat().st_mtime
            if age > max_age_seconds or len(run_dirs) - removed > max_runs:
                shutil.rmtree(d, ignore_errors=True)
                removed += 1
    except Exception:
        # Pruning failure should not block core requests
        pass

    return removed
