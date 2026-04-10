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


@pytest.fixture
def mock_documents_dir(tmp_path):
    """Temporary directory for document storage."""
    docs_dir = tmp_path / "user_data" / "documents"
    docs_dir.mkdir(parents=True)
    with patch("app.routers.documents.DOCUMENTS_DIR", docs_dir):
        yield docs_dir


@pytest.fixture
def sample_extraction():
    """Sample Form 106 extraction result from LLM."""
    return {
        "employer_name": {"value": "חברה לדוגמה בע״מ", "confidence": 0.95},
        "employer_id": {"value": "514000000", "confidence": 0.9},
        "tax_year": {"value": 2024, "confidence": 0.99},
        "gross_salary": {"value": 180000, "confidence": 0.92},
        "tax_withheld": {"value": 35000, "confidence": 0.88},
        "pension_employer": {"value": 12000, "confidence": 0.85},
        "insured_income": {"value": 160000, "confidence": 0.8},
        "convalescence_pay": {"value": 4000, "confidence": 0.75},
        "education_fund": {"value": 9000, "confidence": 0.82},
        "work_days": {"value": 240, "confidence": 0.7},
        "national_insurance": {"value": 8000, "confidence": 0.85},
        "health_insurance": {"value": 5000, "confidence": 0.85},
    }


@pytest.fixture
def sample_pdf_bytes():
    """Minimal valid PDF with Hebrew text."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "שם מעסיק: חברה לדוגמה בע״מ\nהכנסה ברוטו: 180,000")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def documents_client(mock_env, mock_documents_dir):
    """TestClient with documents router wired + mocked env and docs dir."""
    with patch("app.services.llm.ENV_PATH", mock_env):
        from app.main import app
        from app.routers.documents import router as docs_router

        app.include_router(docs_router, prefix="/api")
        yield TestClient(app)
        # Remove the added routes to avoid pollution
        app.routes[:] = [r for r in app.routes if not (hasattr(r, 'path') and r.path.startswith("/api/documents"))]
