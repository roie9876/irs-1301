import pytest
import os
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


@pytest.fixture
def mock_env(tmp_path):
    """Create a temporary .env file for testing."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        'LLM_PROVIDER="openai"\n'
        'LLM_MODEL="gpt-4o"\n'
        'LLM_API_KEY="sk-test-key-123"\n'
        'AZURE_API_BASE=""\n'
    )
    return str(env_file)


@pytest.fixture
def client(mock_env):
    """TestClient with mocked ENV_PATH pointing to temp .env."""
    with patch("app.services.llm.ENV_PATH", mock_env):
        from app.main import app

        yield TestClient(app)


@pytest.fixture
def empty_client(tmp_path):
    """TestClient with empty .env (no settings configured)."""
    env_file = tmp_path / ".env"
    env_file.touch()
    env_keys = ["LLM_PROVIDER", "LLM_MODEL", "LLM_API_KEY", "AZURE_API_BASE"]
    saved = {k: os.environ.pop(k, None) for k in env_keys}
    with patch("app.services.llm.ENV_PATH", str(env_file)):
        from app.main import app

        yield TestClient(app)
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v


@pytest.fixture
def mock_litellm_success():
    """Mock LiteLLM acompletion returning a successful response."""
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = "טופס 1301 הוא דוח שנתי למס הכנסה"
    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock:
        yield mock


@pytest.fixture
def mock_litellm_failure():
    """Mock LiteLLM acompletion raising an error."""
    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=Exception("Invalid API key"),
    ) as mock:
        yield mock
