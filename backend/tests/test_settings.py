from unittest.mock import patch


def test_get_settings_returns_provider_and_model(client):
    """GET /api/settings returns provider, model, has_api_key fields."""
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "provider" in data
    assert "model" in data
    assert "has_api_key" in data
    assert data["provider"] == "openai"
    assert data["model"] == "gpt-4o"
    assert data["has_api_key"] is True
    assert "tax_year" in data


def test_get_settings_never_returns_raw_api_key(client):
    """GET /api/settings response must NOT contain api_key field (security INF-04)."""
    response = client.get("/api/settings")
    data = response.json()
    assert "api_key" not in data


def test_get_settings_empty_env(empty_client):
    """GET /api/settings with no settings returns empty values and has_api_key=False."""
    response = empty_client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == ""
    assert data["model"] == ""
    assert data["has_api_key"] is False


def test_post_test_success(client, mock_litellm_success):
    """POST /api/settings/test with valid credentials returns success."""
    response = client.post(
        "/api/settings/test",
        json={
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": "sk-test-key-123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "חיבור תקין"


def test_post_test_failure(client, mock_litellm_failure):
    """POST /api/settings/test with invalid credentials returns failure."""
    response = client.post(
        "/api/settings/test",
        json={
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": "sk-bad-key",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "Invalid API key" in data["message"]


def test_post_save_settings_success(client, mock_litellm_success, mock_env):
    """POST /api/settings saves settings after successful connection test."""
    with patch("app.services.llm.ENV_PATH", mock_env):
        response = client.post(
            "/api/settings",
            json={
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "api_key": "sk-ant-new-key",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "anthropic"
    assert data["model"] == "claude-sonnet-4-20250514"
    assert data["has_api_key"] is True


def test_post_save_settings_rejects_on_failed_test(client, mock_litellm_failure):
    """POST /api/settings returns 400 when connection test fails (per D-10)."""
    response = client.post(
        "/api/settings",
        json={
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": "sk-bad-key",
        },
    )
    assert response.status_code == 400


def test_load_settings_reads_env(mock_env):
    """load_settings reads values from .env file correctly."""
    with patch("app.services.llm.ENV_PATH", mock_env):
        from app.services.llm import load_settings

        settings = load_settings()
    assert settings["provider"] == "openai"
    assert settings["model"] == "gpt-4o"
    assert settings["has_api_key"] is True


def test_save_settings_writes_env(tmp_path):
    """save_settings writes values to .env file and reloads them."""
    env_file = tmp_path / ".env"
    env_file.touch()
    with patch("app.services.llm.ENV_PATH", str(env_file)):
        from app.services.llm import save_settings, load_settings

        save_settings(
            provider="gemini",
            model="gemini-2.0-flash",
            api_key="AIza-test-key",
        )
        settings = load_settings()
    assert settings["provider"] == "gemini"
    assert settings["model"] == "gemini-2.0-flash"
    assert settings["has_api_key"] is True


def test_put_tax_year(client, mock_env):
    """PUT /api/settings/tax-year updates year without touching LLM settings."""
    with patch("app.services.llm.ENV_PATH", mock_env):
        response = client.put(
            "/api/settings/tax-year",
            json={"tax_year": 2023},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["tax_year"] == 2023
    # LLM settings unchanged
    assert data["provider"] == "openai"
    assert data["has_api_key"] is True
