import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import NoticeStatus
from app.tinyfish import search_fetch

client = TestClient(app)


def test_health_endpoint_reports_service_status():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_invalid_credential_request_uses_api_error_envelope():
    response = client.post(
        "/api/credential/check",
        json={"credential_ref": "REAL-PERSON-123", "zone": "LAB-A"},
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "validation_error"
    assert payload["retryable"] is False
    assert payload["request_id"]


def test_unknown_synthetic_credential_returns_unknown_not_allow():
    response = client.post(
        "/api/credential/check",
        json={"credential_ref": "SYN-9999", "zone": "LAB-A", "checked_at": "2026-10-20T09:00:00Z"},
    )
    assert response.status_code == 200
    assert response.json()["decision"] == "unknown"


def test_tinyfish_missing_key_is_explicit_provider_error(monkeypatch):
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    result = asyncio.run(search_fetch("official public notice near venue", "India"))
    assert result.status == NoticeStatus.provider_error
    assert result.results == []
    assert result.error is not None
