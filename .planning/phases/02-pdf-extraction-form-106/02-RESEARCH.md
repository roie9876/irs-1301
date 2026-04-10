# Phase 2: PDF Extraction — Form 106 - Research

**Researched:** 2026-04-10
**Domain:** PDF text extraction, LLM-based data structuring, FastAPI file upload, React upload UI
**Confidence:** HIGH

## Summary

Phase 2 adds document upload and extraction capability: users upload Form 106 PDFs (annual employer tax certificates), the backend extracts text via PyMuPDF and structures it via LLM, and users review/correct extracted data in a React form. This is a full-stack feature spanning a new FastAPI router, a new React page, and filesystem-based persistence.

The technical approach is straightforward. **PyMuPDF 1.27.2** is already installed and handles text extraction from digital PDFs with a simple `page.get_text("text")` call. Hebrew text extracts correctly from digital PDFs (text layer is Unicode, not a rendering issue). **LiteLLM 1.83.4** is already installed and the `acompletion()` pattern is established in `llm.py`. The LLM structures raw text into JSON using the configured provider. **python-multipart** must be added to requirements.txt for FastAPI file uploads. Frontend uses native HTML5 drag-and-drop (no library needed) — consistent with CONTEXT.md D-03.

**Primary recommendation:** Follow the existing Phase 1 patterns exactly — new router in `backend/app/routers/`, new schema in `backend/app/schemas/`, new service in `backend/app/services/`, new page in `frontend/src/pages/`. Store PDFs and JSON sidecars in `user_data/documents/` (gitignored).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** PyMuPDF (fitz) for text extraction from digital PDFs. No OCR needed — Form 106 is always digital.
- **D-02:** Two-phase: PyMuPDF extracts raw text → LLM structures into JSON. Handles layout variation across employers.
- **D-03:** Drag-and-drop zone with file picker fallback. Multiple files. Cards with filename + status.
- **D-04:** Store PDFs in `user_data/documents/`. Extracted data as JSON sidecar (`filename.106.json`).
- **D-05:** Structured table/form with editable fields, grouped by category, Hebrew labels with field numbers, color-coded confidence (green=high, yellow=needs review).
- **D-06:** Each Form 106 gets its own extraction card. Summary section with aggregated totals. Individual values editable, totals auto-recalculate.
- **D-07:** Extract: employer name+ID, tax year, gross salary, tax withheld, pension employer contribution, insured income, convalescence pay, education fund, work days, National Insurance, Health Insurance.
- **D-08:** Add "מסמכים" nav link next to "הגדרות". Route: `/documents`.
- **D-09:** Structured system prompt with expected JSON schema, Hebrew+English field names, confidence score 0-1 per field, null for missing fields.
- **D-10:** Invalid PDF or extraction failure → inline error on file card. Don't crash.
- **D-11:** Save extracted + user-corrected data as JSON in `user_data/documents/`. Load existing extractions on page load.

### Claude's Discretion
None specified — all decisions locked.

### Deferred Ideas (OUT OF SCOPE)
- OCR for scanned/photographed Form 106 — digital PDFs only
- Automatic document type detection (106 vs 867) — Phase 6 scope
- Batch processing of multiple document types — Phase 6 scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOC-01 | Upload Form 106 (digital PDF) → extract: gross salary, tax withheld, pension/provident fund, work days | PyMuPDF text extraction + LLM structuring + D-07 field schema |
| DOC-02 | Upload multiple Form 106s (multiple employers) → aggregate data | Multi-file upload endpoint + D-06 aggregation UI |
| DOC-09 | User reviews extracted data and can manually correct any field | D-05 review table with editable fields + D-11 save corrections |
| DOC-10 | All documents and data stored in local folder only | D-04 `user_data/documents/` + gitignore pattern |
</phase_requirements>

## Project Constraints (from copilot-instructions.md)

The copilot-instructions.md establishes the tech stack:
- Backend: FastAPI + Python (venv at `.venv/`), port 8000
- Frontend: React + Vite + shadcn/ui, port 5173, proxy `/api/*` → backend
- Hebrew RTL interface
- Local storage for personal data (gitignored)
- LLM via LiteLLM (configured in Phase 1)

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyMuPDF (fitz) | 1.27.2.2 | PDF text extraction | Already in venv. `page.get_text("text")` extracts Unicode text from digital PDFs. Hebrew works natively (text layer is Unicode). |
| LiteLLM | 1.83.4 | LLM calls for data structuring | Already in venv. `acompletion()` pattern established in `llm.py`. JSON mode supported via `response_format`. |
| FastAPI | 0.135.3 | File upload endpoint | Already in venv. `UploadFile` + `File` for multipart uploads. |
| Pydantic | 2.12.5 | Request/response schemas | Already in venv. Schema validation for extraction results. |
| React | 19.2.4 | Upload + review UI | Already installed. Component patterns established in SettingsPage. |
| react-router-dom | 7.14.0 | Routing for `/documents` | Already installed. Route pattern established in App.tsx. |
| shadcn/ui | 4.2.0 | UI components | Already installed. Card, Button, Input, Label available. |
| lucide-react | 1.8.0 | Icons | Already installed. Used in AppLayout. |

### Must Add
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-multipart | latest | FastAPI file upload support | Required by FastAPI for `UploadFile`. Not currently installed. Add to `backend/requirements.txt`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyMuPDF text extraction | pdfplumber | pdfplumber has better table extraction, but PyMuPDF is already installed and Form 106 raw text + LLM structuring works well enough. No need for two PDF libraries. |
| LLM structuring | Pure regex | Fragile across employer variations. LLM handles layout differences gracefully. |
| Native HTML5 DnD | react-dropzone | Adds a dependency for something achievable with ~30 lines of native API. D-03 explicitly says "no external library." |

**Installation:**
```bash
cd backend && ../.venv/bin/pip install python-multipart && echo "python-multipart" >> requirements.txt
```

**Version verification:**
- PyMuPDF: 1.27.2.2 (verified via `import fitz; print(fitz.__version__)`)
- LiteLLM: 1.83.4 (verified via `pip show litellm`)
- FastAPI: 0.135.3 (verified via `requirements.txt`)
- python-multipart: not installed — must add
- starlette: 1.0.0 (FastAPI dependency, handles UploadFile internally)

## Architecture Patterns

### Project Structure (additions for Phase 2)
```
backend/
├── app/
│   ├── routers/
│   │   └── documents.py       # POST /api/documents/upload, GET /api/documents, PUT /api/documents/{id}
│   ├── schemas/
│   │   └── documents.py       # ExtractionResult, DocumentResponse, FieldValue models
│   └── services/
│       ├── llm.py              # Existing — add extract_form106_data() here
│       └── pdf.py              # NEW — PyMuPDF text extraction service
├── tests/
│   └── test_documents.py       # Upload + extraction tests
user_data/
└── documents/                  # Gitignored — PDFs + JSON sidecars
frontend/
└── src/
    ├── pages/
    │   └── DocumentsPage.tsx   # Upload + review page
    └── components/
        └── documents/
            ├── DropZone.tsx     # Drag-and-drop upload area
            ├── FileCard.tsx     # Individual file status card
            ├── ExtractionTable.tsx  # Editable extraction results
            └── AggregationSummary.tsx  # Multi-employer totals
```

### Pattern 1: PyMuPDF Text Extraction
**What:** Extract all text from a Form 106 PDF, page by page
**When to use:** First phase of the two-phase extraction pipeline (D-02)
**Example:**
```python
# backend/app/services/pdf.py
import fitz  # PyMuPDF

def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from a PDF file, page by page."""
    doc = fitz.open(file_path)
    try:
        pages_text = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text = page.get_text("text")  # Returns Unicode str — Hebrew works natively
            pages_text.append(text)
        return "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
    finally:
        doc.close()
```

**Key API details (verified against PyMuPDF 1.27.2):**
- `fitz.open(filepath)` — opens PDF, returns `Document`
- `doc.page_count` — total pages (int)
- `doc.load_page(n)` — returns `Page` object (0-indexed)
- `page.get_text("text")` — returns plain text as `str` (Unicode, so Hebrew is fine)
- `page.get_text("blocks")` — returns list of `(x0, y0, x1, y1, text, block_no, block_type)` tuples
- `page.get_text("dict")` — returns structured dict with blocks → lines → spans (for position analysis)
- Always call `doc.close()` or use context manager

**Hebrew text extraction notes:**
- Digital/text-based PDFs store text as Unicode codepoints — PyMuPDF reads them correctly
- RTL rendering is a display concern, not an extraction concern — extracted text is logical order (correct for processing)
- Form 106 is always generated digitally by employer payroll systems — no OCR needed

### Pattern 2: LLM-Based Data Structuring (D-02, D-09)
**What:** Send extracted raw text to LLM with structured prompt to get JSON output
**When to use:** Second phase of extraction — after PyMuPDF gives us raw text
**Example:**
```python
# In backend/app/services/llm.py — add to existing file
import json
import litellm

FORM_106_EXTRACTION_PROMPT = """You are a data extraction assistant for Israeli tax forms.
Extract the following fields from the Form 106 (טופס 106) text provided.
Return a JSON object with these exact keys. For each field, provide "value" and "confidence" (0.0-1.0).
If a field is not found, set value to null and confidence to 0.

Fields to extract:
- employer_name: שם המעסיק
- employer_id: מספר מזהה מעסיק (ח.פ./ע.מ.)
- tax_year: שנת מס
- gross_salary: הכנסה ברוטו (שכר עבודה) → Form 1301 field 158/172
- tax_withheld: מס הכנסה שנוכה במקור → Form 1301 section 84
- pension_employer: הפרשות מעסיק לפנסיה (תגמולים + פיצויים) → Form 1301 field 248/249
- insured_income: הכנסה מבוטחת → Form 1301 field 244/245
- convalescence_pay: דמי הבראה → Form 1301 field 011/012
- education_fund: קרן השתלמות (הפרשת מעסיק) → Form 1301 field 218/219
- work_days: ימי עבודה
- national_insurance: ביטוח לאומי שנוכה
- health_insurance: ביטוח בריאות שנוכה

Return ONLY valid JSON. Example format:
{
  "employer_name": {"value": "חברה לדוגמא בע\"מ", "confidence": 0.95},
  "tax_year": {"value": 2024, "confidence": 1.0},
  "gross_salary": {"value": 180000, "confidence": 0.9},
  "work_days": {"value": null, "confidence": 0}
}"""

async def extract_form106_data(raw_text: str) -> dict:
    """Send raw PDF text to LLM for structured extraction."""
    from dotenv import load_dotenv
    import os
    
    load_dotenv(ENV_PATH, override=True)
    
    provider = os.getenv("LLM_PROVIDER", "")
    model = os.getenv("LLM_MODEL", "")
    api_key = os.getenv("LLM_API_KEY", "")
    api_base = os.getenv("AZURE_API_BASE", "")
    
    if not all([provider, model, api_key]):
        raise ValueError("LLM not configured. Please configure in Settings first.")
    
    prefix = PROVIDER_PREFIX.get(provider, "")
    llm_model = f"{prefix}{model}"
    
    kwargs = {
        "model": llm_model,
        "messages": [
            {"role": "system", "content": FORM_106_EXTRACTION_PROMPT},
            {"role": "user", "content": f"Extract data from this Form 106:\n\n{raw_text}"},
        ],
        "api_key": api_key,
        "response_format": {"type": "json_object"},  # Force JSON output
    }
    if provider == "azure" and api_base:
        kwargs["api_base"] = api_base
    
    response = await litellm.acompletion(**kwargs)
    content = response.choices[0].message.content
    return json.loads(content)
```

**LiteLLM JSON mode notes:**
- `response_format={"type": "json_object"}` works with OpenAI, Azure OpenAI, Gemini, Anthropic via LiteLLM
- LiteLLM handles the per-provider translation for JSON mode
- The system prompt MUST mention "JSON" when using json_object mode (OpenAI requirement, LiteLLM passes through)
- Anthropic JSON mode: LiteLLM adds prefill `{` and sets stop sequence — works transparently

### Pattern 3: FastAPI File Upload (D-03, D-10)
**What:** Accept multipart file uploads, validate, save to disk
**When to use:** POST `/api/documents/upload` endpoint
**Example:**
```python
# backend/app/routers/documents.py
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List

from app.services.pdf import extract_text_from_pdf
from app.services.llm import extract_form106_data

router = APIRouter(tags=["documents"])

DOCUMENTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "user_data" / "documents"

@router.post("/documents/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload one or more Form 106 PDFs for extraction."""
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    
    results = []
    for file in files:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            results.append({
                "filename": file.filename or "unknown",
                "status": "error",
                "error": "הקובץ אינו PDF תקין",
            })
            continue
        
        # Validate content type
        if file.content_type and file.content_type != "application/pdf":
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": "הקובץ אינו PDF תקין",
            })
            continue
        
        # Save file with unique prefix to avoid collisions
        doc_id = uuid.uuid4().hex[:8]
        safe_filename = f"{doc_id}_{file.filename}"
        file_path = DOCUMENTS_DIR / safe_filename
        
        content = await file.read()
        file_path.write_bytes(content)
        
        try:
            # Phase 1: Extract text
            raw_text = extract_text_from_pdf(str(file_path))
            if not raw_text.strip():
                results.append({
                    "filename": file.filename,
                    "doc_id": doc_id,
                    "status": "error",
                    "error": "לא ניתן לחלץ טקסט מהקובץ",
                })
                continue
            
            # Phase 2: LLM structuring
            extracted = await extract_form106_data(raw_text)
            
            # Save JSON sidecar (D-04)
            json_path = DOCUMENTS_DIR / f"{safe_filename}.106.json"
            import json
            json_path.write_text(json.dumps({
                "doc_id": doc_id,
                "original_filename": file.filename,
                "extracted": extracted,
                "user_corrected": False,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            
            results.append({
                "filename": file.filename,
                "doc_id": doc_id,
                "status": "success",
                "extracted": extracted,
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "doc_id": doc_id,
                "status": "error",
                "error": f"שגיאה בחילוץ: {str(e)}",
            })
    
    return {"results": results}
```

**FastAPI file upload notes:**
- `python-multipart` MUST be installed — FastAPI raises a runtime error without it when handling `UploadFile`
- `UploadFile` is async: use `await file.read()` to get bytes
- `File(...)` marks the parameter as required
- `List[UploadFile]` accepts multiple files in one request
- Content type check is advisory (browsers may not send accurate MIME types)
- File size: Form 106 PDFs are typically < 1MB; no explicit size limit needed for local app

### Pattern 4: Frontend Upload with Native HTML5 DnD (D-03)
**What:** Drag-and-drop zone with file input fallback
**When to use:** Documents page upload area
**Example:**
```tsx
// frontend/src/components/documents/DropZone.tsx
import { useCallback, useState, DragEvent, ChangeEvent } from 'react'
import { Upload } from 'lucide-react'

interface DropZoneProps {
  onFiles: (files: File[]) => void
  disabled?: boolean
}

export function DropZone({ onFiles, disabled }: DropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false)

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragOver(false)
    const files = Array.from(e.dataTransfer.files).filter(
      f => f.type === 'application/pdf'
    )
    if (files.length > 0) onFiles(files)
  }, [onFiles])

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false)
  }, [])

  const handleFileInput = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (files.length > 0) onFiles(files)
    e.target.value = '' // Allow re-selecting same file
  }, [onFiles])

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      className={`
        border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer
        ${isDragOver ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'}
        ${disabled ? 'opacity-50 pointer-events-none' : ''}
      `}
      onClick={() => document.getElementById('file-input')?.click()}
    >
      <Upload className="h-10 w-10 mx-auto mb-3 text-muted-foreground" />
      <p className="text-sm text-muted-foreground">
        גרור קבצי PDF לכאן או לחץ לבחירה
      </p>
      <p className="text-xs text-muted-foreground/60 mt-1">
        טופס 106 בלבד • ניתן להעלות מספר קבצים
      </p>
      <input
        id="file-input"
        type="file"
        accept=".pdf,application/pdf"
        multiple
        className="hidden"
        onChange={handleFileInput}
      />
    </div>
  )
}
```

### Pattern 5: API Utility for File Upload
**What:** The existing `api()` utility sets `Content-Type: application/json` — file uploads need `FormData` without manually setting Content-Type
**When to use:** Uploading files from frontend to backend
**Example:**
```tsx
// In frontend/src/lib/api.ts — add a separate function or handle in DocumentsPage
export async function uploadFiles(files: File[]): Promise<any> {
  const formData = new FormData()
  files.forEach(f => formData.append('files', f))

  const response = await fetch('/api/documents/upload', {
    method: 'POST',
    body: formData,
    // Do NOT set Content-Type — browser sets multipart boundary automatically
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new ApiError(response.status, error.detail || response.statusText)
  }

  return response.json()
}
```

**Critical:** Do NOT set `Content-Type` header for FormData — the browser must set it with the multipart boundary. The existing `api()` function always sets `Content-Type: application/json`, so file uploads need a separate function or the `api()` function needs conditional logic.

### Pattern 6: JSON Sidecar Persistence (D-04, D-11)
**What:** Store extraction results as JSON files alongside PDFs
**When to use:** Saving extracted data, loading on page return
**Example file structure:**
```
user_data/documents/
├── a1b2c3d4_form106_employer1.pdf
├── a1b2c3d4_form106_employer1.pdf.106.json
├── e5f6g7h8_form106_employer2.pdf
└── e5f6g7h8_form106_employer2.pdf.106.json
```

**JSON sidecar format:**
```json
{
  "doc_id": "a1b2c3d4",
  "original_filename": "form106_employer1.pdf",
  "extracted": {
    "employer_name": {"value": "חברה לדוגמא בע\"מ", "confidence": 0.95},
    "employer_id": {"value": "514832769", "confidence": 0.9},
    "tax_year": {"value": 2024, "confidence": 1.0},
    "gross_salary": {"value": 180000.00, "confidence": 0.92},
    "tax_withheld": {"value": 32400.00, "confidence": 0.88},
    "pension_employer": {"value": 11700.00, "confidence": 0.85},
    "insured_income": {"value": 160000.00, "confidence": 0.8},
    "convalescence_pay": {"value": 4700.00, "confidence": 0.75},
    "education_fund": {"value": 13500.00, "confidence": 0.82},
    "work_days": {"value": 240, "confidence": 0.7},
    "national_insurance": {"value": 7200.00, "confidence": 0.85},
    "health_insurance": {"value": 3600.00, "confidence": 0.85}
  },
  "user_corrected": false
}
```

When user corrects a field, update the JSON and set `"user_corrected": true`. Optionally track which fields were corrected.

### Pattern 7: Navigation Integration (D-08)
**What:** Add Documents link to header nav, add route
**Example (AppLayout.tsx):**
```tsx
// Add next to the Settings link:
<Link to="/documents" ...>
  <FileText className="h-4 w-4" />
  מסמכים
</Link>
```

**Example (App.tsx):**
```tsx
<Route path="/documents" element={<DocumentsPage />} />
```

### Pattern 8: Editable Extraction Table (D-05, D-09)
**What:** Display extracted fields in an editable table with confidence indicators
**When to use:** After successful extraction, show results for review

Field display spec:
| Key | Hebrew Label | 1301 Field | Type |
|-----|-------------|------------|------|
| employer_name | שם המעסיק | — | string |
| employer_id | מספר מזהה מעסיק | — | string |
| tax_year | שנת מס | — | number |
| gross_salary | הכנסה ברוטו | 158/172 | number (₪) |
| tax_withheld | מס שנוכה במקור | סעיף 84 | number (₪) |
| pension_employer | הפרשות מעסיק לפנסיה | 248/249 | number (₪) |
| insured_income | הכנסה מבוטחת | 244/245 | number (₪) |
| convalescence_pay | דמי הבראה | 011/012 | number (₪) |
| education_fund | קרן השתלמות | 218/219 | number (₪) |
| work_days | ימי עבודה | — | number |
| national_insurance | ביטוח לאומי | — | number (₪) |
| health_insurance | ביטוח בריאות | — | number (₪) |

Confidence color coding (D-05):
- `≥ 0.8`: green (bg-green-50, text-green-700) — high confidence
- `0.5–0.79`: yellow (bg-yellow-50, text-yellow-700) — needs review
- `< 0.5` or null: red (bg-red-50, text-red-700) — likely missing/wrong

### Anti-Patterns to Avoid
- **Don't import the full `api()` function for file uploads** — it sets `Content-Type: application/json` which breaks multipart
- **Don't use `response_format` with Anthropic directly** — LiteLLM handles the translation, but the system prompt must contain "JSON" for OpenAI models
- **Don't read the entire PDF into memory with `doc.tobytes()`** — use `page.get_text()` per page
- **Don't block the event loop** — PyMuPDF is synchronous; for truly large PDFs, consider `asyncio.to_thread()`, but Form 106 is typically 1-3 pages, so it's fine inline

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom PDF parser | `fitz.open()` + `page.get_text("text")` | PDF format is complex; PyMuPDF handles fonts, encodings, text ordering |
| Hebrew field name matching | Regex patterns per employer | LLM structured extraction | Form 106 layouts vary between payroll systems; LLM generalizes |
| Multipart form parsing | Manual boundary parsing | FastAPI `UploadFile` + `python-multipart` | Security-critical parsing with edge cases |
| UUID generation | Custom ID scheme | `uuid.uuid4().hex[:8]` | Sufficient uniqueness for a local single-user app |
| Drag and drop | react-dropzone library | Native HTML5 DnD API | ~30 lines vs adding a dependency; D-03 says no external library |

## Common Pitfalls

### Pitfall 1: Missing python-multipart
**What goes wrong:** FastAPI imports `UploadFile` fine but raises `RuntimeError` at request time: "Install python-multipart"
**Why it happens:** `python-multipart` is not in `requirements.txt` and not currently installed
**How to avoid:** Add `python-multipart` to `requirements.txt` and install before implementing the upload endpoint
**Warning signs:** Tests pass import-time but fail on actual upload requests

### Pitfall 2: Content-Type Header on FormData Upload
**What goes wrong:** Backend receives empty files or 422 Unprocessable Entity
**Why it happens:** Frontend manually sets `Content-Type: application/json` (as in the existing `api()` function) instead of letting the browser set the multipart boundary
**How to avoid:** Create a separate `uploadFiles()` function that does NOT set Content-Type header; let the browser set `multipart/form-data; boundary=...` automatically
**Warning signs:** Network tab shows wrong Content-Type header

### Pitfall 3: File Path Resolution for user_data/
**What goes wrong:** `user_data/documents/` gets created in wrong location (e.g., inside `backend/` instead of project root)
**Why it happens:** Uvicorn's working directory is `backend/` (see Makefile: `cd backend && ../.venv/bin/python -m uvicorn ...`)
**How to avoid:** Use `Path(__file__).resolve().parent.parent.parent.parent / "user_data"` to navigate from `backend/app/routers/documents.py` to project root. Or define `PROJECT_ROOT` in a shared config. Follow the same pattern as `ENV_PATH` in `llm.py`.
**Warning signs:** Files appear in `backend/user_data/` instead of `./user_data/`

### Pitfall 4: LLM JSON Mode Prompt Requirement
**What goes wrong:** OpenAI returns error: "Must include 'json' in prompt when using json_object response_format"
**Why it happens:** OpenAI requires the word "JSON" in the system or user message when `response_format={"type": "json_object"}` is set
**How to avoid:** The system prompt already includes "Return a JSON object" — ensure this stays in the prompt
**Warning signs:** Works with Anthropic/Gemini but fails with OpenAI

### Pitfall 5: Large PDF Text Overwhelming LLM Context
**What goes wrong:** LLM errors on token limit or costs spike
**Why it happens:** Form 106 is typically 1-3 pages, but corrupted/wrong PDFs might be large
**How to avoid:** Add a text length guard. If extracted text > ~10,000 chars, truncate or reject. Form 106 text is typically < 2,000 chars.
**Warning signs:** Slow extraction, high API costs, timeout errors

### Pitfall 6: JSON Sidecar Encoding
**What goes wrong:** Hebrew text in JSON files becomes `\u05d0\u05d1...` (escaped Unicode)
**Why it happens:** Python's `json.dumps()` defaults to `ensure_ascii=True`
**How to avoid:** Always use `json.dumps(..., ensure_ascii=False, indent=2)` when writing JSON with Hebrew content
**Warning signs:** JSON files are unreadable in a text editor

### Pitfall 7: Gitignore for user_data/
**What goes wrong:** User's personal tax documents get committed to GitHub
**Why it happens:** `user_data/` directory not in `.gitignore`
**How to avoid:** Add `user_data/` to `.gitignore` immediately when creating the directory (or verify it's already there from Phase 1)
**Warning signs:** `git status` shows PDF files

## Code Examples

### Adding a New Router (following Phase 1 pattern)
```python
# backend/app/main.py — add one line
from app.routers import settings, documents  # add documents

# ...existing middleware...

app.include_router(settings.router, prefix="/api")
app.include_router(documents.router, prefix="/api")  # add this line
```

### Pydantic Schema for Extraction Results
```python
# backend/app/schemas/documents.py
from pydantic import BaseModel
from typing import Optional

class FieldValue(BaseModel):
    value: Optional[float | str | int] = None
    confidence: float = 0.0

class Form106Extraction(BaseModel):
    employer_name: FieldValue
    employer_id: FieldValue
    tax_year: FieldValue
    gross_salary: FieldValue
    tax_withheld: FieldValue
    pension_employer: FieldValue
    insured_income: FieldValue
    convalescence_pay: FieldValue
    education_fund: FieldValue
    work_days: FieldValue
    national_insurance: FieldValue
    health_insurance: FieldValue

class DocumentInfo(BaseModel):
    doc_id: str
    original_filename: str
    extracted: Form106Extraction
    user_corrected: bool = False

class UploadResult(BaseModel):
    filename: str
    doc_id: str = ""
    status: str  # "success" | "error"
    error: str = ""
    extracted: Optional[Form106Extraction] = None

class UploadResponse(BaseModel):
    results: list[UploadResult]
```

### Aggregation Logic (D-06)
```typescript
// Frontend aggregation — sum numeric fields across documents
function aggregateExtractions(docs: DocumentInfo[]): Record<string, number> {
  const numericFields = [
    'gross_salary', 'tax_withheld', 'pension_employer',
    'insured_income', 'convalescence_pay', 'education_fund',
    'work_days', 'national_insurance', 'health_insurance'
  ]
  
  const totals: Record<string, number> = {}
  for (const field of numericFields) {
    totals[field] = docs.reduce((sum, doc) => {
      const val = doc.extracted[field]?.value
      return sum + (typeof val === 'number' ? val : 0)
    }, 0)
  }
  return totals
}
```

### GET /api/documents — Load Existing Extractions (D-11)
```python
@router.get("/documents")
async def list_documents():
    """Load all existing extractions from disk."""
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    documents = []
    for json_file in sorted(DOCUMENTS_DIR.glob("*.106.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            documents.append(data)
        except (json.JSONDecodeError, IOError):
            continue  # Skip corrupted files
    return {"documents": documents}
```

## Form 106 Field Schema Reference

From `IRS_Docs/form_1301_schema.json` → `key_source_documents.form_106.key_fields_mapped`:

| Form 106 Field | 1301 Mapping | 1301 Section |
|----------------|-------------|--------------|
| gross_salary | field 158/172 | Section 3 (הכנסה ממשכורת) |
| tax_withheld | section 84 | Section 84 (מס שנוכה ממשכורת) |
| pension_employer | field 248/249 | Section 59 (הפקדות מעביד לפנסיה) |
| insured_income | field 244/245 | Section 58 (הכנסה מבוטחת) |
| convalescence_pay | field 011/012 | Section 60 (דמי הבראה) |
| education_fund | field 218/219 | Section 52 (קרן השתלמות) |

Additional fields (D-07, not in schema mapping but needed):
- `employer_name`, `employer_id`: identification, no 1301 mapping
- `tax_year`: verification, no direct 1301 mapping
- `work_days`: used for various calculations
- `national_insurance`, `health_insurance`: withheld amounts, used for deduction calculations

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PyMuPDF AGPL license | PyMuPDF dual license (AGPL or commercial) | 2024 | License concerns for commercial use; fine for personal local app |
| Manual regex parsing of forms | LLM-based extraction | 2023-2024 | Handles layout variation, multiple languages, confidence scoring |
| python-multipart separate install | Still separate from FastAPI | Ongoing | Must explicitly install and add to requirements.txt |
| `litellm.completion()` (sync) | `litellm.acompletion()` (async) | Standard | Use async version in FastAPI async endpoints |

## Open Questions

1. **LLM response_format support across providers**
   - What we know: OpenAI, Azure, Gemini support `json_object` mode. Anthropic is handled by LiteLLM via prefill.
   - What's unclear: If a user's specific model version doesn't support JSON mode, the fallback behavior
   - Recommendation: Wrap JSON parsing in try/except; if `json.loads()` fails, try extracting JSON from markdown code blocks (LLMs sometimes wrap in ```json...```)

2. **Form 106 layout variation**
   - What we know: Different payroll systems (Hilan, Malam Team, Shapir, etc.) produce Forms 106 with different layouts
   - What's unclear: Exact range of variation and whether the LLM prompt generalizes across all of them
   - Recommendation: Start with the prompt as designed; iterate based on real user PDFs. The confidence score will flag uncertain extractions.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | Runtime | ✓ | 3.14 | — |
| PyMuPDF | PDF extraction | ✓ | 1.27.2.2 | — |
| LiteLLM | LLM calls | ✓ | 1.83.4 | — |
| FastAPI | API endpoints | ✓ | 0.135.3 | — |
| python-multipart | File upload | ✗ | — | Must install (`pip install python-multipart`) |
| Node.js | Frontend dev | ✓ | (via npm) | — |
| React + Vite | Frontend UI | ✓ | 19.2.4 / 8.0.4 | — |

**Missing dependencies with no fallback:**
- `python-multipart` — must be installed for FastAPI file uploads. Add to `requirements.txt`.

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | None (pytest discovery via `backend/tests/`) |
| Quick run command | `cd backend && ../.venv/bin/python -m pytest tests/test_documents.py -x` |
| Full suite command | `cd backend && ../.venv/bin/python -m pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOC-01 | Upload PDF → extract structured data | unit (mock LLM) | `pytest tests/test_documents.py::test_upload_pdf_extracts_data -x` | ❌ Wave 0 |
| DOC-01 | PDF text extraction works | unit | `pytest tests/test_documents.py::test_extract_text_from_pdf -x` | ❌ Wave 0 |
| DOC-02 | Upload multiple PDFs → get results per file | unit | `pytest tests/test_documents.py::test_upload_multiple_files -x` | ❌ Wave 0 |
| DOC-09 | PUT endpoint updates corrected data | unit | `pytest tests/test_documents.py::test_update_document -x` | ❌ Wave 0 |
| DOC-10 | Files saved to user_data/documents/ | unit | `pytest tests/test_documents.py::test_files_saved_locally -x` | ❌ Wave 0 |
| D-10 | Invalid PDF returns error, not crash | unit | `pytest tests/test_documents.py::test_upload_invalid_file -x` | ❌ Wave 0 |
| D-11 | GET /documents loads existing extractions | unit | `pytest tests/test_documents.py::test_list_documents -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && ../.venv/bin/python -m pytest tests/test_documents.py -x`
- **Per wave merge:** `cd backend && ../.venv/bin/python -m pytest tests/ -x` (includes settings tests)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_documents.py` — covers DOC-01, DOC-02, DOC-09, DOC-10, D-10, D-11
- [ ] Test fixtures: sample PDF bytes (create minimal PDF with PyMuPDF in fixture), mock LLM responses
- [ ] `python-multipart` install: `cd backend && ../.venv/bin/pip install python-multipart`

## Sources

### Primary (HIGH confidence)
- PyMuPDF 1.27.2.2 — verified installed, API tested locally (`fitz.open()`, `page.get_text()`, `get_text("blocks")`, `get_text("dict")`)
- LiteLLM 1.83.4 — verified installed, `acompletion()` pattern from existing `llm.py`
- FastAPI 0.135.3 — verified installed, `UploadFile` import tested, router pattern from `settings.py`
- Existing codebase — `main.py`, `llm.py`, `settings.py` (router), `settings.py` (schemas), `App.tsx`, `AppLayout.tsx`, `SettingsPage.tsx`, `api.ts`
- `IRS_Docs/form_1301_schema.json` — Form 106 → Form 1301 field mappings

### Secondary (MEDIUM confidence)
- LiteLLM JSON mode documentation — `response_format={"type": "json_object"}` works cross-provider

### Tertiary (LOW confidence)
- Form 106 layout variation across employers — assumed manageable by LLM based on structured government form, but untested

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified installed with exact versions
- Architecture: HIGH — follows established Phase 1 patterns exactly
- Pitfalls: HIGH — python-multipart gap verified, Content-Type pitfall is well-documented
- Form 106 schema: HIGH — field mappings from authoritative schema JSON
- LLM extraction quality: MEDIUM — prompt design is solid but untested against real Form 106 PDFs

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (stable stack, no fast-moving dependencies)
