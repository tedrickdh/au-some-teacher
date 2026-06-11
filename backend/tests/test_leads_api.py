"""Lead submission API tests for public /api/leads endpoint."""

import os
import uuid
from datetime import datetime
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from typing import Any


# Load public app URL from frontend env (required for external endpoint testing)
load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


@pytest.fixture(scope="module")
def api_client() -> requests.Session:
    """Shared HTTP session for lead API tests."""
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL missing; cannot run public endpoint tests")

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def _valid_payload(kind: str = "client") -> dict[str, str]:
    unique = uuid.uuid4().hex[:8]
    return {
        "kind": kind,
        "name": f"TEST Lead {unique}",
        "email": f"lead_{unique}@example.com",
        "phone": "713-555-1212",
        "child_age": "7",
        "insurance": "Aetna",
        "city": "Houston",
        "message": "Looking for services and next steps.",
    }

def _post_lead(api_client: requests.Session, payload: dict[str, str]) -> dict[str, Any]:
    response = api_client.post(f"{BASE_URL}/api/leads", json=payload, timeout=20)
    assert response.status_code == 200
    return response.json()

def _assert_lead_identity(data: dict[str, Any], payload: dict[str, str]) -> None:
    assert isinstance(data.get("id"), str)
    assert len(data["id"]) > 10
    assert data["kind"] == payload["kind"]
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]

def _assert_lead_routing(data: dict[str, Any]) -> None:
    assert data["destination_email"] == "info@ausometeacher.com"
    assert isinstance(data["notification_sent"], bool)
    assert "notification_error" in data
    assert "email_provider_id" in data

def _assert_iso_datetime(value: str) -> None:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert isinstance(parsed, datetime)


def test_create_client_lead_success(api_client: requests.Session) -> None:
    """Lead create: valid client payload should persist and return structured data."""
    payload = _valid_payload("client")
    data = _post_lead(api_client, payload)

    _assert_lead_identity(data, payload)
    assert data["insurance"] == payload["insurance"]
    assert data["city"] == payload["city"]
    _assert_lead_routing(data)
    _assert_iso_datetime(data["created_at"])


def test_create_insurance_lead_success(api_client: requests.Session) -> None:
    """Lead create: valid insurance verification payload should succeed."""
    payload = _valid_payload("insurance")
    payload["message"] = "Please verify benefits."

    data = _post_lead(api_client, payload)

    _assert_lead_identity(data, payload)
    _assert_lead_routing(data)


def test_create_lead_invalid_email_rejected(api_client: requests.Session) -> None:
    """Lead create: invalid email should return validation error."""
    payload = _valid_payload("client")
    payload["email"] = "not-an-email"

    response = api_client.post(f"{BASE_URL}/api/leads", json=payload, timeout=20)
    assert response.status_code == 422

    data: dict[str, Any] = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], list)
