# Phase 1: Project Scaffolding & LLM Configuration - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a launchable app shell: React+Vite frontend with full Hebrew RTL + FastAPI backend, with a Settings page where the user selects an LLM provider (OpenAI / Azure OpenAI / Gemini / Claude), enters an API key, picks a model, and gets confirmation the connection works. Settings persist between restarts. No document upload, no RAG, no wizard — just the app skeleton and LLM connectivity.

</domain>

<decisions>
## Implementation Decisions

### App Launch & Dev Workflow
- **D-01:** Single command (`make run` or npm script) starts both frontend (Vite dev server on port 5173) and backend (uvicorn on port 8000) concurrently.
- **D-02:** Frontend proxies `/api/*` requests to the backend — no CORS issues in dev.
- **D-03:** A `Makefile` at root orchestrates common tasks (run, install, test, lint).

### LLM Settings UI
- **D-04:** Dedicated Settings page (not a modal) — accessible from sidebar or header navigation.
- **D-05:** On first launch with no provider configured, the app redirects to Settings as the landing page.
- **D-06:** Provider selection: card-based picker with 4 cards (OpenAI, Azure OpenAI, Gemini, Claude) showing provider logo/icon. Selecting a card reveals model dropdown + API key input below.
- **D-07:** Model selection: dropdown populated with common models per provider (e.g., gpt-4o, gpt-4o-mini for OpenAI; claude-sonnet-4 for Claude). User can also type a custom model name.

### API Key Validation
- **D-08:** "Test Connection" button next to API key field. Triggers a minimal LiteLLM `completion()` call with a short Hebrew prompt.
- **D-09:** Inline status indicator: green checkmark + "חיבור תקין" on success, red X + error message on failure. No toast or modal — immediate inline feedback.
- **D-10:** Backend validates the key on save — stores only after successful test.

### Project Structure
- **D-11:** Monorepo layout: `/frontend` (React+Vite+TypeScript) and `/backend` (Python+FastAPI) as top-level siblings.
- **D-12:** Root `Makefile` with targets: `install`, `run`, `lint`, `test`.
- **D-13:** Backend dependencies: `requirements.txt` in `/backend` (no Poetry — keep it simple for a local app).
- **D-14:** Frontend package manager: npm with `package.json` in `/frontend`.
- **D-15:** shadcn/ui for component library — provides professional, accessible, RTL-compatible components.

### Persistence
- **D-16:** API keys and provider settings stored in `/backend/.env` file (dotenv). Loaded by FastAPI on startup.
- **D-17:** `.gitignore` already excludes `.env` files and personal data — verified in existing project setup.

### Agent's Discretion
- Color scheme, specific component styling — agent decides based on shadcn/ui defaults with RTL adjustments.
- Exact LiteLLM test prompt content — agent picks something short and Hebrew.
- Error message wording for connection failures — agent writes appropriate Hebrew text.
- FastAPI project structure (routers, schemas, etc.) — agent follows standard patterns.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Core value, constraints (privacy, local-only, Mac, Hebrew, multi-provider), key decisions
- `.planning/REQUIREMENTS.md` — LLM-01..05 and INF-01..04 are the Phase 1 requirements
- `.planning/ROADMAP.md` — Phase 1 goal and success criteria

### Domain Knowledge
- `IRS_Docs/form_1301_schema.json` — Form 1301 field schema (not needed for Phase 1 but establishes domain model)

### Research
- `.planning/research/STACK.md` — Tech stack recommendations (LiteLLM, PyMuPDF, ChromaDB decisions)
- `.planning/research/ARCHITECTURE.md` — System architecture patterns
- `.planning/research/PITFALLS.md` — 14 domain pitfalls including Hebrew RTL, tokenization costs

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project. No existing code, components, or patterns.

### Established Patterns
- Python virtual environment already exists at `.venv/` with PyMuPDF installed.
- `.gitignore` is already configured for privacy protection (personal docs, .env, uploads).
- IRS guidance documents converted to Markdown in `IRS_Docs/` (4 files, 2022-2025).

### Integration Points
- Phase 2 will add PDF upload routes to the FastAPI backend created here.
- Phase 3 will add RAG endpoints to the FastAPI backend created here.
- Phase 4 will add wizard pages to the React frontend created here.
- The Settings page created here will be reused in all subsequent phases (provider/model selection persists).

</code_context>

<specifics>
## Specific Ideas

- The test connection call should use a Hebrew prompt to also verify the model handles Hebrew well (e.g., "מה זה טופס 1301?").
- Provider cards should show recognizable logos — OpenAI green, Anthropic orange, Google blue, Azure Microsoft colors.
- The app name in the UI should be "עוזר דוח שנתי 1301" or a shorter variant.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-project-scaffolding-llm-configuration*
*Context gathered: 2026-04-10*
