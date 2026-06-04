"""Lead submission API tests for public /api/leads endpoint."""

import os
import uuid
from datetime import datetime
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv


# Load public app URL from frontend env (required for external endpoint testing)
load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


@pytest.fixture(scope="module")
def api_client():
    """Shared HTTP session for lead API tests."""
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL missing; cannot run public endpoint tests")

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def _valid_payload(kind: str = "client"):
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


def test_create_client_lead_success(api_client):
    """Lead create: valid client payload should persist and return structured data."""
    payload = _valid_payload("client")
    response = api_client.post(f"{BASE_URL}/api/leads", json=payload, timeout=20)

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data.get("id"), str) and len(data["id"]) > 10
    assert data["kind"] == payload["kind"]
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]
    assert data["insurance"] == payload["insurance"]
    assert data["city"] == payload["city"]

    # created_at should be an ISO datetime
    parsed = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
    assert isinstance(parsed, datetime)


def test_create_insurance_lead_success(api_client):
    """Lead create: valid insurance verification payload should succeed."""
    payload = _valid_payload("insurance")
    payload["message"] = "Please verify benefits."

    response = api_client.post(f"{BASE_URL}/api/leads", json=payload, timeout=20)
    assert response.status_code == 200

    data = response.json()
    assert data["kind"] == "insurance"
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]


def test_create_lead_invalid_email_rejected(api_client):
    """Lead create: invalid email should return validation error."""
    payload = _valid_payload("client")
    payload["email"] = "not-an-email"

    response = api_client.post(f"{BASE_URL}/api/leads", json=payload, timeout=20)
    assert response.status_code == 422

    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], list)
