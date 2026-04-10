import json
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

FORM_106_EXTRACTION_PROMPT = """אתה מומחה לחילוץ נתונים מטפסי 106 ישראליים.
חלץ את השדות הבאים מהטקסט שלהלן והחזר JSON בלבד.

השדות לחילוץ:
- employer_name: שם המעסיק (טקסט)
- employer_id: מספר מזהה מעסיק (טקסט)
- tax_year: שנת מס (מספר)
- gross_salary: הכנסה ברוטו - שדה 158/172 (מספר)
- tax_withheld: מס שנוכה במקור - סעיף 84 (מספר)
- pension_employer: הפרשות מעסיק לפנסיה - שדה 248/249 (מספר)
- insured_income: הכנסה מבוטחת - שדה 244/245 (מספר)
- convalescence_pay: דמי הבראה - שדה 011/012 (מספר)
- education_fund: קרן השתלמות - שדה 218/219 (מספר)
- work_days: ימי עבודה (מספר)
- national_insurance: ביטוח לאומי (מספר)
- health_insurance: ביטוח בריאות (מספר)

כל שדה צריך להיות אובייקט עם:
- value: הערך שחולץ (מספר או טקסט, null אם לא נמצא)
- confidence: ציון ביטחון בין 0.0 ל-1.0

דוגמה לפורמט JSON:
{
  "employer_name": {"value": "חברה בע״מ", "confidence": 0.95},
  "gross_salary": {"value": 150000, "confidence": 0.9},
  "work_days": {"value": null, "confidence": 0}
}

טקסט הטופס:
"""


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


async def extract_form106_data(raw_text: str) -> dict:
    """Extract Form 106 fields from raw PDF text using LLM with JSON mode."""
    load_dotenv(ENV_PATH, override=True)

    provider = os.getenv("LLM_PROVIDER", "")
    model = os.getenv("LLM_MODEL", "")
    api_key = os.getenv("LLM_API_KEY", "")
    api_base = os.getenv("AZURE_API_BASE", "")

    if not all([provider, model, api_key]):
        raise ValueError("LLM not configured")

    prefix = PROVIDER_PREFIX.get(provider)
    if prefix is None:
        raise ValueError(f"ספק לא מוכר: {provider}")

    llm_model = f"{prefix}{model}"

    kwargs: dict = {
        "model": llm_model,
        "messages": [
            {"role": "user", "content": FORM_106_EXTRACTION_PROMPT + raw_text},
        ],
        "api_key": api_key,
        "response_format": {"type": "json_object"},
        "max_tokens": 2000,
    }
    if provider == "azure" and api_base:
        kwargs["api_base"] = api_base

    response = await litellm.acompletion(**kwargs)
    content = response.choices[0].message.content
    return json.loads(content)
