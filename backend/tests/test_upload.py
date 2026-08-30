import pytest
import json
import io
import zipfile
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    login_resp = client.post("/api/v1/auth/token", json={
        "username": "analyst",
        "password": "tracex2026"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_json_package_upload_and_deduplication(auth_headers):
    package = {
        "investigation_id": "INV-TEST-UPLOAD-01",
        "target_persona_a": "ThreatActor_X",
        "target_persona_b": "DarkNet_Seller_Y",
        "artifacts": [
            {
                "evidence_id": "EV-UP-001",
                "artifact_type": "PGP_KEY",
                "source_uri": "darknet://keys.onion/123",
                "collected_at": "2026-08-30T12:00:00Z",
                "raw_payload": {
                    "key_id": "0xDEAD_BEEF",
                    "key_fingerprint": "1111 2222 3333 4444 5555 6666 7777 8888",
                    "persona": "ThreatActor_X"
                }
            }
        ]
    }

    # 1. First upload -> 200 OK
    resp1 = client.post("/api/v1/ingestion/upload", json=package, headers=auth_headers)
    assert resp1.status_code == 200
    assert resp1.json()["ingested_count"] == 1

    # 2. Duplicate upload within same investigation -> idempotent deduplication (DB row remains 1)
    resp2 = client.post("/api/v1/ingestion/upload", json=package, headers=auth_headers)
    assert resp2.status_code == 200
    
    from app.models.database import SessionLocal, EvidenceRecordModel
    db = SessionLocal()
    count = db.query(EvidenceRecordModel).filter(
        EvidenceRecordModel.investigation_id == "INV-TEST-UPLOAD-01"
    ).count()
    db.close()
    assert count == 1


def test_multipart_file_upload(auth_headers):
    file_payload = {
        "investigation_id": "INV-TEST-FILE-02",
        "target_persona_a": "GhostAlpha",
        "target_persona_b": "SpecterBeta",
        "artifacts": [
            {
                "evidence_id": "EV-FILE-001",
                "artifact_type": "FORUM_POST",
                "source_uri": "darknet://forum.onion/thread/99",
                "collected_at": "2026-08-30T12:00:00Z",
                "raw_payload": {
                    "forum": "DreadForum",
                    "persona": "GhostAlpha",
                    "post_text": "Sample darknet post detailing exploits.",
                    "word_count": 8
                }
            }
        ]
    }

    file_bytes = json.dumps(file_payload).encode("utf-8")
    files = {"file": ("evidence_package.json", io.BytesIO(file_bytes), "application/json")}

    resp = client.post("/api/v1/ingestion/upload-file", files=files, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["investigation_id"] == "INV-TEST-FILE-02"
    assert data["ingested_count"] == 1
