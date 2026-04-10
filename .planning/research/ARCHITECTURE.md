# Architecture Patterns

**Domain:** LLM-powered document processing + tax form wizard (Israeli 1301)
**Researched:** 2026-04-10

## Recommended Architecture

### Overview: Service-Layer Monolith (No HTTP API)

For a local-only Streamlit app, the standard pattern is a **service-layer monolith** — Streamlit calls Python service modules directly, no FastAPI/HTTP layer in between. FastAPI adds complexity (serialization, async handling, separate process) with zero benefit when everything runs in one process on one machine.

```
┌────────────────────────────────────────────────────────────────┐
│                    Streamlit Application                        │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌──────────┐ │
│  │  Wizard   │  │  Doc Upload  │  │   Chat    │  │ Settings │ │
│  │  Pages    │  │  & Review    │  │  Panel    │  │  Page    │ │
│  └─────┬────┘  └──────┬───────┘  └─────┬─────┘  └────┬─────┘ │
│        │              │                │              │        │
│  ┌─────┴──────────────┴────────────────┴──────────────┴─────┐ │
│  │                  Session State Manager                    │ │
│  │         (in-memory state + JSON persistence)              │ │
│  └─────┬──────────────┬────────────────┬──────────────┬─────┘ │
└────────┼──────────────┼────────────────┼──────────────┼───────┘
         │              │                │              │
┌────────┴──────────────┴────────────────┴──────────────┴───────┐
│                      Service Layer                             │
│  ┌────────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ Document       │ │ RAG Engine   │ │ Form Engine          │ │
│  │ Processor      │ │              │ │                      │ │
│  │ ┌────────────┐ │ │ ┌──────────┐ │ │ ┌──────────────────┐ │ │
│  │ │ PDF Text   │ │ │ │ Indexer  │ │ │ │ Schema Registry  │ │ │
│  │ │ Extractor  │ │ │ │          │ │ │ │ (1301 structure)  │ │ │
│  │ ├────────────┤ │ │ ├──────────┤ │ │ ├──────────────────┤ │ │
│  │ │ Vision     │ │ │ │ Retriever│ │ │ │ Field Resolver   │ │ │
│  │ │ Extractor  │ │ │ │          │ │ │ │ (wizard logic)   │ │ │
│  │ ├────────────┤ │ │ ├──────────┤ │ │ ├──────────────────┤ │ │
│  │ │ Structured │ │ │ │ Query    │ │ │ │ Value Suggester  │ │ │
│  │ │ Extractor  │ │ │ │ Composer │ │ │ │ (doc → field)    │ │ │
│  │ └────────────┘ │ │ └──────────┘ │ │ └──────────────────┘ │ │
│  └────────┬───────┘ └──────┬───────┘ └──────────┬───────────┘ │
│           │                │                     │             │
│  ┌────────┴────────────────┴─────────────────────┴───────────┐ │
│  │                    LLM Gateway                            │ │
│  │  ┌──────────┐ ┌────────────┐ ┌────────┐ ┌─────────────┐  │ │
│  │  │ OpenAI   │ │ Azure AOAI │ │ Gemini │ │ Claude      │  │ │
│  │  └──────────┘ └────────────┘ └────────┘ └─────────────┘  │ │
│  └───────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
         │                │                     │
    ┌────┴────┐    ┌──────┴──────┐    ┌────────┴────────┐
    │ Local   │    │ ChromaDB    │    │ LLM Provider    │
    │ Files   │    │ (per-year   │    │ APIs            │
    │ (JSON,  │    │  collections│    │ (cloud)         │
    │  PDFs)  │    │  on disk)   │    │                 │
    └─────────┘    └─────────────┘    └─────────────────┘
```

**Why no FastAPI:** The REQUIREMENTS.md diagram shows a FastAPI backend, but for a single-user local app this is unnecessary indirection. Streamlit can import and call service classes directly. If a REST API is ever needed (e.g., for a future web frontend), the service layer is already decoupled and can be wrapped in FastAPI trivially.

---

## Component Boundaries

### Component 1: Streamlit UI Layer

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Page routing, form rendering, file upload widgets, chat interface, RTL layout |
| **Communicates with** | Session State Manager (read/write state), Service Layer (via direct function calls) |
| **Does NOT** | Contain business logic, call LLM APIs directly, access ChromaDB directly |

**Pages:**
- `settings.py` — LLM provider selection, API key entry, model choice, tax year selection
- `documents.py` — Upload documents, view extracted data, manual corrections
- `wizard.py` — Step-by-step 1301 form filling with explanations
- `chat.py` — Context-aware free chat about tax questions

**RTL Pattern:** Streamlit supports RTL via CSS injection. Standard pattern:

```python
st.markdown("""<style>
    .stApp { direction: rtl; }
    .stTextInput input, .stTextArea textarea { direction: rtl; text-align: right; }
</style>""", unsafe_allow_html=True)
```

### Component 2: Session State Manager

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Manages wizard progress, user profile, extracted document data in memory; persists to disk |
| **Communicates with** | Streamlit (via `st.session_state`), local filesystem (JSON persistence) |
| **Does NOT** | Contain UI rendering, call external APIs |

**State Architecture:**

```
data/
├── config.json              # LLM provider settings (no API keys)
├── .env                     # API keys only (gitignored)
└── sessions/
    └── {tax_year}/
        ├── profile.json     # Taxpayer + spouse profile, credit points
        ├── documents/
        │   ├── raw/         # Original uploaded PDFs (gitignored)
        │   └── extracted/   # Structured JSON from each document
        ├── wizard_state.json   # Current step, completed steps, field values
        └── chat_history.json   # Conversation history for context
```

**Persistence Strategy:** Write to JSON on every significant state change (field completion, document processing). Load on startup. No database needed — the data volume is tiny (one taxpayer, ~10 documents, ~200 form fields).

### Component 3: Document Processor

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Extract structured data from uploaded PDFs/images, normalize into typed models |
| **Communicates with** | LLM Gateway (for Vision extraction + structured extraction prompts), local filesystem |
| **Does NOT** | Know about form 1301 fields, manage UI state |

**Extraction Pipeline (two-path):**

```
                    ┌─────────────────┐
                    │   Upload PDF    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Detect Type    │
                    │  (106? 867?     │
                    │   donation?     │
                    │   RSU report?)  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
     ┌────────▼────────┐          ┌────────▼────────┐
     │ Has selectable  │   NO     │   Vision API    │
     │ text?           ├──────────►   (send page    │
     │ (PyMuPDF check) │          │    as image)    │
     │                 │          └────────┬────────┘
     └────────┬────────┘                   │
              │ YES                        │
     ┌────────▼────────┐                   │
     │ Text Extraction │                   │
     │ (PyMuPDF /      │                   │
     │  pdfplumber)    │                   │
     └────────┬────────┘                   │
              │                            │
              └──────────┬─────────────────┘
                         │
                ┌────────▼────────┐
                │ LLM Structured  │
                │ Extraction      │
                │ (prompt per     │
                │  document type) │
                └────────┬────────┘
                         │
                ┌────────▼────────┐
                │ Typed Pydantic  │
                │ Model Output    │
                │ (Form106Data,   │
                │  Form867Data,   │
                │  etc.)          │
                └────────┬────────┘
                         │
                ┌────────▼────────┐
                │ User Review &   │
                │ Manual Fixes    │
                └─────────────────┘
```

**Key Design Decision: LLM for structured extraction, not regex.** Tax forms change layout between years. Hard-coded field positions break. The pattern is:

1. Extract raw text (cheap, fast, local)
2. Send text + extraction prompt to LLM (expensive, accurate)
3. LLM returns structured JSON matching a Pydantic schema
4. User reviews and can correct any field

**Document Type Detection:** Based on filename heuristics first (users name files "106.pdf"), then LLM classification as fallback. Don't over-engineer — a simple dropdown "What document is this?" is fine for MVP.

### Component 4: RAG Engine

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Index IRS guidance documents per tax year, retrieve relevant sections for form field explanations |
| **Communicates with** | ChromaDB (local disk), LLM Gateway (for embeddings + query rewriting) |
| **Does NOT** | Process user documents, manage form state |

**Per-Year Indexing Architecture:**

```
chroma_data/
├── irs_guidance_2022/    # Collection: guidance docs for tax year 2022
├── irs_guidance_2023/    # Collection: guidance docs for tax year 2023
├── irs_guidance_2024/    # Collection: guidance docs for tax year 2024
└── irs_guidance_2025/    # Collection: guidance docs for tax year 2025
```

**Why separate collections per year:** The IRS guidance documents change between years (tax brackets, credit point values, new deductions). Mixing years would contaminate answers. When the user selects tax year 2024, the RAG engine queries only the `irs_guidance_2024` collection.

**Chunking Strategy:**

```
PDF → Pages → Sections (by headings) → Chunks (1000 tokens, 200 overlap)
```

Each chunk gets metadata: `{ year: 2024, page: 15, section: "חלק ד - הכנסות מעסק" }`. This metadata enables filtering and attribution ("מקור: עמ' 15, חלק ד").

**Embedding Strategy Decision:** Use a single embedding model regardless of LLM provider. Switching embeddings when the user changes LLM provider would require re-indexing everything. Recommended: `text-embedding-3-small` from OpenAI (cheap, good for Hebrew), or a local model like `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` for offline use.

**Query Pipeline:**

```
User context (current field + profile) 
    → Query composer (build search query from field context)
    → ChromaDB similarity search (top-k=5, year-filtered)
    → Re-rank by relevance to specific field
    → Inject into LLM prompt as context
```

### Component 5: LLM Gateway

| Aspect | Detail |
|--------|--------|
| **Responsibility** | Unified interface to all LLM providers; handles chat, structured extraction, embeddings, vision |
| **Communicates with** | External LLM APIs (OpenAI, Azure OpenAI, Gemini, Claude) |
| **Does NOT** | Know about tax forms, form fields, document types |

**Recommended: LiteLLM as the abstraction layer.** It provides a unified `completion()` and `embedding()` interface across all four providers with the same OpenAI-compatible API shape. This eliminates writing four separate provider integrations.

**Why LiteLLM over custom abstraction:**
- Handles auth, retries, rate limiting per provider
- Unified streaming interface
- Model name mapping (e.g., `gemini/gemini-2.0-flash`, `claude-3-5-sonnet-20241022`)
- Vision/multimodal support across providers
- Active maintenance, wide adoption

**Interface Design:**

```python
class LLMGateway:
    """Wraps LiteLLM with project-specific defaults."""
    
    def chat(self, messages: list[dict], **kwargs) -> str:
        """General chat completion."""
    
    def chat_structured(self, messages: list[dict], response_model: type[BaseModel]) -> BaseModel:
        """Chat with structured output (JSON mode / tool use)."""
    
    def vision(self, image_bytes: bytes, prompt: str) -> str:
        """Send image to vision-capable model."""
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings (uses configured embedding model)."""
```

**Structured Output:** Use `instructor` library on top of LiteLLM for reliable structured extraction. `instructor` patches LiteLLM's completion to return Pydantic models, with retry logic for malformed responses. This is the standard pattern for LLM → structured data pipelines.

**Provider-Specific Considerations:**

| Provider | Chat Model | Vision | Embeddings | Notes |
|----------|-----------|--------|------------|-------|
| OpenAI | gpt-4o, gpt-4o-mini | gpt-4o | text-embedding-3-small | Best structured output support |
| Azure OpenAI | same models via deployment | same | same | Needs endpoint + deployment name |
| Gemini | gemini-2.0-flash, gemini-2.5-pro | gemini-2.0-flash | text-embedding-004 | Good Hebrew, cheap |
| Claude | claude-sonnet-4-20250514 | claude-sonnet-4-20250514 | No native embeddings | Need separate embedding model |

**Claude caveat:** Anthropic doesn't offer an embeddings API. If user chooses Claude as LLM provider, embeddings must still come from OpenAI or a local model. The architecture must decouple "chat provider" from "embedding provider."

### Component 6: Form Engine

| Aspect | Detail |
|--------|--------|
| **Responsibility** | 1301 form schema definition, field dependencies, conditional visibility, value suggestion, validation |
| **Communicates with** | RAG Engine (for field explanations), Document Processor (for suggested values), Session State |
| **Does NOT** | Render UI, call LLM directly (goes through RAG or LLM Gateway) |

**Form Schema Design:**

The 1301 form has ~30 sections (חלקים) with ~200 fields total. Not all sections apply to every taxpayer. The schema must encode:

1. **Field definitions** — type, label, section, validation rules
2. **Conditional logic** — which fields/sections are visible based on taxpayer profile
3. **Dependencies** — field X auto-fills from document Y
4. **Dual-column structure** — taxpayer (נישום) and spouse (בן/בת זוג) columns

```python
# Schema structure (Python dataclasses or Pydantic)

class FormField:
    id: str                    # e.g., "section_b_gross_income"
    section: str               # e.g., "ב" (part B)
    label_he: str              # Hebrew field name
    field_type: FieldType      # number, text, boolean, date, choice
    applies_to: AppliesTo      # taxpayer, spouse, both, household
    visible_when: str | None   # condition expression, e.g., "profile.is_employed"
    source_doc: str | None     # which document type provides this value
    source_field: str | None   # which field in the extracted document
    validation: dict | None    # min/max, required, regex
    irs_field_number: str      # reference to official form field number

class FormSection:
    id: str                    # e.g., "section_b"
    name_he: str               # e.g., "חלק ב' - פרטים על הכנסות"
    visible_when: str | None   # condition for entire section
    fields: list[FormField]
    
class Form1301Schema:
    tax_year: int
    sections: list[FormSection]
```

**Conditional Logic Engine:** The wizard's "screening questionnaire" (WIZ-2) sets a taxpayer profile that drives which sections appear:

```
Profile flags:
  is_employed → Show section ב (employment income)
  is_self_employed → Show נספח א (NOT in MVP)
  is_married → Show spouse column in all dual-column sections
  has_children → Show credit points for children
  has_rental_income → Show section ד (rental income subsection)
  has_capital_gains → Show section ד (capital gains subsection)
  has_donations → Show section י (deductions)
  has_mortgage → Show mortgage interest deduction
```

**Value Suggestion Flow:**

```
Document extracted data (Form106Data.gross_income = 450,000)
    → Field resolver maps: Form106Data.gross_income → section_b_gross_income
    → Wizard shows: "הכנסה ברוטו: 450,000 ₪ (מטופס 106)" with edit option
```

### Component 7: Spouse / Joint Filing Data Model

Israeli tax joint filing has a specific structure that the data model must reflect:

```python
class TaxpayerProfile:
    """Primary taxpayer (נישום)."""
    id_number: str           # תעודת זהות
    first_name: str
    last_name: str
    date_of_birth: date
    is_employed: bool
    documents: list[DocumentRef]  # Their 106, 867, etc.
    
class SpouseProfile:
    """Spouse (בן/בת זוג) — optional."""
    id_number: str
    first_name: str
    last_name: str
    date_of_birth: date
    is_employed: bool
    documents: list[DocumentRef]  # Their own 106, 867, etc.

class HouseholdProfile:
    """Shared data for the household."""
    tax_year: int
    filing_status: FilingStatus  # single, married_joint
    taxpayer: TaxpayerProfile
    spouse: SpouseProfile | None
    children: list[Child]        # For credit point calculation
    address: Address
    settlement_code: str | None  # For settlement credit points
    
class Child:
    date_of_birth: date
    has_disability: bool
```

**Key Design Point:** In 1301, each spouse reports their own income in separate columns, but deductions (like donations, mortgage interest) may be split or attributed to one spouse. The form engine must track which person each data point belongs to, and the wizard must clearly separate "your data" from "spouse data" while showing them side by side as the form requires.

**Document Ownership:** Each uploaded document belongs to either the taxpayer or the spouse. The upload flow must ask "whose document is this?" when filing jointly.

---

## Data Flow

### Flow 1: Document Upload → Extraction → Field Population

```
User uploads PDF
    → Streamlit file_uploader receives bytes
    → Document Processor detects type (106/867/donation/etc.)
    → Document Processor chooses extraction path:
        Digital PDF → PyMuPDF text extraction → raw text
        Scanned PDF → LLM Vision API → raw text
    → LLM Structured Extraction: raw text + type-specific prompt → Pydantic model
    → Extracted data stored in sessions/{year}/documents/extracted/{doc_id}.json
    → User reviews extracted fields in Streamlit table, can edit
    → Form Engine maps extracted fields → 1301 form fields
    → Session State updated with suggested values
```

### Flow 2: Wizard Step → RAG Explanation → User Input

```
User navigates to wizard step (e.g., "חלק ב - הכנסות מעבודה")
    → Form Engine resolves visible fields for this section (based on profile)
    → For each field:
        1. RAG Engine queries guidance docs: "הסבר על שדה {field_label} בטופס 1301"
           ChromaDB returns relevant guidance chunks (year-filtered)
        2. LLM composes explanation from RAG context + user profile
        3. Form Engine checks if extracted doc data maps to this field → suggested value
        4. Streamlit renders: field label | explanation | suggested value | input
    → User fills/accepts value → Session State persists
```

### Flow 3: Free Chat with Context

```
User types question in chat panel
    → Chat module gathers context:
        - Current tax year
        - Current wizard section/field (if in wizard)
        - Uploaded document summaries
        - Recent chat history (last 10 messages)
    → RAG Engine retrieves relevant guidance passages
    → LLM receives: system prompt + context + RAG passages + user question
    → Response streamed to Streamlit chat display
    → Chat history appended to sessions/{year}/chat_history.json
```

---

## Patterns to Follow

### Pattern 1: Provider-Agnostic LLM Calls via LiteLLM

**What:** All LLM calls go through a single gateway class that wraps LiteLLM. No service should import provider SDKs directly.

**Why:** Changing provider = changing one config value, not rewriting call sites.

**Example:**

```python
from litellm import completion

class LLMGateway:
    def __init__(self, provider: str, model: str, api_key: str):
        self.model = f"{provider}/{model}"  # e.g., "openai/gpt-4o"
        os.environ[f"{provider.upper()}_API_KEY"] = api_key
    
    def chat(self, messages, **kwargs):
        return completion(model=self.model, messages=messages, **kwargs)
```

### Pattern 2: Pydantic Models as Extraction Contracts

**What:** Every document type has a Pydantic model defining exactly what fields are extracted. The LLM is instructed to return JSON matching this schema.

**Why:** Type safety, validation, clear contract between extraction and form engine.

**Example:**

```python
class Form106Data(BaseModel):
    employer_name: str
    employer_id: str
    gross_income: float
    tax_deducted: float
    pension_employee_contribution: float | None
    pension_employer_contribution: float | None
    training_fund_contribution: float | None
    work_days: int | None
```

### Pattern 3: Wizard State as Flat Dict with Schema Overlay

**What:** Wizard state is a flat `dict[str, Any]` mapping field IDs to values. The form schema provides structure, validation, and display logic on top.

**Why:** Simple serialization (JSON), easy diff/merge, schema can evolve independently of stored data.

```python
# Stored state (flat)
wizard_state = {
    "section_a_id_number": "123456789",
    "section_b_gross_income": 450000,
    "section_b_gross_income_spouse": 380000,
    "section_b_tax_deducted": 95000,
    ...
}

# Schema provides meaning
schema.get_field("section_b_gross_income").label_he  # "הכנסה ברוטו מעבודה"
schema.get_field("section_b_gross_income").source_doc  # "form_106"
```

### Pattern 4: Embedding Model Decoupled from Chat Model

**What:** The embedding model is configured separately from the chat model. Changing chat provider doesn't change embeddings.

**Why:** Re-indexing 4 years of guidance documents on every provider switch is expensive and slow. Embeddings must be stable.

**Implementation:** Store embedding model config separately. Default to `text-embedding-3-small` (OpenAI) since it works well for Hebrew and is cheap. Alternative: local `sentence-transformers` model for fully offline RAG.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: FastAPI Layer for Local-Only App

**What:** Adding a REST API between Streamlit and the service layer.
**Why bad:** Adds serialization overhead, async complexity, two processes to manage, error surface area — with zero users benefiting from a network API.
**Instead:** Import service classes directly from Streamlit pages. If API is needed later, wrap the existing service layer.

### Anti-Pattern 2: One ChromaDB Collection for All Years

**What:** Storing all guidance documents in a single collection with year as metadata filter.
**Why bad:** Metadata filtering in ChromaDB is post-retrieval — similarity search may return wrong-year chunks before filtering. Separate collections guarantee year isolation.
**Instead:** One collection per year: `irs_guidance_{year}`.

### Anti-Pattern 3: Hard-Coded Field Positions for PDF Extraction

**What:** Using coordinates or regex patterns to extract data from specific positions in PDF forms.
**Why bad:** Form layouts change between years, printers, and versions. Coordinate-based extraction is brittle.
**Instead:** Extract full text, then use LLM to find and structure the relevant data. The LLM understands the semantic meaning of fields regardless of layout.

### Anti-Pattern 4: Provider SDK Imports Scattered Across Codebase

**What:** Importing `openai`, `anthropic`, `google.generativeai` in document processor, RAG engine, chat module, etc.
**Why bad:** Adding/changing a provider requires touching every module.
**Instead:** Single LLM Gateway module. Everything else calls the gateway.

### Anti-Pattern 5: Storing API Keys in Config JSON

**What:** Writing API keys to the same JSON file as other settings.
**Why bad:** Config files may be less carefully gitignored. Keys mixed with non-sensitive data.
**Instead:** API keys in `.env` only, loaded via `python-dotenv`. Non-sensitive config (provider, model name, tax year) in `config.json`.

---

## Directory Structure

```
irs-1301/
├── app.py                      # Streamlit entry point
├── pages/
│   ├── 1_settings.py           # LLM provider + API key setup
│   ├── 2_documents.py          # Document upload + review
│   ├── 3_wizard.py             # 1301 form wizard
│   └── 4_chat.py               # Free chat
├── services/
│   ├── llm_gateway.py          # LiteLLM wrapper (multi-provider)
│   ├── document_processor.py   # PDF extraction pipeline
│   ├── rag_engine.py           # ChromaDB indexing + retrieval
│   ├── form_engine.py          # 1301 schema, field resolution, suggestions
│   └── state_manager.py        # Session persistence (JSON)
├── models/
│   ├── documents.py            # Pydantic models for extracted docs (106, 867, etc.)
│   ├── profile.py              # Taxpayer, Spouse, Household models
│   ├── form_schema.py          # 1301 form field/section definitions
│   └── wizard_state.py         # Wizard progress model
├── schemas/
│   └── form_1301.json          # 1301 form definition (sections, fields, conditions)
├── prompts/
│   ├── extraction/
│   │   ├── form_106.txt        # Prompt template for 106 extraction
│   │   ├── form_867.txt        # Prompt template for 867 extraction
│   │   ├── donation.txt        # Prompt template for donation receipt
│   │   └── rsu_report.txt      # Prompt template for RSU/E*Trade report
│   ├── wizard_explain.txt      # Prompt for field explanation (RAG-augmented)
│   └── chat_system.txt         # System prompt for free chat
├── IRS_Docs/                   # Official guidance PDFs (committed)
│   ├── Guides_IncomeTax_da-2022.pdf
│   ├── Guides_IncomeTax_da-2023.pdf
│   ├── Guides_IncomeTax_da-2024.pdf
│   └── Guides_IncomeTax_da-2025.pdf
├── data/                       # User data (gitignored)
│   ├── config.json
│   ├── chroma_db/              # Vector store on disk
│   └── sessions/
│       └── {tax_year}/
│           ├── profile.json
│           ├── documents/
│           │   ├── raw/        # Original PDFs
│           │   └── extracted/  # Structured JSON
│           ├── wizard_state.json
│           └── chat_history.json
├── .env                        # API keys (gitignored)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Scalability Considerations

| Concern | 1 User (MVP) | Multiple Users (Future) |
|---------|--------------|------------------------|
| State storage | JSON files | SQLite per user or server-side DB |
| ChromaDB | On-disk, single process | Still fine — guidance docs are read-only shared data |
| LLM calls | User's own API key | Same — each user brings their key |
| Document storage | Local filesystem | Would need user isolation |
| Concurrent access | N/A (local app) | Streamlit doesn't handle concurrent state well — would need rearchitecting |

**For MVP scope (single local user), JSON persistence and direct module calls are the right architecture. Do not over-engineer for multi-user.**

---

## Build Order (Dependencies)

The component dependency graph dictates build order:

```
Phase 1: Foundation
├── LLM Gateway (everything depends on this)
├── Data Models (Pydantic models for profile, documents, state)
└── Project skeleton (Streamlit app shell, directory structure)

Phase 2: Document Pipeline
├── PDF Text Extraction (needs: LLM Gateway)
├── Vision Extraction (needs: LLM Gateway)
├── Structured Extraction per doc type (needs: extraction + data models)
└── Document Upload UI (needs: extraction pipeline)

Phase 3: RAG Engine
├── Guidance Doc Indexer (needs: LLM Gateway for embeddings)
├── Per-Year Collection Setup (needs: indexer)
├── Retrieval + Query Composition (needs: collections indexed)
└── Embedding model decision (independent, but needed before indexing)

Phase 4: Form Engine + Wizard
├── 1301 Schema Definition (needs: understanding of form structure)
├── Field Resolver (needs: schema + extracted document data)
├── Wizard UI (needs: form engine + RAG for explanations)
└── Spouse/Joint Filing (needs: schema supports dual columns)

Phase 5: Chat + Polish
├── Context-Aware Chat (needs: RAG + session state + wizard context)
├── Full RTL Styling (can be incremental)
└── Progress Persistence (needs: state manager finalized)
```

**Critical path:** LLM Gateway → Document Extraction → RAG → Wizard.
The LLM Gateway must be built first because every other component depends on it.

**Parallelizable:** RAG indexing and document extraction prompts can be developed in parallel once the LLM Gateway exists.

---

## Sources

- LiteLLM documentation — multi-provider LLM abstraction (HIGH confidence, widely adopted)
- Instructor library — structured LLM output with Pydantic (HIGH confidence, standard pattern)
- ChromaDB documentation — local vector database (HIGH confidence)
- Streamlit multi-page app patterns (HIGH confidence)
- PyMuPDF / pdfplumber — PDF text extraction (HIGH confidence, mature libraries)
- Israeli 1301 form structure — based on project REQUIREMENTS.md and domain knowledge (MEDIUM confidence — form schema details need validation against actual form)
