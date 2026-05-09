"""
FastAPI server behavior: auth, payload limits, rate limiting (no full digitizer path).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_PY_ROOT = Path(__file__).resolve().parents[1]
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

import server as srv  # noqa: E402


@pytest.fixture
def clear_rate_store():
    srv._rate_store.clear()
    yield
    srv._rate_store.clear()


def test_healthz(clear_rate_store, monkeypatch):
    monkeypatch.setattr(srv, "_PYTHON_API_KEY", "")
    monkeypatch.setattr(srv, "_RATE_MAX_REQUESTS", 1000)
    client = TestClient(srv.app)
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_analyze_missing_auth_returns_401(clear_rate_store, monkeypatch):
    monkeypatch.setattr(srv, "_PYTHON_API_KEY", "secret-token")
    monkeypatch.setattr(srv, "_RATE_MAX_REQUESTS", 1000)
    client = TestClient(srv.app)
    r = client.post("/analyze", json={"image_base64": "QQ=="})
    assert r.status_code == 401


def test_analyze_invalid_token_returns_403(clear_rate_store, monkeypatch):
    monkeypatch.setattr(srv, "_PYTHON_API_KEY", "good-token")
    monkeypatch.setattr(srv, "_RATE_MAX_REQUESTS", 1000)
    client = TestClient(srv.app)
    r = client.post(
        "/analyze",
        json={"image_base64": "QQ=="},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert r.status_code == 403


def test_analyze_approx_payload_too_large_returns_413(clear_rate_store, monkeypatch):
    monkeypatch.setattr(srv, "_PYTHON_API_KEY", "")
    monkeypatch.setattr(srv, "_MAX_IMAGE_BYTES", 10)
    monkeypatch.setattr(srv, "_RATE_MAX_REQUESTS", 1000)
    client = TestClient(srv.app)
    huge = "A" * 100
    r = client.post("/analyze", json={"image_base64": huge})
    assert r.status_code == 413
    assert r.json()["detail"] == "Image too large"


def test_analyze_rate_limit_returns_429(clear_rate_store, monkeypatch):
    monkeypatch.setattr(srv, "_PYTHON_API_KEY", "")
    monkeypatch.setattr(srv, "_MAX_IMAGE_BYTES", 10)
    monkeypatch.setattr(srv, "_RATE_MAX_REQUESTS", 1)
    client = TestClient(srv.app)
    huge = "B" * 100
    assert client.post("/analyze", json={"image_base64": huge}).status_code == 413
    r2 = client.post("/analyze", json={"image_base64": huge})
    assert r2.status_code == 429
    body = r2.json()
    assert "detail" in body
    assert body["detail"]["error"] == "Rate limit exceeded"
