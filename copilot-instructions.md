<!-- GSD:project-start source:PROJECT.md -->
## Project

**עוזר דוח שנתי 1301**

אפליקציה מקומית שמנחה שכירים צעד-אחר-צעד במילוי טופס 1301 (דוח שנתי למס הכנסה בישראל).
משתמשת ב-LLM כדי לחלץ נתונים ממסמכים (106, 867, אקסלס, אישורים), להסביר כל שדה בטופס על בסיס מסמכי ההנחיות הרשמיים של אותה שנת מס, ולהציע ערכים למילוי.
מיועדת לכל אדם שמגיש דוח שנתי כשכיר — כולל דוח משותף עם בן/בת זוג.

**Core Value:** המשתמש מבין בדיוק מה למלא בכל שדה בטופס 1301, על בסיס המסמכים שלו וההנחיות הרשמיות — ומגיש את הדוח בעצמו בלי עזרה חיצונית.

### Constraints

- **פרטיות**: מסמכים אישיים לא עולים ל-GitHub (gitignore)
- **מקומי בלבד**: אין שרתים בענן — רק קריאות API ל-LLM
- **Mac (Apple Silicon)**: סביבת פיתוח מקומית
- **עברית**: ממשק בעברית, RTL מלא
- **רב-ספקי**: המשתמש בוחר את ספק ה-LLM שלו ומשתמש ב-API Key אישי
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Runtime
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | ≥3.12 | Runtime | Standard for ML/AI apps. 3.12+ has performance improvements and is the current stable line | HIGH |
### LLM Abstraction Layer
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| litellm | ~1.83 | Multi-provider LLM calls | Single `completion()` call for OpenAI, Azure OpenAI, Gemini, Claude + 100 more. Used by Stripe, Netflix, OpenAI Agents SDK. Supports chat, vision, embeddings — all via one interface. One codebase = all providers | HIGH |
### PDF Processing
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pdfplumber | ~0.11.9 | Text/table extraction from digital PDFs | Best-in-class table extraction. MIT-compatible license. Built on pdfminer.six. Ideal for Form 106 and Form 867 which are machine-generated PDFs with text layers and tabular data | HIGH |
| PyMuPDF | ~1.27 | PDF page → image conversion | Fastest PDF-to-image conversion for Vision API fallback on scanned documents. Pure pip install, no external deps on macOS. Used only for rendering pages as images — not for text extraction | HIGH |
### Vector Database (RAG)
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| chromadb | ~1.5 | Local vector store | Zero-config local persistence. Handles embedding + indexing + querying in 4 API calls. Apache 2.0 license. Supports per-collection metadata filtering (perfect for per-year-index isolation). No external infrastructure needed | HIGH |
- ChromaDB: Built-in persistence (`PersistentClient`), built-in embedding management, metadata filtering, simple Python API. One `pip install`, done.
- FAISS: Faster for million-scale datasets, but requires manual serialization, manual embedding orchestration, no metadata filtering. Overkill for ~4 tax guideline documents (hundreds of chunks, not millions).
### Embeddings
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| litellm (embedding) | ~1.83 | Generate embeddings via user's chosen provider | `litellm.embedding()` supports OpenAI, Azure, Gemini, Cohere embeddings with the same multi-provider abstraction. User's API key works for both chat and embedding | HIGH |
- OpenAI: `text-embedding-3-small` (good balance of quality/cost for Hebrew)
- Azure OpenAI: `text-embedding-3-small` (same model, deployed on Azure)
- Gemini: `text-embedding-004`
- Anthropic: Does not offer an embedding API → fall back to ChromaDB's default local model
### Text Splitting
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| langchain-text-splitters | ~1.1 | Chunk tax guideline PDFs for RAG indexing | `RecursiveCharacterTextSplitter` is battle-tested across thousands of RAG apps. Handles Hebrew text correctly (splits on paragraphs, sentences, then characters). Standalone package — does NOT require full LangChain | HIGH |
### UI Framework
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| streamlit | ~1.56 | Hebrew RTL wizard + chat UI | Fastest Python-to-web-app framework. Built-in `st.chat_message`/`st.chat_input` for conversational UI. Built-in `st.file_uploader` for document upload. `st.session_state` for wizard progress. `st.tabs`/`st.columns` for layout. Apache 2.0 | HIGH |
### Configuration & State
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| python-dotenv | ~1.2 | API key and provider config management | Standard .env file loading. Keys stored in `.env` locally, never committed to git. `load_dotenv()` sets them as environment variables — which is exactly what LiteLLM reads | HIGH |
| JSON files (stdlib) | — | Wizard progress persistence | One JSON file per tax year: `data/{year}/progress.json`. Human-readable, no additional dependency. Python's `json` module is sufficient | HIGH |
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| LLM abstraction | litellm | openai + anthropic + google-generativeai SDKs | 4 separate integrations, 4 response formats, 4 error handlers. LiteLLM unifies all |
| LLM abstraction | litellm | langchain (full framework) | Massive dependency tree, frequent breaking changes, abstraction overhead for a straightforward RAG app |
| Vector DB | chromadb | faiss-cpu | No built-in persistence, no metadata filtering, requires manual embedding orchestration |
| Vector DB | chromadb | qdrant | Overkill — requires separate server process. ChromaDB embeds in-process |
| PDF extraction | pdfplumber | PyMuPDF (for text) | PyMuPDF's AGPL license is more restrictive. pdfplumber's table extraction is superior for structured forms. PyMuPDF is used only for page-to-image conversion |
| PDF extraction | pdfplumber | pypdf | pypdf extracts text but doesn't handle tables well. Form 106 has tabular data |
| OCR | LLM Vision API | Tesseract | Lower accuracy for Hebrew, requires system-level install + language packs, can't understand document layout |
| UI | streamlit | gradio | Weaker multi-page support, less state management, designed for ML demos not wizard flows |
| UI | streamlit | nicegui | Smaller community, fewer examples for LLM apps, less battle-tested |
| UI | streamlit | FastAPI + React | Over-engineering. Two codebases, build step, CORS — unnecessary for a single-user local app |
| State persistence | JSON files | SQLite | Added complexity for a simple key-value data model. JSON is inspectable, editable, sufficient |
| State persistence | JSON files | TinyDB | Adds a dependency for something the stdlib handles fine |
| Text splitting | langchain-text-splitters | manual splitting | RecursiveCharacterTextSplitter handles edge cases (smart overlap, paragraph-aware splitting) that would take significant effort to reimplement |
| Config | python-dotenv | pydantic-settings | pydantic-settings is great for complex configs but overkill here. We need to load 3-4 env vars |
## What NOT to Use
| Technology | Why Avoid |
|------------|-----------|
| **LangChain (full framework)** | Pulls in dozens of dependencies. Its agent/chain abstractions add complexity without benefit for a straightforward RAG wizard. Use only `langchain-text-splitters` as a standalone utility |
| **Tesseract OCR** | Inferior to LLM Vision for Hebrew structured documents. Requires `brew install tesseract` + Hebrew language pack. The user is already paying for an LLM API — use its Vision capability |
| **Docker** | Requirement NF-6 explicitly states no Docker. Python + pip is sufficient |
| **FastAPI** | No need for a separate API server. Streamlit handles the entire stack for a single-user local app |
| **Pinecone / Weaviate / Qdrant** | Cloud-hosted or server-based vector DBs. This app is local-only. ChromaDB runs in-process |
| **sentence-transformers (direct)** | Only needed as a fallback inside ChromaDB. Don't install separately — ChromaDB bundles what it needs |
| **pdf2image** | Requires `brew install poppler` (system dependency). PyMuPDF does the same page-to-image conversion with zero system deps |
## Installation
# Create virtual environment
# Core dependencies
### Minimal `.env` file
# Choose ONE provider and set its key:
# OPENAI_API_KEY=sk-...
# AZURE_API_KEY=...
# AZURE_API_BASE=https://your-resource.openai.azure.com/
# GEMINI_API_KEY=...
# ANTHROPIC_API_KEY=sk-ant-...
# Provider selection (set at runtime via UI)
# LLM_PROVIDER=openai
# LLM_MODEL=gpt-4o
## Dependency Summary
| Package | PyPI Version (verified Apr 2026) | License | Size Impact |
|---------|----------------------------------|---------|-------------|
| litellm | 1.83.4 | MIT | Medium (many provider SDKs as optional deps) |
| chromadb | 1.5.7 | Apache 2.0 | Medium (includes hnswlib, numpy) |
| streamlit | 1.56.0 | Apache 2.0 | Large (includes tornado, protobuf, altair) |
| pdfplumber | 0.11.9 | MIT | Small (depends on pdfminer.six, Pillow) |
| PyMuPDF | 1.27.2 | AGPL-3.0 | Medium (includes MuPDF C library) |
| langchain-text-splitters | 1.1.1 | MIT | Small (depends on langchain-core) |
| python-dotenv | 1.2.2 | BSD-3 | Tiny (pure Python) |
## Sources
- LiteLLM: https://pypi.org/project/litellm/ (v1.83.4, Apr 7, 2026) — verified
- ChromaDB: https://pypi.org/project/chromadb/ (v1.5.7, Apr 8, 2026) — verified
- Streamlit: https://pypi.org/project/streamlit/ (v1.56.0, Apr 1, 2026) — verified
- pdfplumber: https://pypi.org/project/pdfplumber/ (v0.11.9, Jan 5, 2026) — verified
- PyMuPDF: https://pypi.org/project/PyMuPDF/ (v1.27.2.2, Mar 19, 2026) — verified
- langchain-text-splitters: https://pypi.org/project/langchain-text-splitters/ (v1.1.1, Feb 19, 2026) — verified
- python-dotenv: https://pypi.org/project/python-dotenv/ (v1.2.2, Mar 1, 2026) — verified
- LiteLLM docs (multi-provider): https://docs.litellm.ai/docs/providers
- ChromaDB docs: https://docs.trychroma.com/
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
