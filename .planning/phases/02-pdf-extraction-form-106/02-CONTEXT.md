# Phase 02 Context: PDF Extraction — Form 106

**Created:** 2026-04-10
**Mode:** auto (all decisions auto-selected)

## Phase Goal (from ROADMAP)

User uploads Form 106 PDFs and gets structured financial data extracted for review and correction.

## Requirements

- **DOC-01**: Upload Form 106 (digital PDF) → extract: gross salary, tax withheld, pension/provident fund contributions, work days
- **DOC-02**: Upload multiple Form 106s (multiple employers) → aggregate data
- **DOC-09**: User reviews extracted data and can manually correct any field
- **DOC-10**: All documents and data stored in a local folder only

## Prior Decisions (from Phase 1)

- Monorepo: `/frontend` + `/backend` siblings
- Backend: FastAPI + Python 3.14, venv at `.venv/`
- Frontend: React + Vite + shadcn/ui with Hebrew RTL
- API proxy: frontend `/api/*` → backend port 8000
- Local storage: all personal data in gitignored local folders
- LLM configured via Settings page (Phase 1 complete)

## Canonical References

- `IRS_Docs/form_1301_schema.json` — Form 106 field mappings to Form 1301 (section `key_source_documents.form_106`)
- `backend/app/services/llm.py` — LLM service (test_connection, acompletion via LiteLLM)
- `backend/app/main.py` — FastAPI app (add new router here)
- `frontend/src/App.tsx` — Router (add new route here)
- `frontend/src/lib/api.ts` — API utility for backend calls

<decisions>

### D-01: PDF Extraction Method
**Decision:** Use PyMuPDF (fitz) for text extraction from digital/text-based PDFs. Form 106 is a structured government form — it's always digital (not scanned). Extract text by page/area, then parse with regex patterns to identify fields.
**Rationale:** [auto] PyMuPDF is already installed in the venv (used for IRS doc conversion). No need for OCR — Form 106 from employers is always a digital PDF. Regex parsing of structured government forms is reliable and fast.

### D-02: Extraction Strategy — Regex vs LLM
**Decision:** Two-phase approach: (1) PyMuPDF extracts raw text, (2) LLM structures the data. Send the raw text to the configured LLM with a prompt that specifies the expected fields and output format (JSON). This handles variations in Form 106 layouts across employers.
**Rationale:** [auto] Pure regex is fragile across different employer payroll systems. LLM handles layout variation well. The user already has an LLM configured (Phase 1). Cost per extraction is negligible (small text input).

### D-03: File Upload UX
**Decision:** Drag-and-drop zone with a file picker fallback. Multiple files allowed (for multiple employers per DOC-02). Files show as cards with filename, upload status, and extraction status.
**Rationale:** [auto] Standard modern upload UX. shadcn/ui doesn't have a built-in upload component so we'll build a simple one with drop zone + input[type=file].

### D-04: Document Storage Location
**Decision:** Store uploaded PDFs in `user_data/documents/` directory at project root. This directory is gitignored. Extracted data saved as JSON alongside the PDF (`filename.106.json`).
**Rationale:** [auto] Per DOC-10, all data local only. Separating from `IRS_Docs/` (reference material) keeps user data organized. JSON sidecar files are simple and don't need a database.

### D-05: Review & Correction UI
**Decision:** After extraction, show a structured table/form with all extracted fields. Each field is editable. Fields grouped by category (income, tax withheld, pension, etc.). Hebrew labels with the Form 106 field numbers shown. Color-coded confidence indicators (green = high confidence, yellow = needs review).
**Rationale:** [auto] Per DOC-09, user must be able to review and correct. Table format matches the source document structure. Confidence indicators help users focus review on uncertain extractions.

### D-06: Multi-Employer Aggregation
**Decision:** Each uploaded Form 106 gets its own extraction card. A summary section at the bottom shows aggregated totals across all employers. Individual values are editable; totals auto-recalculate.
**Rationale:** [auto] Per DOC-02, multiple employers need aggregation. Keeping individual extractions visible lets users verify per-employer data while seeing combined totals.

### D-07: Form 106 Field Schema
**Decision:** Extract these fields from Form 106 (matching the `key_source_documents.form_106` mapping in the schema):
- Employer name and ID (מספר מזהה מעסיק)
- Tax year (שנת מס)
- Gross salary (הכנסה ברוטו) → 1301 field 158/172
- Tax withheld (מס שנוכה במקור) → 1301 section 84
- Pension employer contribution (הפרשות מעסיק לפנסיה) → 1301 field 248/249
- Insured income (הכנסה מבוטחת) → 1301 field 244/245
- Convalescence pay (דמי הבראה) → 1301 field 011/012
- Education fund (קרן השתלמות) → 1301 field 218/219
- Work days (ימי עבודה)
- National Insurance (ביטוח לאומי שנוכה)
- Health Insurance (ביטוח בריאות שנוכה)
**Rationale:** [auto] These are the fields that map directly from Form 106 to Form 1301 per the schema. Covers all DOC-01 requirements.

### D-08: Navigation Integration
**Decision:** Add a "מסמכים" (Documents) link to the header navigation, next to "הגדרות". Route: `/documents`. This is the upload + review page.
**Rationale:** [auto] Consistent with Phase 1 navigation pattern. Simple flat navigation for now.

### D-09: Extraction Prompt Design
**Decision:** Use a structured system prompt that specifies the expected JSON schema for Form 106 fields. Include field names in Hebrew and English. Ask the LLM to return a confidence score (0-1) per field. If a field isn't found, return null rather than guessing.
**Rationale:** [auto] Structured output with confidence scores enables the review UI (D-05). Null for missing fields prevents hallucinated values.

### D-10: Error Handling — Invalid PDFs
**Decision:** If uploaded file isn't a PDF or text extraction fails, show an inline error on the file card: "הקובץ אינו PDF תקין" or "לא ניתן לחלץ טקסט מהקובץ". Don't crash the app.
**Rationale:** [auto] Graceful degradation. Users may accidentally upload wrong files.

### D-11: Persistence of Extracted Data
**Decision:** Save extracted + user-corrected data as JSON files in `user_data/documents/`. When the user returns to the documents page, load existing extractions from disk. No database needed.
**Rationale:** [auto] Consistent with Phase 1's file-based persistence (.env for settings). Simple for a local app.

</decisions>

<deferred>
- OCR for scanned/photographed Form 106 — out of scope, Phase 2 targets digital PDFs only
- Automatic detection of document type (106 vs 867 vs other) — Phase 6 scope
- Batch processing of multiple document types — Phase 6 scope
</deferred>
