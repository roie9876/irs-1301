import io
import json
from unittest.mock import AsyncMock, patch


def test_upload_id_supplement_extracts_extended_identity_fields(documents_client):
    extracted = {
        "holder_name": {"value": "בן חיים רועי", "confidence": 0.95},
        "holder_id": {"value": "33074451", "confidence": 0.98},
        "holder_birth_date": {"value": "01.01.1985", "confidence": 0.8},
        "spouse_name": {"value": "בן חיים מיכל", "confidence": 0.93},
        "spouse_id": {"value": "60183810", "confidence": 0.9},
        "spouse_birth_date": {"value": "02.02.1986", "confidence": 0.8},
        "holder_gender": {"value": "male", "confidence": 0.99},
        "address_street": {"value": "הרצל", "confidence": 0.75},
        "address_house_number": {"value": "15", "confidence": 0.7},
        "address_city": {"value": "רמת גן", "confidence": 0.7},
        "address_zip": {"value": "1234567", "confidence": 0.6},
        "children": [],
    }

    with patch("app.routers.documents.extract_id_supplement_data", new_callable=AsyncMock, return_value=extracted):
        response = documents_client.post(
            "/api/documents/upload",
            files=[("files", ("id.jpg", io.BytesIO(b"fake-image"), "image/jpeg"))],
        )

    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["status"] == "success"
    assert data["results"][0]["document_type"] == "id_supplement"
    assert data["results"][0]["extracted"]["holder_birth_date"]["value"] == "01.01.1985"
    assert data["results"][0]["extracted"]["address_street"]["value"] == "הרצל"


def test_upload_id_supplement_clears_spouse_when_it_matches_child(documents_client):
    extracted = {
        "holder_name": {"value": "בן חיים רועי", "confidence": 0.95},
        "holder_id": {"value": "33074451", "confidence": 0.98},
        "holder_birth_date": {"value": "09.08.1976", "confidence": 0.8},
        "spouse_name": {"value": "בן חיים שקד", "confidence": 0.9},
        "spouse_id": {"value": "219136272", "confidence": 0.9},
        "spouse_birth_date": {"value": "17.04.2010", "confidence": 0.9},
        "holder_gender": {"value": "male", "confidence": 0.99},
        "address_street": {"value": "דוכן", "confidence": 0.75},
        "address_house_number": {"value": "17", "confidence": 0.7},
        "address_city": {"value": "ירושלים", "confidence": 0.7},
        "address_zip": {"value": None, "confidence": 0.0},
        "children": [
            {"name": "בן חיים שקד", "id_number": "219136272", "birth_date": "17.04.2010", "birth_year": 2010},
        ],
    }

    with patch("app.routers.documents.extract_id_supplement_data", new_callable=AsyncMock, return_value=extracted):
        response = documents_client.post(
            "/api/documents/upload",
            files=[("files", ("id.jpg", io.BytesIO(b"fake-image"), "image/jpeg"))],
        )

    assert response.status_code == 200
    data = response.json()
    result = data["results"][0]
    assert result["status"] == "success"
    assert result["extracted"]["spouse_name"]["value"] is None
    assert result["extracted"]["spouse_id"]["value"] is None


def test_reextract_single_id_supplement_document(documents_client, mock_documents_dir):
    initial = {
        "doc_id": "abc12345",
        "original_filename": "id.jpg",
        "document_type": "id_supplement",
        "extracted": {
            "holder_name": {"value": "ישן", "confidence": 0.3},
            "holder_id": {"value": "33074451", "confidence": 0.9},
            "children": [],
        },
        "user_corrected": False,
    }
    sidecar = mock_documents_dir / "abc12345_id.jpg.doc.json"
    sidecar.write_text(json.dumps(initial, ensure_ascii=False), encoding="utf-8")
    (mock_documents_dir / "abc12345_id.jpg").write_bytes(b"fake-image")

    refreshed = {
        "holder_name": {"value": "בן חיים רועי", "confidence": 0.95},
        "holder_id": {"value": "33074451", "confidence": 0.98},
        "holder_birth_date": {"value": "09.08.1976", "confidence": 0.8},
        "spouse_name": {"value": None, "confidence": 0.0},
        "spouse_id": {"value": None, "confidence": 0.0},
        "spouse_birth_date": {"value": None, "confidence": 0.0},
        "holder_gender": {"value": "male", "confidence": 0.99},
        "address_street": {"value": "דוכן", "confidence": 0.75},
        "address_house_number": {"value": "17", "confidence": 0.7},
        "address_city": {"value": "ירושלים", "confidence": 0.7},
        "address_zip": {"value": None, "confidence": 0.0},
        "children": [],
    }

    with patch("app.routers.documents.extract_id_supplement_data", new_callable=AsyncMock, return_value=refreshed):
        response = documents_client.post("/api/documents/abc12345/reextract")

    assert response.status_code == 200
    data = response.json()
    assert data["doc_id"] == "abc12345"
    assert data["extracted"]["holder_name"]["value"] == "בן חיים רועי"