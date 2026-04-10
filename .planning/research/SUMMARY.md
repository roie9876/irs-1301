# Project Research Summary

**Project:** עוזר דוח שנתי 1301 (Israeli Tax Report Assistant)
**Domain:** LLM-powered document processing + guided tax form filing
**Researched:** 2026-04-10
**Confidence:** HIGH

## Executive Summary

This is a local-only, LLM-powered tax filing assistant for Israeli salaried workers filing Form 1301. No comparable Israeli product exists — the market is dominated by expensive CPAs (₪1,000–5,000/filing) and a bare-bones government website. The recommended approach is a **service-layer monolith** built with Streamlit (Hebrew RTL via CSS injection), where Python service modules handle PDF extraction, RAG-based guidance, and multi-provider LLM calls via LiteLLM — all running in a single process with zero infrastructure requirements. This architecture eliminates FastAPI, Docker, and database overhead while keeping the service layer cleanly decoupled for future extraction.

The core value proposition is two-fold: (1) automated extraction of employer/bank documents (Form 106, Form 867) into structured data that pre-fills the 1301, and (2) RAG-grounded explanations from the official IRS guidance documents, scoped per tax year, so users understand what each field means. ChromaDB provides per-year-isolated vector collections locally. The stack is deliberately minimal — 7 pip-installable packages, no system dependencies, no Docker.

The primary risks are **Hebrew PDF text extraction** (pdfplumber has open RTL bugs — PyMuPDF is the safer primary extractor with Vision API fallback) and **Hebrew tokenization bloat** (3-5x token cost vs English, requiring larger character-based chunks). Both are mitigatable with the two-tier extraction strategy and semantic chunking. Joint filing (spouse) complexity is the biggest feature risk and should be deferred until single-filer wizard works end-to-end.

## Key Findings

### Recommended Stack

The stack is all-Python, pip-installable, with no system-level dependencies. See [STACK.md](STACK.md) for full rationale and alternatives considered.

**Core technologies:**
- **Python ≥3.12** — runtime, performance improvements
- **LiteLLM ~1.83** — unified `completion()` + `embedding()` across OpenAI/Azure/Gemini/Claude. Eliminates maintaining 4 separate SDK integrations
- **pdfplumber ~0.11** — table extraction from digital PDFs (Form 106/867). Best-in-class for structured tabular data
- **PyMuPDF ~1.27** — PDF page→image conversion for Vision API fallback on scanned docs. Also better RTL text handling than pdfplumber
- **ChromaDB ~1.5** — zero-config local vector store with per-collection metadata filtering. One collection per tax year
- **Streamlit ~1.56** — full UI framework with `st.chat_*`, `st.file_uploader`, `st.session_state`. Hebrew RTL via CSS injection
- **langchain-text-splitters ~1.1** — `RecursiveCharacterTextSplitter` for chunking guidance docs (standalone, no full LangChain)
- **python-dotenv ~1.2** — API key management via `.env` files

**Explicitly avoided:** LangChain (full), Tesseract OCR, Docker, FastAPI, cloud vector DBs, SQLite.

### Expected Features

See [FEATURES.md](FEATURES.md) for full feature landscape with dependencies.

**Must have (table stakes):**
- Step-by-step wizard following 1301 form structure (T1)
- Hebrew RTL interface (T2)
- Preliminary questionnaire to filter relevant sections (T3)
- Form 106 upload + extraction (T4) — primary data source for salaried workers
- Extracted data review + manual correction (T6)
- Contextual field explanations via RAG (T7)
- Save and resume progress (T8)
- Tax year selection (T9)
- LLM provider selection with personal API key (T10)
- Credit points calculator (T11)

**Should have (differentiators):**
- RAG-based guidance from official IRS guidelines, per year (D1) — the killer feature
- Contextual AI chat aware of user's documents and current field (D2)
- Smart field suggestions: document data → 1301 fields (D7)
- Form 867 upload for capital gains (T5)
- Rental income track advisor (D6)
- Donation calculator (D9)

**Defer to v2+:**
- RSU/stock compensation extraction (D4) — very high complexity, variable PDF formats
- Refund/liability estimator (D11) — requires full Israeli tax calculation engine
- Spouse joint filing wizard (D3) — complex parallel-column logic, build single-filer first
- Prior year comparison (D8)
- Self-employed support (A6) — different product essentially
- PDF form export (A7) — fragile, limited value

### Architecture Approach

A service-layer monolith where Streamlit imports Python service modules directly — no HTTP API, no separate processes. See [ARCHITECTURE.md](ARCHITECTURE.md) for diagrams and data flows.

**Major components:**
1. **Streamlit UI Layer** — pages for settings, documents, wizard, chat. RTL via CSS. No business logic
2. **Session State Manager** — in-memory state + JSON persistence per tax year. Flat dict with schema overlay
3. **Document Processor** — two-tier extraction: pdfplumber/PyMuPDF text → LLM structured extraction with Pydantic schemas. Vision API fallback for scanned docs
4. **RAG Engine** — per-year ChromaDB collections, semantic chunking, query composition with field context
5. **LLM Gateway** — LiteLLM wrapper providing `chat()`, `chat_structured()`, `vision()`, `embed()`. Single abstraction point for all providers
6. **Form Engine** — 1301 schema registry, field resolution, conditional visibility, value suggestion (doc→field mapping)

**Key architectural decisions:**
- Embedding model decoupled from chat model (no re-indexing on provider switch)
- Pydantic models as extraction contracts per document type
- One ChromaDB collection per tax year (never mix years)
- API keys in `.env` only, never in JSON config

### Critical Pitfalls

See [PITFALLS.md](PITFALLS.md) for all 14 pitfalls with prevention strategies.

1. **Hebrew PDF text reversal** — pdfplumber has open RTL bugs (#794, #1159, #1187). Use PyMuPDF as primary extractor with `sort=True`. Build a validation layer checking Unicode ranges. Test with real 106 forms from day one
2. **Hebrew tokenization bloat** — 3-5x more tokens than English. Chunk by semantic boundaries (section headers), use 1500-2000 character chunks, benchmark embedding cost early
3. **Tax year cross-contamination in RAG** — separate ChromaDB collections per year, include year in chunk metadata, lock year in session state. Wrong-year answers are worse than no answers
4. **No native Streamlit RTL** — CSS injection is the only path. Centralize in `rtl_utils.py`, pin Streamlit version, test all components individually
5. **Table extraction from PDFs** — flat text loses spatial relationships. Use `extract_table()` methods, map known form layouts per year, prefer Vision API for complex forms

## Implications for Roadmap

Based on combined research, the following phase structure respects dependency chains, addresses pitfalls early, and groups features by architectural component.

### Phase 1: Project Scaffolding & Configuration
**Rationale:** Foundation that everything else builds on. Establishes directory structure, `.gitignore`, `.env` handling, and LLM provider selection — the critical path root (T10)
**Delivers:** Working Streamlit app shell with RTL, provider selection UI, API key management, validated LLM connectivity
**Addresses:** T10 (LLM Provider), T2 (Hebrew RTL), T9 (Tax Year Selection)
**Avoids:** Pitfall #4 (RTL — establish CSS foundation first), Pitfall #12 (API key exposure — `.gitignore` from day one)

### Phase 2: PDF Extraction Pipeline
**Rationale:** Hebrew PDF extraction is the highest-risk technical challenge (Pitfalls #1, #8). Must validate with real 106 forms before building anything downstream. This is where the project either works or doesn't
**Delivers:** Document processor that extracts structured data from Form 106 PDFs into Pydantic models, with Vision API fallback
**Addresses:** T4 (106 Upload), T6 (Extracted Data Review)
**Avoids:** Pitfall #1 (Hebrew text reversal), Pitfall #8 (table extraction), Pitfall #5 (unstructured Vision responses)

### Phase 3: RAG Engine & Guideline Indexing
**Rationale:** RAG is the second pillar of value (after document extraction). Must validate embedding quality for Hebrew and establish per-year collection isolation before building explanations or chat
**Delivers:** Indexed IRS guidance documents (2024-2025 minimum) in year-isolated ChromaDB collections, retrieval pipeline returning relevant guidance chunks
**Addresses:** D1 (RAG Guidance), T9 dependency on RAG
**Avoids:** Pitfall #2 (tokenization bloat — semantic chunking), Pitfall #3 (year mixing — separate collections), Pitfall #9 (embedding lock-in — evaluate models first), Pitfall #14 (inconsistent PDF internals — test all files)

### Phase 4: Form Engine & Wizard
**Rationale:** With extraction and RAG working, the wizard can now show fields with explanations and suggested values. This is where the user experience comes together
**Delivers:** Step-by-step 1301 wizard with conditional sections, field explanations from RAG, preliminary questionnaire, save/resume
**Addresses:** T1 (Wizard), T3 (Questionnaire), T7 (Field Explanations), T8 (Save/Resume), D7 (Smart Suggestions)
**Avoids:** Pitfall #7 (joint filing — single filer only in this phase), Pitfall #11 (state corruption — persist to JSON)

### Phase 5: Contextual Chat
**Rationale:** Chat builds on RAG + wizard context. Relatively straightforward once RAG works — the main work is context assembly and anti-hallucination guardrails
**Delivers:** Context-aware chat panel that combines user profile, current wizard position, uploaded documents, and RAG retrieval
**Addresses:** D2 (Contextual Chat)
**Avoids:** Pitfall #10 (hallucination — source display, grounding prompt)

### Phase 6: Form 867 & Additional Documents
**Rationale:** Extends the document pipeline to capital gains (867), donation receipts, and pension certificates. Same extraction pattern as Phase 2, different Pydantic models
**Delivers:** Upload + extraction for 867, donations, pension/insurance docs. Aggregation across multiple 867s
**Addresses:** T5 (867 Upload), D9 (Donation Calculator), T12 (Data Validation)
**Avoids:** Pitfall #8 (table extraction — same mitigation as Phase 2)

### Phase 7: Credit Points & Tax Calculations
**Rationale:** Credit points calculator and tax estimation require the full form data model. Defer until wizard and document extraction are stable
**Delivers:** Credit points calculator with per-year rules, rental income track advisor, estimated refund/liability display
**Addresses:** T11 (Credit Points), D6 (Rental Track Advisor), D11 (Estimator)
**Avoids:** Anti-feature A1 (never present as authoritative — always mark as estimate)

### Phase 8: Joint Filing (Spouse)
**Rationale:** Deliberately last. Joint filing touches every component (document ownership, dual-column wizard, combined credit points). Building it on a stable single-filer foundation is dramatically safer than weaving it in from the start
**Delivers:** Spouse data model, dual-column wizard, per-spouse document upload, combined household calculations
**Addresses:** D3 (Joint Filing)
**Avoids:** Pitfall #7 (complexity explosion — built on proven single-filer wizard)

### Phase Ordering Rationale

- **Phases 1-3 are the foundation:** Configuration → PDF extraction → RAG. Each phase validates a critical risk before building on it. If Hebrew PDF extraction fails (Phase 2), we know before investing in the wizard
- **Phase 4 is the integration point:** Wizard brings extraction + RAG together into the user-facing product. This is where value becomes visible
- **Phases 5-7 are additive:** Each extends the product without changing the foundation. Can be parallelized or reordered
- **Phase 8 (joint filing) is isolated:** Intentionally deferred. It's the highest-complexity feature and touching it early would slow everything else

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (PDF Extraction):** Hebrew RTL extraction behavior needs empirical testing with real Form 106 PDFs. pdfplumber vs PyMuPDF quality comparison. Vision API structured output reliability for Hebrew forms
- **Phase 3 (RAG Indexing):** Embedding model evaluation for Hebrew retrieval quality. Chunking strategy validation on actual IRS guidance PDFs. Token cost benchmarking
- **Phase 4 (Form Engine):** 1301 form structure mapping — ~200 fields across ~30 sections with conditional logic. Needs careful schema design
- **Phase 7 (Tax Calculations):** Israeli tax bracket rules, credit point values, and rental exemption ceilings per year. Domain-specific constants that must be verified against official sources

Phases with standard patterns (skip research):
- **Phase 1 (Scaffolding):** Streamlit setup, RTL CSS, dotenv — well-documented patterns
- **Phase 5 (Chat):** Standard RAG + chat pattern, extensively documented
- **Phase 6 (Additional Docs):** Same extraction pipeline as Phase 2, different schemas

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies are well-established, documented, pip-installable. LiteLLM verified via docs. No speculative choices |
| Features | MEDIUM-HIGH | Feature landscape derived from US tax software (TurboTax) adapted to Israeli context. No direct Israeli competitor to benchmark against. Feature dependencies are clear |
| Architecture | HIGH | Service-layer monolith for local Streamlit apps is a proven pattern. Component boundaries are clean. Data flows are straightforward |
| Pitfalls | HIGH | Critical pitfalls (Hebrew RTL, tokenization) verified via open bug reports and tokenizer testing. Prevention strategies are concrete |

**Overall confidence:** HIGH

### Gaps to Address

- **Hebrew PDF extraction quality:** Must be validated empirically with real Form 106/867 PDFs in Phase 2. Research identifies the risk but only real testing resolves it
- **Embedding model quality for Hebrew:** Need to benchmark `text-embedding-3-small` vs `paraphrase-multilingual-MiniLM-L12-v2` on Hebrew tax content before committing
- **1301 form field mapping:** ~200 fields need to be enumerated and mapped. Research identifies the need for a schema but the actual field inventory is Phase 4 planning work
- **Anthropic embedding gap:** Claude users need a separate embedding provider (Anthropic has no embedding API). Architecture handles this but UX flow needs design
- **PyMuPDF AGPL license:** Acceptable for local personal use. If distribution model ever changes, swap to `pdf2image` (MIT) for image conversion

## Sources

### Primary (HIGH confidence)
- Israeli Tax Authority guidance documents (IRS_Docs 2022-2025) — form structure, field definitions, tax rules
- PROJECT.md and REQUIREMENTS.md — user context, constraints, prior accountant returns
- pdfplumber issue tracker (#794, #1159, #1187) — verified open RTL bugs
- LiteLLM documentation (docs.litellm.ai) — verified multi-provider interface
- PyMuPDF documentation — RTL text handling capabilities

### Secondary (MEDIUM confidence)
- NerdWallet TurboTax Review 2026 — feature patterns for guided tax filing
- Streamlit community forum — RTL support limitations confirmed
- tiktoken tokenizer — Hebrew token count verifiable empirically
- ChromaDB documentation — per-collection isolation behavior

### Tertiary (LOW confidence)
- Israeli tax software market analysis — based on training data, no direct market research. Claim of "no competitor" needs validation
- RSU report format variability — based on user context (E*Trade), not comprehensive broker survey

---
*Research completed: 2026-04-10*
*Ready for roadmap: yes*
