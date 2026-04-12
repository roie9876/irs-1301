import io
import json

from unittest.mock import AsyncMock, patch


CLASSIFY_106 = {"document_type": "form_106", "confidence": 0.95, "description": "טופס 106"}


def _upload_mocks(sample_extraction):
    """Context manager stack for common upload mocks."""
    mock_extractor = AsyncMock(return_value=sample_extraction)
    return (
        patch("app.routers.documents.extract_text_from_pdf", return_value="שם מעסיק: חברה"),
        patch("app.routers.documents.classify_document", new_callable=AsyncMock, return_value=CLASSIFY_106),
        patch.dict("app.routers.documents.EXTRACTORS", {"form_106": mock_extractor}),
    )


def test_upload_single_pdf_success(documents_client, sample_pdf_bytes, sample_extraction):
    m1, m2, m3 = _upload_mocks(sample_extraction)
    with m1, m2, m3:
        response = documents_client.post(
            "/api/documents/upload",
            files=[("files", ("form106.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf"))],
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    result = data["results"][0]
    assert result["status"] == "success"
    assert result["extracted"]["gross_salary"]["value"] == 180000
    assert result["extracted"]["employer_name"]["value"] == "חברה לדוגמה בע״מ"


def test_upload_non_pdf_returns_error(documents_client):
    response = documents_client.post(
        "/api/documents/upload",
        files=[("files", ("file.txt", io.BytesIO(b"hello"), "text/plain"))],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["status"] == "error"
    assert "הקובץ אינו PDF, Excel או תמונה תקינה" in data["results"][0]["error"]


def test_upload_multiple_files(documents_client, sample_pdf_bytes, sample_extraction):
    m1, m2, m3 = _upload_mocks(sample_extraction)
    with m1, m2, m3:
        response = documents_client.post(
            "/api/documents/upload",
            files=[
                ("files", ("form106_a.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")),
                ("files", ("form106_b.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")),
            ],
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    assert all(r["status"] == "success" for r in data["results"])


def test_upload_creates_json_sidecar(documents_client, sample_pdf_bytes, sample_extraction, mock_documents_dir):
    m1, m2, m3 = _upload_mocks(sample_extraction)
    with m1, m2, m3:
        documents_client.post(
            "/api/documents/upload",
            files=[("files", ("form106.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf"))],
        )

    sidecars = list(mock_documents_dir.glob("*.doc.json"))
    assert len(sidecars) == 1
    data = json.loads(sidecars[0].read_text(encoding="utf-8"))
    assert data["original_filename"] == "form106.pdf"
    assert data["document_type"] == "form_106"
    assert data["user_corrected"] is False
    assert "gross_salary" in data["extracted"]


def test_get_documents_returns_saved(documents_client, sample_pdf_bytes, sample_extraction):
    m1, m2, m3 = _upload_mocks(sample_extraction)
    with m1, m2, m3:
        documents_client.post(
            "/api/documents/upload",
            files=[("files", ("form106.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf"))],
        )

    response = documents_client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert len(data["documents"]) == 1
    assert data["documents"][0]["original_filename"] == "form106.pdf"


def test_put_document_updates_field(documents_client, sample_pdf_bytes, sample_extraction):
    m1, m2, m3 = _upload_mocks(sample_extraction)
    with m1, m2, m3:
        upload_resp = documents_client.post(
            "/api/documents/upload",
            files=[("files", ("form106.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf"))],
        )

    doc_id = upload_resp.json()["results"][0]["doc_id"]
    response = documents_client.put(
        f"/api/documents/{doc_id}",
        json={"fields": {"gross_salary": {"value": 200000, "confidence": 1.0}}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_corrected"] is True
    assert data["extracted"]["gross_salary"]["value"] == 200000


def test_put_document_not_found(documents_client):
    response = documents_client.put(
        "/api/documents/nonexistent",
        json={"fields": {"gross_salary": {"value": 200000, "confidence": 1.0}}},
    )
    assert response.status_code == 404


def test_upload_extraction_error_handled(documents_client, sample_pdf_bytes):
    with patch("app.routers.documents.extract_text_from_pdf", return_value="שם מעסיק: חברה"), \
         patch("app.routers.documents.classify_document", new_callable=AsyncMock, return_value=CLASSIFY_106), \
         patch.dict("app.routers.documents.EXTRACTORS", {"form_106": AsyncMock(side_effect=Exception("LLM fail"))}):
        response = documents_client.post(
            "/api/documents/upload",
            files=[("files", ("form106.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf"))],
        )
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["status"] == "error"
    assert "שגיאה בחילוץ" in data["results"][0]["error"]
