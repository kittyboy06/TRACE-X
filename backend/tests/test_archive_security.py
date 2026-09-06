import pytest
import io
import zipfile
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def lead_auditor_headers():
    login_resp = client.post("/api/v1/auth/token", json={
        "username": "lead_auditor",
        "password": "auditor2026"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_zip_in_memory(files_dict: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for filename, content in files_dict.items():
            z.writestr(filename, content)
    return buf.getvalue()


def test_directory_traversal_archive_rejected(lead_auditor_headers):
    """Verify that an archive containing directory traversal sequences (..) is rejected with 400."""
    malicious_files = {
        "../../etc/passwd.json": json.dumps({"artifacts": []})
    }
    zip_bytes = create_zip_in_memory(malicious_files)

    resp = client.post(
        "/api/v1/ingestion/upload-file",
        files={"file": ("traversal.zip", zip_bytes, "application/zip")},
        headers=lead_auditor_headers
    )
    assert resp.status_code == 400
    assert "traversal" in resp.json()["detail"].lower()


def test_max_zip_entries_limit_enforced(lead_auditor_headers):
    """Verify that an archive with > 50 entries is rejected with 400."""
    files_dict = {
        f"artifact_{i:03d}.json": json.dumps({"raw_payload": {"index": i}})
        for i in range(55)  # Exceeds MAX_ZIP_ENTRIES = 50
    }
    zip_bytes = create_zip_in_memory(files_dict)

    resp = client.post(
        "/api/v1/ingestion/upload-file",
        files={"file": ("too_many_entries.zip", zip_bytes, "application/zip")},
        headers=lead_auditor_headers
    )
    assert resp.status_code == 400
    assert "entries" in resp.json()["detail"].lower()


def test_max_uncompressed_limit_enforced(lead_auditor_headers):
    """Verify that an archive whose uncompressed contents exceed 25 MB is rejected with 400."""
    # Create a highly compressible 26MB zero payload
    large_content = "0" * (26 * 1024 * 1024)
    files_dict = {
        "large_bomb.json": large_content
    }
    zip_bytes = create_zip_in_memory(files_dict)

    resp = client.post(
        "/api/v1/ingestion/upload-file",
        files={"file": ("bomb.zip", zip_bytes, "application/zip")},
        headers=lead_auditor_headers
    )
    assert resp.status_code == 400
    assert "exceeds" in resp.json()["detail"].lower()


def test_max_upload_size_limit_enforced(lead_auditor_headers):
    """Verify that an upload exceeding 10 MB is rejected with 413 Request Entity Too Large."""
    oversized_bytes = b"X" * (11 * 1024 * 1024)  # 11 MB > 10 MB

    resp = client.post(
        "/api/v1/ingestion/upload-file",
        files={"file": ("oversized.json", oversized_bytes, "application/json")},
        headers=lead_auditor_headers
    )
    assert resp.status_code == 413
    assert "maximum limit" in resp.json()["detail"].lower()


def test_valid_zip_evidence_package_ingestion(lead_auditor_headers):
    """Verify safe extraction, normalization, and ingestion of a valid ZIP evidence archive."""
    valid_package = {
        "investigation_id": "INV-SAFE-ZIP-001",
        "title": "Operation Safe Archive Ingestion",
        "target_persona_a": "ZipPersonaA",
        "target_persona_b": "ZipPersonaB",
        "narrative": "Valid compressed archive test.",
        "artifacts": [
            {
                "artifact_type": "FORUM_POST",
                "source_uri": "safe-forum.onion/post/100",
                "raw_payload": {
                    "persona": "ZipPersonaA",
                    "post_text": "PGP key ID 0xDEADBEEF active on hidden service."
                }
            }
        ]
    }
    zip_bytes = create_zip_in_memory({"package.json": json.dumps(valid_package)})

    resp = client.post(
        "/api/v1/ingestion/upload-file",
        files={"file": ("safe_package.zip", zip_bytes, "application/zip")},
        headers=lead_auditor_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["investigation_id"] == "INV-SAFE-ZIP-001"
    assert data["ingested_count"] == 1
    assert len(data["records"]) == 1
    rec = data["records"][0]
    assert rec["evidence_id"].startswith("EV-")
    assert len(rec["content_hash"]) == 64
