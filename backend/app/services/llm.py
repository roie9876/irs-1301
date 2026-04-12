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

כלל חשוב: אם שדה לא מופיע בטקסט כלל — החזר value=null עם confidence=0.
אל תמציא ערכים. רק ערכים שמופיעים במפורש בטקסט.
הבדל בין "לא נמצא" (value=null, confidence=0) לבין "נמצא עם ערך 0" (value=0, confidence גבוה).

השדות לחילוץ:
- employer_name: שם המעסיק (טקסט)
- employer_id: מספר חברה — 9 ספרות (טקסט). זה השדה "חברה:" ולא "תיק ניכויים"
- tax_year: שנת מס (מספר)
- gross_salary: "משכורת חייבת במס" — הסכום הכולל של כל הרכיבים החייבים במס (מספר). חשוב: אם מופיעים גם "הכנסה חייבת רגילה" וגם "משכורת חייבת במס" — קח את "משכורת חייבת במס" כי הוא כולל גם החזר הוצאות וחלק חייב בפיצויים. אם אין שדה "משכורת חייבת במס" אבל יש כמה שורות עם סעיף 158/172 (למשל "משכורת" ו"שווי הטבה") — סכום אותן. אל תיקח את "סה"כ התשלום ברוטו" כי הוא כולל גם תשלומים פטורים
- tax_withheld: מס הכנסה שנוכה - סעיף 042 (מספר)
- pension_employer: הפרשות לקופ"ג לקצבה, לרבות מרכיב פיצויים - שדה 249/248 (מספר). חשוב: אם מופיעים גם "הפרשת מעסיק לקופת גמל לקצבה" וגם "סך הפרשות מעסיק לקצבה" — קח את "סך הפרשות מעסיק לקצבה" כי הוא כולל גם את מרכיב הפיצויים
- pension_employee: ניכוי לקופות גמל לקצבה כ"עמית שכיר" - שדה 086/045 (מספר). זה הסכום שהעובד הפקיד, לא המעסיק. חפש "ניכוי לקופת גמל לקצבה כ'עמית שכיר'" או שורה ליד שדה 086/045
- insured_income: השכר המבוטח לקופ"ג לקצבה - שדה 245/244 (מספר). זה לא השכר ברוטו — זה השכר שעליו מחושבות ההפרשות
- convalescence_pay: מחיר יום ההבראה שהופחת משכר העובד - שדה 012/011 (מספר)
- education_fund: השכר לקרן השתלמות - שדה 219/218 (מספר). זה השכר לצורך הפקדות, לא סכום ההפקדה עצמה
- work_days: סה"כ חודשי עבודה × 25, או לפי יחידות מס (מספר). אם כתוב "300 יחידות מס" הערך הוא 300
- national_insurance: דמי ביטוח לאומי (מספר). חפש "נ. ביטוח לאומי" — קח את הסכום הראשון (הגדול) שליד שכר חייב בדמי ביטוח. אל תסכום הפרשים לשנה קודמת
- health_insurance: דמי ביטוח בריאות (מספר). חפש "נ. ביטוח בריאות" — קח את הסכום הראשון (הגדול). אל תסכום הפרשים לשנה קודמת
- donations: תרומות למוסדות ציבור - שדה 037/237 (מספר). חפש "תרומות" או "מוסדות ציבור"
- life_insurance: ביטוח חיים — חפש "ביטוח חיים", "ניכוי לביטוח חיים", או שורה ליד שדה 036/081. לא כל טופס 106 מכיל שדה זה. אם לא מופיע בטקסט — החזר null עם confidence=0
- capital_gains_102: רווח הון מניירות ערך לפי סעיף 102 לפקודה (מספר). חפש "רווח הון" ליד סכום כספי. יכול להופיע גם כ"רווח הון מנייר ערך" או "רווח הון מני"ע" עם הפניה לסעיף 102. בטופס OCR הטקסט עלול להיות חתוך — אם יש שורה עם "רווח הון" וסכום, חלץ את הסכום גם אם "102" לא מופיע באותה שורה. אם לא מופיע — החזר null עם confidence=0

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
- "form_106": טופס 106 — אישור שנתי מהמעסיק על הכנסות ומס שנוכה. גם טופס 76 (השם הישן) הוא form_106. כל מסמך שמכיל פירוט משכורת, ניכוי מס, הפרשות לקופות גמל ונקודות זיכוי מהמעסיק — סווג כ-form_106
- "form_867": טופס 867 — אישור ניכוי מס במקור על דיבידנד וריבית מניירות ערך
- "rental_payment": אישור תשלום מס על הכנסות משכירות למגורים (10%)
- "annual_summary": דוח שנתי על מכירת מניות/אופציות (Annual Sales Report)
- "receipt": קבלה/חשבונית (למשל שכ"ט רו"ח)
- "unknown": כל מסמך אחר — שומה, אישור הגשה, דוח רואה חשבון, טופס 1301, קבלה על דו"ח שנתי, וכדומה. זה כולל גם ניירת שהמטרה שלה היא בדיקה כנגד (reference) ולא מקור נתונים.

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


ID_SUPPLEMENT_EXTRACTION_PROMPT = """אתה מומחה לחילוץ נתונים מספח תעודת זהות ישראלית.
חלץ את כל הפרטים מהתמונה והחזר JSON בלבד.

כלל קריטי:
- אסור לבחור ילד או ילדה מתוך רשימת הילדים בתור spouse_name או spouse_id.
- spouse_name/spouse_id/spouse_birth_date חייבים להגיע רק משורת בן/בת הזוג באזור הראשי של הספח.
- אם אינך בטוח שמצאת את בן/בת הזוג באזור הראשי, החזר null עבור spouse_name/spouse_id/spouse_birth_date.
- עדיף null מאשר לבחור בטעות אחד הילדים.
- address_street/address_house_number/address_city/address_zip חייבים להגיע רק מבלוק הכתובת של בעל התעודה.
- אסור לנחש כתובת על בסיס אזורים אחרים במסמך.
- אם אינך בטוח בכתובת, החזר null לשדה הרלוונטי במקום ערך חלקי או שגוי.

השדות לחילוץ:
- holder_name: שם בעל התעודה (טקסט)
- holder_id: מספר תעודת זהות של בעל התעודה (טקסט)
- holder_birth_date: תאריך לידה של בעל התעודה בפורמט DD.MM.YYYY או YYYY-MM-DD אם ניתן
- spouse_name: שם בן/בת הזוג (טקסט, null אם לא נשוי)
- spouse_id: מספר ת.ז. של בן/בת הזוג (טקסט, null אם לא נשוי)
- spouse_birth_date: תאריך לידה של בן/בת הזוג בפורמט DD.MM.YYYY או YYYY-MM-DD אם ניתן
- holder_gender: מין בעל התעודה — "male" אם כתוב "זכר" או "male", או "female" אם כתוב "נקבה" או "female"
- address_street: שם הרחוב כפי שמופיע בבלוק הכתובת בלבד, בלי לנחש ובלי לכלול את מספר הבית (טקסט)
- address_house_number: מספר הבית מתוך בלוק הכתובת בלבד (טקסט)
- address_city: יישוב/עיר מתוך בלוק הכתובת בלבד (טקסט)
- address_zip: מיקוד אם מופיע בבלוק הכתובת (טקסט)
- children: רשימה של כל הילדים המופיעים בספח

כל שדה (חוץ מ-children) צריך להיות אובייקט עם:
- value: הערך שחולץ (טקסט, null אם לא נמצא)
- confidence: ציון ביטחון 0.0-1.0

children הוא מערך של אובייקטים, כל אחד עם:
- name: שם הילד/ה (טקסט)
- id_number: מספר ת.ז. של הילד/ה (טקסט)
- birth_date: תאריך לידה בפורמט DD.MM.YYYY (אם מופיע בתאריך עברי, המר ללועזי)
- birth_year: שנת לידה (מספר)

חשוב: הספח כולל תאריכים בעברית (כ"ג באב תשע"ז וכד'). המר אותם לתאריכים לועזיים.
אם לא ניתן לקרוא את הפרטים, החזר מערך ריק.
אל תחלץ את בן/בת הזוג מתוך בלוק הילדים גם אם מופיעים שם שם פרטי, שם משפחה ומספר זהות.
אל תחזיר רחוב או יישוב אם הקריאה לא ודאית או אם הערך נראה חלקי/קטוע.

דוגמה:
{
  "holder_name": {"value": "כהן ישראל", "confidence": 0.95},
  "holder_id": {"value": "123456789", "confidence": 0.98},
    "holder_birth_date": {"value": "15.03.1985", "confidence": 0.88},
  "spouse_name": {"value": "כהן רחל", "confidence": 0.95},
  "spouse_id": {"value": "987654321", "confidence": 0.95},
    "spouse_birth_date": {"value": "20.11.1987", "confidence": 0.84},
  "holder_gender": {"value": "male", "confidence": 0.99},
    "address_street": {"value": "הרצל", "confidence": 0.8},
    "address_house_number": {"value": "15", "confidence": 0.78},
    "address_city": {"value": "תל אביב", "confidence": 0.8},
    "address_zip": {"value": "6789001", "confidence": 0.6},
  "children": [
    {"name": "כהן דן", "id_number": "111222333", "birth_date": "15.03.2015", "birth_year": 2015},
    {"name": "כהן נועה", "id_number": "444555666", "birth_date": "20.08.2018", "birth_year": 2018}
  ]
}
"""


async def extract_id_supplement_data(image_bytes: bytes, filename: str) -> dict:
    """Extract data from Israeli ID supplement (ספח) using vision model."""
    import base64

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

    # Determine MIME type
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/jpeg")

    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    kwargs: dict = {
        "model": llm_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": ID_SUPPLEMENT_EXTRACTION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64_image}"},
                    },
                ],
            }
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
