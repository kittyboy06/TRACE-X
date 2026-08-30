import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import verify_password, DEMO_USERS

client = TestClient(app)


def test_auth_success_analyst():
    response = client.post("/api/v1/auth/token", json={
        "username": "analyst",
        "password": "tracex2026"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "CTI_ANALYST"
    assert data["analyst_id"] == "ANALYST-001"


def test_auth_success_lead_auditor():
    response = client.post("/api/v1/auth/token", json={
        "username": "lead_auditor",
        "password": "auditor2026"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "LEAD_AUDITOR"


def test_auth_failure_invalid_password():
    response = client.post("/api/v1/auth/token", json={
        "username": "analyst",
        "password": "wrong_password_xyz"
    })
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


def test_auth_failure_unknown_user():
    response = client.post("/api/v1/auth/token", json={
        "username": "hacker_unknown",
        "password": "any_password"
    })
    assert response.status_code == 401


def test_protected_profile_endpoint():
    # 1. Without token -> 401
    resp_unauth = client.get("/api/v1/auth/me")
    assert resp_unauth.status_code == 401

    # 2. Login and retrieve token
    login_resp = client.post("/api/v1/auth/token", json={
        "username": "ntro_evaluator",
        "password": "ntro2026"
    })
    token = login_resp.json()["access_token"]

    # 3. With token -> 200
    resp_auth = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp_auth.status_code == 200
    assert resp_auth.json()["username"] == "ntro_evaluator"
    assert resp_auth.json()["role"] == "LEAD_AUDITOR"
