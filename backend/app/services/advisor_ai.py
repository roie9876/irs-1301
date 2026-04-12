import os
from pathlib import Path

import litellm
from dotenv import load_dotenv

from app.schemas.advisor import AdvisorQuestionRequest
from app.services.llm import ENV_PATH, PROVIDER_PREFIX


SYSTEM_PROMPT = """אתה עוזר מקצועי לדוח שנתי 1301 בישראל.
ענה רק על בסיס ההקשר שנשלח אליך: שנת המס, אזהרות, מסמכים שהועלו, השלמות מומלצות, נתוני הסיכום אם יש, והקשר של השדה הנוכחי אם נשלח.
כללים:
- אל תמציא מסמכים או נתונים שלא נמסרו.
- אם חסר מידע, אמור במפורש מה חסר.
- היה פרקטי וקצר.
- כתוב בעברית.
- אם המשתמש שואל על שדה מסוים, הסבר בשפה פשוטה מה השדה אומר, מתי בדרך כלל ממלאים כן או לא, ומה כדאי לבדוק לפני שמחליטים.
- אינך מחליף רואה חשבון; כאשר צריך אימות מול שומה או מסמך, אמור זאת.
"""


async def answer_advisor_question(request: AdvisorQuestionRequest) -> str:
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
    advisor_lines = "\n".join(
        f"- [{item.level}] {item.title}: {item.detail}"
        for item in request.advisor_items
    ) or "- אין פריטי השלמה מיוחדים"
    warning_lines = "\n".join(f"- {warning}" for warning in request.warnings) or "- אין אזהרות"
    document_lines = "\n".join(f"- {name}" for name in request.source_documents) or "- לא הועלו מסמכים"

    user_prompt = f"""
שנת מס: {request.tax_year}
יתרה/החזר נוכחי: {request.balance}
מס נטו: {request.net_tax}

הקשר השדה הנוכחי:
- קטגוריה: {request.current_section or 'לא נבחרה'}
- שדה: {request.current_field_label or 'לא נבחר'}
- הסבר פנימי: {request.current_field_explanation or 'אין'}

מסמכים שהועלו:
{document_lines}

אזהרות חישוב:
{warning_lines}

השלמות ובדיקות מומלצות:
{advisor_lines}

שאלת המשתמש:
{request.question}
""".strip()

    kwargs: dict = {
        "model": llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "api_key": api_key,
        "max_tokens": 400,
        "timeout": 30,
    }
    if provider == "azure" and api_base:
        kwargs["api_base"] = api_base

    response = await litellm.acompletion(**kwargs)
    return response.choices[0].message.content.strip()


# ------------- Guide loader for chat grounding -------------

_GUIDES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "IRS_Docs"
_guide_cache: dict[int, str] = {}


def _load_guide(year: int) -> str:
    if year in _guide_cache:
        return _guide_cache[year]
    path = _GUIDES_DIR / f"guide_{year}_raw.md"
    if not path.exists():
        # fallback to nearest available
        for fallback in sorted(_GUIDES_DIR.glob("guide_*_raw.md"), reverse=True):
            path = fallback
            break
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    # Limit to ~15k chars to stay within context budget
    if len(text) > 15000:
        text = text[:15000] + "\n... (המדריך קוצר)"
    _guide_cache[year] = text
    return text


CHAT_SYSTEM_PROMPT = """אתה עוזר מקצועי לדוח שנתי 1301 בישראל.
יש לך גישה למדריך הרשמי של רשות המסים לשנת המס ולנתוני הטופס הנוכחיים של המשתמש.

כללים:
- ענה בהתבסס על המדריך הרשמי ועל נתוני הטופס שנשלחו אליך.
- הסבר בשפה פשוטה, לא בז'רגון מקצועי מיותר.
- אם הנתונים מצביעים על בעיה או חוסר, אמור זאת.
- אם מישהו שואל על שדה ספציפי, הסבר מה השדה עושה ומה המשמעות במצב שלו.
- כתוב תמיד בעברית.
- אל תמציא נתונים שלא נמסרו.
- אינך מחליף רואה חשבון; כאשר נדרש אימות, אמור זאת.
- אם המשתמש רוצה לדעת מה חסר לו, בדוק את נתוני הטופס ותן המלצות קונקרטיות.
"""


async def answer_chat_question(
    question: str,
    tax_year: int,
    form_summary: str,
    source_documents: list[str],
    warnings: list[str],
    balance: float,
    net_tax: float,
) -> str:
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

    guide_excerpt = _load_guide(tax_year)
    document_lines = "\n".join(f"- {name}" for name in source_documents) or "- לא הועלו מסמכים"
    warning_lines = "\n".join(f"- {w}" for w in warnings) or "- אין אזהרות"

    user_prompt = f"""מצב הטופס הנוכחי של המשתמש:
{form_summary}

יתרה/החזר: {balance}
מס נטו: {net_tax}

מסמכים שהועלו:
{document_lines}

אזהרות:
{warning_lines}

--- קטע מתוך המדריך הרשמי לשנת {tax_year} ---
{guide_excerpt}
--- סוף קטע מדריך ---

שאלת המשתמש:
{question}
""".strip()

    kwargs: dict = {
        "model": llm_model,
        "messages": [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "api_key": api_key,
        "max_tokens": 600,
        "timeout": 30,
    }
    if provider == "azure" and api_base:
        kwargs["api_base"] = api_base

    response = await litellm.acompletion(**kwargs)
    return response.choices[0].message.content.strip()
