# Roadmap: עוזר דוח שנתי 1301

## Overview

Transform Israeli salaried workers' tax filing from a ₪1,000–5,000 CPA expense into a self-service experience. The journey starts with a working Hebrew app shell and LLM connectivity, validates the highest-risk technical challenge (Hebrew PDF extraction), builds the RAG knowledge engine, then assembles the step-by-step wizard that brings extraction + RAG together. From there, contextual chat, additional document types, credit point calculations, and joint spouse filing extend the product incrementally — each phase delivering verifiable capability on a stable foundation.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Project Scaffolding & LLM Configuration** - Working Streamlit app with Hebrew RTL, LLM provider selection, API key management
- [ ] **Phase 2: PDF Extraction — Form 106** - Upload Form 106 PDFs, extract structured data, review and correct
- [ ] **Phase 3: RAG Engine & Guideline Indexing** - Index IRS guidance documents per tax year, retrieve field-level explanations
- [ ] **Phase 4: Form Wizard — Step-by-Step 1301** - Guided form filling with AI explanations, suggested values, and save/resume
- [ ] **Phase 5: Contextual Chat** - Free-form tax Q&A grounded in user documents and official guidelines
- [ ] **Phase 6: Additional Document Types** - Form 867, RSU reports, donations, insurance, medical, mortgage documents
- [ ] **Phase 7: Credit Points & Additional Income** - Credit point calculator, rental income tracks, interest, mortgage refund
- [ ] **Phase 8: Joint Filing (Spouse)** - Dual data entry and dual-column wizard for joint tax reports

## Phase Details

### Phase 1: Project Scaffolding & LLM Configuration
**Goal**: User can launch the app, select an LLM provider, and interact with a fully Hebrew RTL interface
**Depends on**: Nothing (first phase)
**Requirements**: LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, INF-01, INF-02, INF-03, INF-04
**Success Criteria** (what must be TRUE):
  1. User launches the app with `streamlit run` and sees a Hebrew RTL interface
  2. User selects an LLM provider and model, enters an API key, and gets confirmation that the connection works
  3. LLM settings persist between app restarts without re-entering credentials
  4. Personal documents and API keys are excluded from version control (.gitignore)
**Plans**: TBD
**UI hint**: yes

### Phase 2: PDF Extraction — Form 106
**Goal**: User uploads Form 106 PDFs and gets structured financial data extracted for review and correction
**Depends on**: Phase 1
**Requirements**: DOC-01, DOC-02, DOC-09, DOC-10
**Success Criteria** (what must be TRUE):
  1. User uploads a Form 106 PDF and sees extracted data: gross income, tax withheld, pension/provident fund contributions, work days
  2. User uploads multiple Form 106 files (multiple employers) and sees aggregated totals
  3. User can review each extracted value and manually correct any field
  4. All uploaded documents and extracted data are stored in a local folder only
**Plans**: TBD
**UI hint**: yes

### Phase 3: RAG Engine & Guideline Indexing
**Goal**: The system retrieves relevant official IRS guidance for any form field, scoped to the correct tax year
**Depends on**: Phase 1
**Requirements**: RAG-01, RAG-02, RAG-03, RAG-04
**Success Criteria** (what must be TRUE):
  1. IRS guidance documents (from IRS_Docs/) are indexed into per-year ChromaDB collections
  2. Querying a field name returns relevant guidance text from the correct tax year's document
  3. Guidance from different tax years never mixes — year isolation is verified
**Plans**: TBD

### Phase 4: Form Wizard — Step-by-Step 1301
**Goal**: User fills Form 1301 step by step with AI-powered explanations and suggested values from documents
**Depends on**: Phase 2, Phase 3
**Requirements**: WIZ-01, WIZ-02, WIZ-03, WIZ-04, WIZ-05, WIZ-07
**Success Criteria** (what must be TRUE):
  1. User selects a tax year and answers a preliminary questionnaire that filters the form to relevant sections only
  2. User progresses through form fields sequentially, with irrelevant sections hidden
  3. Each field shows an LLM-generated explanation (grounded in RAG) and a suggested value from extracted documents
  4. User can ask a free-form question about any field and get a contextual answer
  5. User can close the app and resume later from where they left off
**Plans**: TBD
**UI hint**: yes

### Phase 5: Contextual Chat
**Goal**: User asks free-form tax questions and gets answers grounded in their documents and official guidelines
**Depends on**: Phase 3, Phase 4
**Requirements**: CHAT-01, CHAT-02, CHAT-03
**Success Criteria** (what must be TRUE):
  1. User opens a chat interface and asks questions about income tax topics
  2. Chat answers reflect the user's context — tax year, uploaded documents, and current wizard position
  3. Answers cite the official IRS guidelines (RAG-grounded) rather than relying on general LLM knowledge
**Plans**: TBD
**UI hint**: yes

### Phase 6: Additional Document Types
**Goal**: User uploads and extracts data from all supported document types beyond Form 106
**Depends on**: Phase 2
**Requirements**: DOC-03, DOC-04, DOC-05, DOC-06, DOC-07, DOC-08
**Success Criteria** (what must be TRUE):
  1. User uploads Form 867 and sees extracted capital gains, losses, dividends, and withheld tax
  2. User uploads RSU annual report (E*Trade PDF) and sees extracted sale transactions and tax withholding
  3. User uploads donation receipts, insurance/pension certificates, medical receipts, and mortgage certificates — each with correctly extracted data
  4. Extracted data from all document types flows as suggested values into the wizard fields
**Plans**: TBD
**UI hint**: yes

### Phase 7: Credit Points & Additional Income
**Goal**: User calculates credit points and reports additional income types within the wizard
**Depends on**: Phase 4
**Requirements**: WIZ-06, INC-01, INC-02, INC-03
**Success Criteria** (what must be TRUE):
  1. Credit points are calculated based on user's personal details, children, locality, and disability status
  2. User can report rental income and select the appropriate tax track (exempt / 10% / marginal)
  3. User can report interest income from deposits and mortgage tax refund data in the relevant wizard sections
**Plans**: TBD
**UI hint**: yes

### Phase 8: Joint Filing (Spouse)
**Goal**: User files a joint report with spouse, with separate data entry and dual-column display
**Depends on**: Phase 4, Phase 6
**Requirements**: SPO-01, SPO-02, SPO-03
**Success Criteria** (what must be TRUE):
  1. User marks the report as joint and enters spouse personal details
  2. Each spouse has separate data entry for income, deductions, and document uploads
  3. The wizard displays side-by-side columns for taxpayer and spouse, matching the official 1301 form layout
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8
Note: Phases 2 and 3 depend only on Phase 1 and could run in sequence. Phases 5, 6, 7 are additive and can be reordered.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Scaffolding & LLM Configuration | 0/0 | Not started | - |
| 2. PDF Extraction — Form 106 | 0/0 | Not started | - |
| 3. RAG Engine & Guideline Indexing | 0/0 | Not started | - |
| 4. Form Wizard — Step-by-Step 1301 | 0/0 | Not started | - |
| 5. Contextual Chat | 0/0 | Not started | - |
| 6. Additional Document Types | 0/0 | Not started | - |
| 7. Credit Points & Additional Income | 0/0 | Not started | - |
| 8. Joint Filing (Spouse) | 0/0 | Not started | - |
