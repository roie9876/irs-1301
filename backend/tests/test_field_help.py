def test_get_field_help_for_income_field(client):
    response = client.get("/api/form-1301/field-help/158")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "158"
    assert data["part_id"] == "ג"
    assert "משכורת" in data["title"]


def test_get_field_help_for_general_override(client):
    response = client.get("/api/form-1301/field-help/331")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "331"
    assert data["part_id"] == "א"
    assert "66(ד)" in data["description"]


def test_get_field_help_returns_404_for_unknown_code(client):
    response = client.get("/api/form-1301/field-help/999999")
    assert response.status_code == 404
