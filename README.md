# עוזר דוח שנתי 1301

אפליקציה מקומית שמנחה אותך במילוי טופס 1301 (דוח שנתי למס הכנסה בישראל).

## מה האפליקציה עושה

- **חילוץ אוטומטי** — העלה טפסי 106, 867, אישורי שכירות ומסמכים נוספים, והאפליקציה תחלץ את הנתונים ותמלא את השדות הרלוונטיים בטופס.
- **חישוב מס** — חישוב מס הכנסה, מס ייסף, זיכויים וניכויים בזמן אמת.
- **הסברים לשדות** — לחיצה על קוד שדה (למשל 158, 222, 034) מציגה הסבר מפורט בעברית.
- **צ'אט עם עוזר** — שאל שאלות על הדוח, על שדות ספציפיים, או על מה עוד חסר — העוזר עונה על בסיס המדריך הרשמי של רשות המסים.
- **פרטיות** — הכל רץ מקומית על המחשב שלך. המסמכים והנתונים האישיים לא עולים לענן.

## דרישות מקדימות

- **Python 3.11+**
- **Node.js 18+** ו-npm
- **מפתח API** לספק LLM (OpenAI, Google Gemini, Anthropic Claude, או Azure OpenAI)

## התקנה

### 1. שכפול הפרויקט

```bash
git clone <repo-url>
cd irs-1301
```

### 2. יצירת סביבה וירטואלית ל-Python

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. התקנת כל התלויות

```bash
make install
```

זה מריץ:
- `npm install` בתיקיית `frontend/`
- `pip install -r backend/requirements.txt` בסביבה הוירטואלית

### 4. הגדרת ספק LLM

צור קובץ `.env` בתיקיית `backend/`:

```bash
cp backend/.env.example backend/.env  # אם קיים
# או צור ידנית:
```

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_API_KEY=sk-...
```

ספקים נתמכים:

| ספק | `LLM_PROVIDER` | דוגמת `LLM_MODEL` |
|-----|----------------|---------------------|
| OpenAI | `openai` | `gpt-4o`, `gpt-4o-mini` |
| Google Gemini | `gemini` | `gemini-2.0-flash` |
| Anthropic Claude | `anthropic` | `claude-sonnet-4-20250514` |
| Azure OpenAI | `azure` | `gpt-4o` (+ `AZURE_API_BASE`) |

> אפשר גם להגדיר את הספק דרך דף ההגדרות באפליקציה עצמה.

## הפעלה

```bash
make run
```

זה מפעיל במקביל:
- **Frontend** — Vite dev server על `http://localhost:5173`
- **Backend** — FastAPI/uvicorn על `http://localhost:8000`

פתח בדפדפן: **http://localhost:5173**

## בדיקות

```bash
make test
```

מריץ את בדיקות הבקנד (`pytest`) ובדיקות הפרונטנד (`vitest`).

## בדיקת קוד

```bash
make lint
```

## מבנה הפרויקט

```
irs-1301/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── main.py       # נקודת כניסה
│   │   ├── routers/      # API endpoints
│   │   ├── schemas/      # Pydantic models
│   │   └── services/     # לוגיקה עסקית: מס, LLM, PDF
│   └── tests/
├── frontend/             # React + TypeScript + Tailwind
│   └── src/
│       ├── pages/        # דפי האפליקציה
│       ├── components/   # רכיבי UI
│       └── lib/          # API, utils
├── IRS_Docs/             # סכמת הטופס ומדריכים רשמיים
├── user_data/            # נתוני משתמש (לא ב-git)
├── Makefile
└── REQUIREMENTS.md
```

## שימוש

1. **הגדרות** — בחר ספק LLM והזן מפתח API בדף ההגדרות.
2. **העלאת מסמכים** — העלה טפסי 106, 867, אישורי שכירות וכו'. האפליקציה תחלץ את הנתונים אוטומטית.
3. **מילוי הטופס** — עבור לדף הטופס. שדות שחולצו ממסמכים ימולאו אוטומטית (מסומנים בכחול). תקן או השלם לפי הצורך.
4. **צ'אט** — לחץ על כפתור הצ'אט בפינה השמאלית-תחתונה כדי לשאול שאלות.
5. **תוצאה** — לחץ "חשב" לראות את חישוב המס, ההחזר או התשלום.

## רישיון

שימוש אישי בלבד. אין להסתמך על התוצאות ללא אימות ע״י רואה חשבון או יועץ מס.
