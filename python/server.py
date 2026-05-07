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
import time
from functools import lru_cache
from typing import cast

from fastapi import FastAPI, HTTPException, Request
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
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ---------------------------------------------------------------------------
# Minimal auth + rate limiting + request limits
# ---------------------------------------------------------------------------

_PYTHON_API_KEY = os.environ.get("PYTHON_API_KEY", "").strip()

_MAX_IMAGE_BYTES = int(os.environ.get("MAX_IMAGE_BYTES", str(4 * 1024 * 1024)))

_INCLUDE_CLAUDE_PROMPT = os.environ.get("INCLUDE_CLAUDE_PROMPT", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

_RATE_WINDOW_S = int(os.environ.get("RATE_WINDOW_S", str(60 * 60)))
_RATE_MAX_REQUESTS = int(os.environ.get("RATE_MAX_REQUESTS", "60"))
_rate_store: dict[str, list[float]] = {}


def _client_ip(req: Request) -> str:
    xff = req.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    xrip = req.headers.get("x-real-ip")
    if xrip:
        return xrip.strip()
    host = getattr(req.client, "host", None)
    return host or "unknown"


def _require_auth(req: Request) -> None:
    if not _PYTHON_API_KEY:
        # Auth disabled (e.g. local dev). Recommended to set in prod.
        return
    auth = req.headers.get("authorization") or ""
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth.removeprefix("Bearer ").strip()
    if token != _PYTHON_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API token")


def _check_rate_limit(ip: str) -> None:
    # In-memory sliding window. Good enough for single-instance Railway dev/test.
    now = time.time()
    cutoff = now - _RATE_WINDOW_S
    ts = [t for t in _rate_store.get(ip, []) if t > cutoff]
    if len(ts) >= _RATE_MAX_REQUESTS:
        retry_after = int(ts[0] + _RATE_WINDOW_S - now)
        raise HTTPException(
            status_code=429,
            detail={"error": "Rate limit exceeded", "retry_after_seconds": max(1, retry_after)},
            headers={"Retry-After": str(max(1, retry_after))},
        )
    ts.append(now)
    _rate_store[ip] = ts


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
        "digitizer_method": digitized["method"],
        "leads_available": list(digitized["signals"].keys()),
        "sampling_rate": digitized["sampling_rate"],
        "pipeline_classification": pipeline_classification,
    }
    if _INCLUDE_CLAUDE_PROMPT:
        result["claude_prompt"] = prompt
    return json.dumps(result, cls=NumpyEncoder)


class AnalyzeRequest(BaseModel):
    image_base64: str
    media_type: str = "image/png"


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(req: AnalyzeRequest, request: Request) -> dict[str, object]:
    request_id = id(req)
    _require_auth(request)
    ip = _client_ip(request)
    _check_rate_limit(ip)

    try:
        # Fast reject obviously oversized payloads before decoding
        approx_bytes = int(len(req.image_base64) * 0.75)
        if approx_bytes > _MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Image too large")

        # validate=True rejects non-base64 alphabet characters
        image_bytes = base64.b64decode(req.image_base64, validate=True)
    except Exception as e:
        logger.warning(f"[{request_id}] Invalid base64: {type(e).__name__}")
        raise HTTPException(status_code=400, detail="image_base64 is not valid base64")

    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image too large")

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
