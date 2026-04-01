#!/usr/bin/env python3
"""
FastAPI HTTP wrapper around the ECG analysis pipeline.

Endpoints:
  GET  /healthz          — liveness probe
  POST /analyze          — digitize + measure an ECG image

Deploy:
  uvicorn server:app --host 0.0.0.0 --port 8000
"""

import base64
import json
import os
import tempfile
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analyze_ecg import (
    _NumpyEncoder,
    analyze_signal,
    build_claude_prompt,
    digitize_image,
)

app = FastAPI(title="EKG Trainer — Python Pipeline", version="1.0.0")

# Allow requests from the Next.js server (same-origin in prod, localhost in dev)
_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


class AnalyzeRequest(BaseModel):
    image_base64: str
    media_type: str = "image/png"


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    # Decode base64 → temp file
    ext = req.media_type.split("/")[-1].replace("jpeg", "jpg")
    tmp_path = None
    try:
        image_bytes = base64.b64decode(req.image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="image_base64 is not valid base64")

    try:
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
            f.write(image_bytes)
            tmp_path = f.name

        # Step 1: digitize
        digitized = digitize_image(tmp_path)

        # Step 2: measure
        measurements = analyze_signal(digitized["signals"], digitized["sampling_rate"])

        # Step 3: build Claude prompt
        prompt = build_claude_prompt(measurements, digitized["method"])

        result = {
            "success": True,
            "measurements": measurements,
            "claude_prompt": prompt,
            "digitizer_method": digitized["method"],
            "leads_available": list(digitized["signals"].keys()),
            "sampling_rate": digitized["sampling_rate"],
        }
        # Use NumpyEncoder to serialize any remaining numpy scalars
        return json.loads(json.dumps(result, cls=_NumpyEncoder))

    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

    finally:
        if tmp_path and Path(tmp_path).exists():
            Path(tmp_path).unlink(missing_ok=True)
