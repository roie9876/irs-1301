import os
from pathlib import Path

from dotenv import load_dotenv, set_key
import litellm

# Absolute path per Pitfall 4 — consistent regardless of working directory
ENV_PATH = str(Path(__file__).resolve().parent.parent / ".env")

PROVIDER_PREFIX = {
    "openai": "",              # OpenAI needs no prefix
    "azure": "azure/",         # Azure OpenAI
    "gemini": "gemini/",       # Google Gemini
    "anthropic": "anthropic/", # Anthropic Claude
}


def load_settings() -> dict:
    """Load LLM settings from .env. Returns has_api_key (bool), never the raw key."""
    load_dotenv(ENV_PATH, override=True)
    return {
        "provider": os.getenv("LLM_PROVIDER", ""),
        "model": os.getenv("LLM_MODEL", ""),
        "has_api_key": bool(os.getenv("LLM_API_KEY")),
        "api_base": os.getenv("AZURE_API_BASE", ""),
    }


def save_settings(provider: str, model: str, api_key: str, api_base: str = "") -> None:
    """Save LLM settings to .env file. Per D-10, only called after successful test."""
    set_key(ENV_PATH, "LLM_PROVIDER", provider)
    set_key(ENV_PATH, "LLM_MODEL", model)
    set_key(ENV_PATH, "LLM_API_KEY", api_key)
    if api_base:
        set_key(ENV_PATH, "AZURE_API_BASE", api_base)
    load_dotenv(ENV_PATH, override=True)


async def test_connection(
    provider: str, model: str, api_key: str, api_base: str = ""
) -> dict:
    """Test LLM connection with a minimal Hebrew prompt. Uses acompletion for async FastAPI."""
    prefix = PROVIDER_PREFIX.get(provider)
    if prefix is None:
        raise ValueError(f"ספק לא מוכר: {provider}")

    llm_model = f"{prefix}{model}"

    kwargs: dict = {
        "model": llm_model,
        "messages": [{"role": "user", "content": "מה זה טופס 1301? ענה במשפט אחד."}],
        "api_key": api_key,
        "max_tokens": 30,
    }
    if provider == "azure" and api_base:
        kwargs["api_base"] = api_base

    response = await litellm.acompletion(**kwargs)
    return {"content": response.choices[0].message.content}
