from unittest.mock import AsyncMock, patch


def test_form1301_assistant_returns_answer(client):
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = "לפי הנתונים הקיימים, חסר טופס 106 נוסף עבור בן הזוג אם הייתה לו משכורת."

    with patch("app.services.advisor_ai.litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
        response = client.post(
            "/api/form-1301/assistant",
            json={
                "question": "מה חסר לי כרגע?",
                "tax_year": 2024,
                "source_documents": ["form106.pdf"],
                "warnings": [],
                "advisor_items": [
                    {"title": "נמצא רק טופס 106 אחד במשק בית זוגי", "detail": "אם גם לבן או לבת הזוג הייתה משכורת, כדאי להעלות גם את טופס 106 שלהם.", "level": "warn"}
                ],
                "current_section": "פרטים כלליים והצהרות בסיס",
                "current_field_label": "בה\"ח/י עולה",
                "current_field_explanation": "שדה שבודק אם אחד מבני הזוג הוא עולה חדש או תושב חוזר הזכאי להקלות מס.",
                "balance": 1200,
                "net_tax": 50000,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "טופס 106" in data["answer"]
