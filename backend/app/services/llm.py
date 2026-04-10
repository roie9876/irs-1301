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

FORM_867_EXTRACTION_PROMPT = """אתה מומחה לחילוץ נתונים מטופס 867 ישראלי (אישור ניכוי מס במקור — דיבידנד וריבית מניירות ערך).
חלץ את השדות הבאים מהטקסט שלהלן והחזר JSON בלבד.

השדות לחילוץ:
- broker_name: שם הברוקר/חייב (טקסט)
- broker_id: מספר תיק ניכויים (טקסט)
- account_name: שם החשבון (טקסט)
- tax_year: שנת מס (מספר)
- dividend_income: סה"כ הכנסה מדיבידנד לפני קיזוז הפסדים — שורה 1 (מספר)
- dividend_foreign: הכנסה מדיבידנד בחו"ל — שורה 2 (מספר)
- dividend_tax_rate: שיעור ניכוי המס על דיבידנד (מספר, לדוגמה 25)
- dividend_tax_withheld: מס שנוכה במקור מדיבידנד — שורה 6 (מספר)
- foreign_tax_paid: מס ששולם בחו"ל — שורה 5 (מספר)
- interest_income: הכנסה מריבית/דמי ניכיון — שורה 7 (מספר)
- interest_tax_withheld: מס שנוכה במקור מריבית — שורה 11 (מספר)

כל שדה צריך להיות אובייקט עם:
- value: הערך שחולץ (מספר או טקסט, null אם לא נמצא)
- confidence: ציון ביטחון בין 0.0 ל-1.0

טקסט הטופס:
"""

DOCUMENT_CLASSIFIER_PROMPT = """אתה מומחה לזיהוי סוגי טפסים ישראליים של מס הכנסה.
בהינתן הטקסט הבא שחולץ מ-PDF, זהה את סוג המסמך.

הסוגים האפשריים:
- "form_106": טופס 106 — אישור שנתי מהמעסיק על הכנסות ומס שנוכה
- "form_867": טופס 867 — אישור ניכוי מס במקור על דיבידנד וריבית מניירות ערך
- "rental_payment": אישור תשלום מס על הכנסות משכירות למגורים (10%)
- "annual_summary": דוח שנתי על מכירת מניות/אופציות (Annual Sales Report)
- "receipt": קבלה/חשבונית (למשל שכ"ט רו"ח)
- "unknown": לא ניתן לזהות

החזר JSON בפורמט:
{
  "document_type": "form_106",
  "confidence": 0.95,
  "description": "תיאור קצר של המסמך"
}

טקסט המסמך (500 תווים ראשונים):
"""

RENTAL_PAYMENT_EXTRACTION_PROMPT = """אתה מומחה לחילוץ נתונים מאישורי תשלום מס הכנסה ישראליים.
חלץ את השדות הבאים מהטקסט שלהלן והחזר JSON בלבד.

השדות לחילוץ:
- taxpayer_name: שם הנישום (טקסט)
- taxpayer_id: מספר תיק (טקסט)
- tax_year: שנת מס (מספר)
- payment_amount: סכום תשלום בש"ח (מספר)
- payment_type: סוג תשלום (טקסט, למשל "מס על הכנסות משכ"ד למגורים")
- payment_date: תאריך תשלום (טקסט)
- reference_number: מספר קישור (טקסט)

כל שדה צריך להיות אובייקט עם:
- value: הערך שחולץ (מספר או טקסט, null אם לא נמצא)
- confidence: ציון ביטחון בין 0.0 ל-1.0

טקסט המסמך:
"""

ANNUAL_SUMMARY_EXTRACTION_PROMPT = """אתה מומחה לחילוץ נתונים מדוחות שנתיים על מכירת מניות (Annual Sales Report) ישראליים.
חלץ את השדות הבאים מהטקסט שלהלן והחזר JSON בלבד.

השדות לחילוץ:
- employee_name: שם העובד (טקסט)
- employee_id: מספר זהות (טקסט)
- tax_year: שנת מס (מספר)
- total_shares_sold: סה"כ מניות שנמכרו (מספר)
- ordinary_income_ils: הכנסת עבודה בשקלים (מספר) — סה"כ
- capital_income_ils: רווח הון בשקלים (מספר) — סה"כ
- tax_advance_payment: מקדמת מס שנוכתה (מספר) — סה"כ
- gross_proceed_usd: תמורה ברוטו בדולרים (מספר) — סה"כ
- tax_plan: תוכנית מס, למשל "102 הוני" (טקסט)

כל שדה צריך להיות אובייקט עם:
- value: הערך שחולץ (מספר או טקסט, null אם לא נמצא)
- confidence: ציון ביטחון בין 0.0 ל-1.0

טקסט המסמך:
"""

RECEIPT_EXTRACTION_PROMPT = """אתה מומחה לחילוץ נתונים מקבלות וחשבוניות מס ישראליות.
חלץ את השדות הבאים מהטקסט שלהלן והחזר JSON בלבד.

השדות לחילוץ:
- vendor_name: שם הספק/נותן השירות (טקסט)
- receipt_number: מספר קבלה/חשבונית (טקסט)
- date: תאריך (טקסט)
- amount_before_vat: סכום לפני מע"מ (מספר)
- vat_amount: סכום מע"מ (מספר)
- total_amount: סכום כולל מע"מ (מספר)
- description: תיאור השירות (טקסט)
- payer_name: שם המשלם (טקסט)
- payer_id: מספר זהות המשלם (טקסט)

כל שדה צריך להיות אובייקט עם:
- value: הערך שחולץ (מספר או טקסט, null אם לא נמצא)
- confidence: ציון ביטחון בין 0.0 ל-1.0

טקסט המסמך:
"""


def load_settings() -> dict:
    """Load LLM settings from .env. Returns has_api_key (bool), never the raw key."""
    load_dotenv(ENV_PATH, override=True)
    return {
        "provider": os.getenv("LLM_PROVIDER", ""),
        "model": os.getenv("LLM_MODEL", ""),
        "has_api_key": bool(os.getenv("LLM_API_KEY")),
        "api_base": os.getenv("AZURE_API_BASE", ""),
        "tax_year": int(os.getenv("TAX_YEAR", "2024")),
    }


def save_settings(provider: str, model: str, api_key: str, api_base: str = "", tax_year: int = 0) -> None:
    """Save LLM settings to .env file. Per D-10, only called after successful test."""
    if provider:
        set_key(ENV_PATH, "LLM_PROVIDER", provider)
    if model:
        set_key(ENV_PATH, "LLM_MODEL", model)
    if api_key:
        set_key(ENV_PATH, "LLM_API_KEY", api_key)
    if api_base:
        set_key(ENV_PATH, "AZURE_API_BASE", api_base)
    if tax_year:
        set_key(ENV_PATH, "TAX_YEAR", str(tax_year))
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


async def _llm_extract(prompt: str, raw_text: str, max_tokens: int = 2000) -> dict:
    """Generic LLM extraction — send prompt + text, return parsed JSON."""
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
            {"role": "user", "content": prompt + raw_text},
        ],
        "api_key": api_key,
        "response_format": {"type": "json_object"},
        "max_tokens": max_tokens,
    }
    if provider == "azure" and api_base:
        kwargs["api_base"] = api_base

    response = await litellm.acompletion(**kwargs)
    content = response.choices[0].message.content
    return json.loads(content)


async def extract_form106_data(raw_text: str) -> dict:
    """Extract Form 106 fields from raw PDF text using LLM with JSON mode."""
    return await _llm_extract(FORM_106_EXTRACTION_PROMPT, raw_text)


async def classify_document(raw_text: str) -> dict:
    """Classify a document by its type from extracted PDF text."""
    preview = raw_text[:500]
    return await _llm_extract(DOCUMENT_CLASSIFIER_PROMPT, preview, max_tokens=200)


async def extract_form867_data(raw_text: str) -> dict:
    """Extract Form 867 fields (dividends/interest) from raw PDF text."""
    return await _llm_extract(FORM_867_EXTRACTION_PROMPT, raw_text)


async def extract_rental_payment_data(raw_text: str) -> dict:
    """Extract rental tax payment confirmation data."""
    return await _llm_extract(RENTAL_PAYMENT_EXTRACTION_PROMPT, raw_text)


async def extract_annual_summary_data(raw_text: str) -> dict:
    """Extract annual RSU/stock sales report data."""
    return await _llm_extract(ANNUAL_SUMMARY_EXTRACTION_PROMPT, raw_text)


async def extract_receipt_data(raw_text: str) -> dict:
    """Extract receipt/invoice data (e.g., CPA fee)."""
    return await _llm_extract(RECEIPT_EXTRACTION_PROMPT, raw_text)
