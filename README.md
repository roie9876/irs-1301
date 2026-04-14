# עוזר דוח שנתי 1301

אפליקציה מקומית שמנחה אותך במילוי טופס 1301 (דוח שנתי למס הכנסה בישראל).

## מה האפליקציה עושה

- **חילוץ אוטומטי** — העלה טפסי 106, 867, אישורי שכירות ומסמכים נוספים, והאפליקציה תחלץ את הנתונים ותמלא את השדות הרלוונטיים בטופס.
- **חישוב מס** — חישוב מס הכנסה, מס ייסף, זיכויים וניכויים בזמן אמת.
- **הסברים לשדות** — לחיצה על קוד שדה (למשל 158, 222, 034) מציגה הסבר מפורט בעברית.
- **צ'אט עם עוזר** — שאל שאלות על הדוח, על שדות ספציפיים, או על מה עוד חסר — העוזר עונה על בסיס המדריך הרשמי של רשות המסים.
- **פרטיות** — הכל רץ מקומית על המחשב שלך. המסמכים והנתונים האישיים לא עולים לענן.

![מסך ראשי](main%20screenshot.jpeg)

---

## התקנה — שלב אחר שלב

> **לפני שמתחילים:** צריך להתקין 3 תוכנות חינמיות על המחשב. ההוראות למטה מסבירות בדיוק איך.

---

### שלב 1: התקנת תוכנות נדרשות

#### 🍎 Mac

1. **פתח את Terminal** — לחץ `Cmd + Space`, הקלד `Terminal`, לחץ Enter.

2. **התקן Homebrew** (מנהל חבילות ל-Mac) — הדבק את השורה הזו ולחץ Enter:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
   > אם הוא מבקש סיסמה — הקלד את סיסמת המחשב שלך (לא תראה את האותיות, זה תקין).

3. **התקן Python, Node.js ו-Git:**
   ```bash
   brew install python node git
   ```

4. **ודא שהכל הותקן** (אופציונלי):
   ```bash
   python3 --version && node --version && git --version
   ```
   אמור להופיע מספר גרסה לכל אחד.

#### 🪟 Windows

1. **הורד והתקן את התוכנות הבאות** (לחץ על כל קישור, הורד, והרץ את ההתקנה):

   | תוכנה | קישור להורדה |
   |--------|-------------|
   | Python | [python.org/downloads](https://www.python.org/downloads/) |
   | Node.js | [nodejs.org](https://nodejs.org/) — בחר בגרסת **LTS** |
   | Git | [git-scm.com/download/win](https://git-scm.com/download/win) |

   > ⚠️ **חשוב בהתקנת Python:** סמן את התיבה **"Add Python to PATH"** במסך הראשון של ההתקנה!

2. **פתח את PowerShell** — לחץ `Win + X` ובחר **"Terminal"** או **"PowerShell"**.

3. **ודא שהכל הותקן** (אופציונלי):
   ```powershell
   python --version; node --version; git --version
   ```

---

### שלב 2: הורדת הפרויקט

פתח את ה-Terminal (Mac) או PowerShell (Windows) והריצ:

```bash
git clone <repo-url>
cd irs-1301
```

> החלף את `<repo-url>` בקישור שקיבלת לפרויקט.

---

### שלב 3: הכנת סביבת העבודה

#### 🍎 Mac

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
```

#### 🪟 Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
cd frontend && npm install && cd ..
.venv\Scripts\pip install -r backend\requirements.txt
```

> אם PowerShell מסרב להריץ סקריפטים, הריצ' קודם:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

---

### שלב 4: הגדרת מפתח AI

האפליקציה צריכה מפתח API של ספק AI (בינה מלאכותית) כדי לחלץ נתונים ממסמכים ולענות על שאלות.

> **זה נעשה מתוך האפליקציה עצמה** — אחרי שתפעיל אותה (שלב 5), לך לדף **הגדרות** ➜ בחר ספק ➜ הדבק את המפתח ➜ לחץ שמור. זה הכל!

**איפה משיגים מפתח?**

| ספק | איפה להירשם ולקבל מפתח |
|-----|------------------------|
| OpenAI | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| Google Gemini | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| Anthropic Claude | [console.anthropic.com](https://console.anthropic.com/) |
| Azure OpenAI | דרך פורטל Azure |

---

### שלב 5: הפעלה 🚀

#### 🍎 Mac

```bash
make run
```

#### 🪟 Windows

פתח **שני חלונות** של PowerShell:

**חלון 1 — Backend:**
```powershell
cd irs-1301
.venv\Scripts\Activate.ps1
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

**חלון 2 — Frontend:**
```powershell
cd irs-1301\frontend
npm run dev
```

---

### פתח בדפדפן

כשהכל רץ, פתח את **Chrome** (או כל דפדפן) ולך ל:

👉 **http://localhost:5173**

---

## שימוש

1. **הגדרות** — בחר ספק AI והזן מפתח API בדף ההגדרות.
2. **העלאת מסמכים** — העלה טפסי 106, 867, אישורי שכירות וכו'. האפליקציה תחלץ את הנתונים אוטומטית.
3. **מילוי הטופס** — עבור לדף הטופס. שדות שחולצו ממסמכים ימולאו אוטומטית (מסומנים בכחול). תקן או השלם לפי הצורך.
4. **צ'אט** — לחץ על כפתור הצ'אט בפינה השמאלית-תחתונה כדי לשאול שאלות.
5. **תוצאה** — לחץ "חשב" לראות את חישוב המס, ההחזר או התשלום.

---

## הפעלת האפליקציה בפעמים הבאות

אחרי ההתקנה הראשונית, בכל פעם שרוצים להשתמש באפליקציה:

#### 🍎 Mac
```bash
cd irs-1301
source .venv/bin/activate
make run
```

#### 🪟 Windows
מריצים את שני חלונות ה-PowerShell כמו בשלב 5 למעלה.

---

## פתרון בעיות נפוצות

| בעיה | פתרון |
|------|-------|
| `command not found: python3` | Python לא הותקן, או לא נוסף ל-PATH. התקן מחדש וסמן "Add to PATH". |
| `command not found: node` / `npm` | Node.js לא הותקן. הורד מ-[nodejs.org](https://nodejs.org/). |
| `command not found: make` (Windows) | רגיל ב-Windows. עקוב אחרי הוראות Windows שלמעלה (בלי `make`). |
| האפליקציה עולה אבל לא מחלצת מסמכים | ודא שמילאת מפתח API בדף ההגדרות או בקובץ `.env`. |
| `ModuleNotFoundError` | הסביבה הווירטואלית לא פעילה. הרץ `source .venv/bin/activate` (Mac) או `.venv\Scripts\Activate.ps1` (Windows). |
| `EACCES: permission denied` (Mac) | הרץ עם `sudo` או תקן הרשאות npm: `sudo chown -R $USER /usr/local/lib/node_modules` |

---

## למפתחים

### בדיקות
```bash
make test
```

### בדיקת קוד
```bash
make lint
```

### מבנה הפרויקט

```
irs-1301/
├── backend/              # FastAPI backend (Python)
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

---

## רישיון

שימוש אישי בלבד. אין להסתמך על התוצאות ללא אימות ע״י רואה חשבון או יועץ מס.
