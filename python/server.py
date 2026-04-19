#!/usr/bin/env python3
"""
FastAPI HTTP wrapper around the ECG analysis pipeline.

Endpoints:
  GET  /healthz          — liveness probe
  POST /analyze          — digitize + measure an ECG image

Deploy:
  uvicorn server:app --host 0.0.0.0 --port 8000
"""

import asyncio
import base64
import functools
import hashlib
import json
import logging
import os
from functools import lru_cache
from typing import cast

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analyze_ecg import (
    NumpyEncoder,
    analyze_signal,
    build_claude_prompt,
    digitize_image,
    run_pipeline_classification,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="EKG Trainer — Python Pipeline", version="1.0.0")

_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

# ---------------------------------------------------------------------------
# SHA-256-keyed LRU response cache
# Avoids reprocessing the same image bytes twice within a server lifetime.
# ---------------------------------------------------------------------------
_CACHE_MAX = int(os.environ.get("ANALYZE_CACHE_SIZE", "128"))

@lru_cache(maxsize=_CACHE_MAX)
def _cached_analyze(image_hash: str, image_bytes: bytes) -> str:
    """
    Run the full analysis pipeline and return JSON string.
    Keyed by SHA-256 hash so identical image bytes are never reprocessed.
    The bytes argument is included so lru_cache uses it as the actual cache key
    (the hash alone could theoretically collide).
    """
    digitized = digitize_image(image_bytes=image_bytes)

    measurements = analyze_signal(
        digitized["signals"],
        digitized["sampling_rate"],
        calibrated=digitized.get("calibrated", False),
    )

    pipeline_classification = run_pipeline_classification(
        digitized["signals"],
        digitized["sampling_rate"],
        precomputed_rpeaks=measurements.get("r_peaks"),  # avoid re-detecting R-peaks
        precomputed_fs=digitized["sampling_rate"],
    )

    prompt = build_claude_prompt(
        measurements, digitized["method"], pipeline_classification
    )

    result: dict[str, object] = {
        "success": True,
        "measurements": measurements,
        "claude_prompt": prompt,
        "digitizer_method": digitized["method"],
        "leads_available": list(digitized["signals"].keys()),
        "sampling_rate": digitized["sampling_rate"],
        "pipeline_classification": pipeline_classification,
    }
    return json.dumps(result, cls=NumpyEncoder)


class AnalyzeRequest(BaseModel):
    image_base64: str
    media_type: str = "image/png"


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(req: AnalyzeRequest) -> dict[str, object]:
    request_id = id(req)
    try:
        image_bytes = base64.b64decode(req.image_base64)
    except Exception as e:
        logger.warning(f"[{request_id}] Invalid base64: {type(e).__name__}")
        raise HTTPException(status_code=400, detail="image_base64 is not valid base64")

    image_hash = hashlib.sha256(image_bytes).hexdigest()

    try:
        # Run blocking CPU work in a thread pool so the event loop stays free.
        result_json = await asyncio.to_thread(
            _cached_analyze, image_hash, image_bytes
        )
        return cast(dict[str, object], json.loads(result_json))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[{request_id}] Analysis failed: {type(e).__name__}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Check logs for details.",
        )
