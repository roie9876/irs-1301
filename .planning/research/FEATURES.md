# Feature Landscape

**Domain:** Israeli income tax filing assistant (Form 1301, salaried workers)
**Researched:** 2026-04-10
**Overall confidence:** MEDIUM-HIGH

Research based on: TurboTax/H&R Block feature analysis, NerdWallet 2026 reviews, Israeli tax authority guidelines (IRS_Docs 2022–2025), PROJECT.md/REQUIREMENTS.md context. Israeli tax software market is thin — no TurboTax equivalent exists, so feature baseline is derived from US/international patterns adapted to Israeli tax structure.

---

## Table Stakes

Features users expect. Missing = product feels incomplete or untrustworthy.

| # | Feature | Why Expected | Complexity | Notes |
|---|---------|-------------|------------|-------|
| T1 | **Step-by-step wizard following form structure** | TurboTax's #1 praised feature is "never dropping the curtain between you and the IRS forms." Users expect guided flow, not a blank form. | High | Must map to 1301 parts (א'–ל'), show only relevant sections. Hide irrelevant parts based on T3 questionnaire. |
| T2 | **Hebrew RTL interface** | Target audience is Hebrew-speaking Israelis. Non-negotiable. | Medium | Streamlit has RTL support but needs custom CSS. All labels, explanations, field names in Hebrew. |
| T3 | **Preliminary questionnaire** | "Are you married? Kids? Rental income? Capital gains?" TurboTax starts with this to determine relevant sections. Users expect to skip what doesn't apply. | Low | Determines which 1301 parts to show. Key questions: married/single, children count+ages, employer count, rental property, investments, donations. |
| T4 | **Document upload & extraction — Form 106** | 106 is the primary data source for salaried workers (equivalent to US W-2). Contains gross income, tax withheld, pension contributions, training fund. Without this, user has to type everything manually. | High | 106 is digital PDF (text extractable via PyMuPDF/pdfplumber). Must handle multiple 106s (multiple employers). Must map extracted fields to correct 1301 fields. |
| T5 | **Document upload & extraction — Form 867** | Capital gains from banks/brokers. Users with stock portfolios need this. Forms come from every bank/brokerage separately. | High | Similar PDF extraction. Must aggregate across multiple 867 forms. Fields: realized gains, losses, dividends, tax withheld. |
| T6 | **Extracted data review & manual correction** | TurboTax shows extracted values with edit capability. Users don't trust blind extraction — they need to verify and fix. | Medium | Show extracted data in editable table. Highlight low-confidence extractions. Allow adding missing values. |
| T7 | **Contextual field explanations** | TurboTax's biggest UX advantage: "expandable sidebar information, embedded links, tips, explainers." Every field needs a "what is this?" | Medium | Pull from RAG (official guidelines). Explain in plain Hebrew what each field means, who fills it, and what value to enter. |
| T8 | **Save and resume progress** | Tax filing takes hours/days. Users can't complete in one session. TurboTax explicitly supports pausing and returning. | Medium | Persist state to local JSON/SQLite. Must save: completed sections, extracted data, user inputs, current position. |
| T9 | **Tax year selection** | Guidelines change every year. User may be filing for 2024 or catching up on 2022. | Low | Drives which RAG index to use and which credit/deduction rules apply. MVP: 2022–2025. |
| T10 | **LLM provider selection** | Project constraint: user chooses their own LLM provider (OpenAI/Azure/Gemini/Claude) with personal API key. | Medium | UI for provider selection, model picker, API key input, key validation. Persist in local config. |
| T11 | **Credit points calculator (נקודות זיכוי)** | Every Israeli taxpayer has credit points. Miscounting = wrong tax. TurboTax equivalent: standard deduction wizard with situation-specific adjustments. | Medium | Personal points (2.25 for resident), children (varies by age and gender of parent), new immigrant, settlement, disability, academic degree. Rules change per tax year. |
| T12 | **Data validation** | Flag incomplete or inconsistent data before user finishes. "You uploaded 106 showing pension contributions but didn't fill the pension section." | Medium | Cross-reference extracted 106/867 data with filled form fields. Warn on missing required fields. |

---

## Differentiators

Features that set the product apart. Not expected because **no comparable Israeli product exists**, but these create the core value.

| # | Feature | Value Proposition | Complexity | Notes |
|---|---------|-------------------|------------|-------|
| D1 | **RAG-based guidance from official IRS guidelines** | The killer feature. Instead of generic AI answers, responses are grounded in the actual IRS guidance document for that specific tax year. "Field 042: according to the 2024 guidelines, you should enter..." | High | Requires per-year vector index (ChromaDB/FAISS). Must chunk guidelines intelligently — by section/field reference. Must cite which guideline section the answer came from. |
| D2 | **Contextual AI chat** | Ask any question while filling the form. Chat knows: current tax year, uploaded documents, current field. "Is rental income below ₪5,471/month exempt?" → answers based on the relevant year's guidelines. | High | Combines RAG retrieval + user context (year, documents, current form section). Must avoid hallucination — prefer "I don't have specific guidance on this" over making up rules. |
| D3 | **Spouse joint filing wizard (דוח משותף)** | In Israel, married couples file ONE form with separate columns for each spouse. This is a major pain point — each spouse has their own 106, 867, income sources, but it all goes into one form. No Israeli software handles this well. | High | UI must support uploading documents for both spouses separately. Map each spouse's data to their column. Handle "higher-earning spouse" designation. Calculate combined credit points. |
| D4 | **RSU/stock compensation extraction** | Hi-tech workers have E*Trade/Schwab/Morgan Stanley RSU reports. These are NOT in Form 867 — they're separate. Accountants charge specifically for this complexity. Must extract: vesting dates, sale dates, exercise price, fair market value, ordinary income portion vs capital gains. | Very High | PDF format varies by broker. May need Vision API for some formats. Must calculate Israeli tax treatment: ordinary income at vesting (Section 102), capital gains at sale. Currency conversion (USD→ILS) at historical rates. |
| D5 | **Multi-year guideline support** | Each tax year has different rules (brackets, credit point values, thresholds). Most people file 1-3 years late. The system must apply the RIGHT rules per year, not mix them up. | Medium | Separate RAG index per year. Year-specific constants (tax brackets, credit point value, rental exemption ceiling). Version-controlled. |
| D6 | **Rental income track advisor** | Israel has 3 tax tracks for rental income: full exemption (below ceiling), flat 10%, or marginal rate. Choosing wrong track = overpaying. Tool should recommend optimal track based on user's total income and rental amount. | Medium | Calculate tax under each track, recommend lowest. Must know yearly exemption ceiling. Show calculation breakdown. |
| D7 | **Smart field suggestions** | After extracting documents, pre-fill form fields with suggested values. "Based on your 106, field 042 should be ₪185,000." User confirms or edits. | Medium | Map 106 fields → 1301 fields. Must handle multiple 106s (sum employer incomes). Show source document for each suggestion. |
| D8 | **Prior year comparison** | Upload previous year's 1301 (from accountant). System shows deltas: "Your gross income increased by 12% vs last year." Catches obvious errors. | Medium | Parse submitted 1301 PDF. Compare field-by-field. Highlight significant changes that might indicate errors or missed deductions. |
| D9 | **Section-specific donation calculator (סעיף 46)** | Donations above ₪190 to approved charities give 35% tax credit. Must aggregate across multiple donation receipts and cap at the yearly maximum. | Low | Extract donation receipts. Sum and apply threshold/cap rules. List which charities qualify. |
| D10 | **Privacy-first local architecture** | Everything runs locally. Documents never leave the machine. Only LLM API calls go to the cloud (and those don't contain full documents — only extracted/chunked text). | Low | This is an architectural constraint, not a feature to build. But it's a differentiator vs cloud-based tax tools. Mention prominently in UX. |
| D11 | **Expected refund/liability estimator** | TurboTax's refund tracker is praised: "not only tallies up your estimated bill or refund, but also provides a detailed breakdown." Show running estimate as user fills sections. | High | Requires implementing Israeli tax calculation: brackets, credits, withholdings. Explicitly mark as ESTIMATE — not official. Complex because of different rates for different income types (capital gains, dividends, salary). |
| D12 | **Multi-provider LLM flexibility** | User uses their own API key — no subscription to us. Works with OpenAI, Anthropic, Google, Azure. If one provider is expensive or slow, user switches. | Medium | Abstraction layer over multiple SDKs. Some providers may not support Vision (needed for scanned docs). Must handle capability differences gracefully. |

---

## Anti-Features

Features to explicitly NOT build. Important for scope control and legal safety.

| # | Anti-Feature | Why Avoid | What to Do Instead |
|---|-------------|-----------|-------------------|
| A1 | **Final tax calculation / official liability** | Legal minefield. Only the Tax Authority determines final tax liability. If the tool says "you owe ₪5,000" and it's wrong, user has legal exposure. Israeli law is specific about who can provide tax advice (licensed CPA/tax advisor). | Provide "estimated" calculations clearly labeled as unofficial. Show formula and inputs so user can verify. Add disclaimer on every screen. |
| A2 | **Direct submission to IRS website** | The IRS website (shaam.gov.il) requires personal login with digital certificate or biometric ID. Automating this is fragile (website changes), risky (credential handling), and legally questionable. | Show a printable summary. User manually enters values on the IRS website. Consider a side-by-side view showing "enter this value in field X." |
| A3 | **Licensed tax advice** | Tool is NOT a licensed tax advisor. Cannot recommend "you should do X" when it involves subjective tax strategy. In Israel, providing tax advice without a license is legally restricted. | Frame everything as "according to the guidelines, field X is for..." rather than "you should claim..." Add clear disclaimers. Show what the guidelines say, let user decide. |
| A4 | **Cloud storage of personal documents** | Privacy constraint. Storing someone's 106 (shows exact salary) or 867 (shows investment portfolio) in the cloud is a liability and trust-breaker. | Everything local. gitignore all personal data. Clear documentation on where data is stored. |
| A5 | **Auto-connection to banks/employers** | Israeli banks don't have public APIs for tax document retrieval. Scraping bank websites is fragile, against ToS, and a security risk (handling bank credentials). | Manual upload. Provide instructions on where to download each document from the bank/employer portal. |
| A6 | **Self-employed support (נספח א')** | Self-employed tax reporting (Schedule A / נספח א') is vastly more complex: business expenses, depreciation, VAT reporting, advance tax payments. Different target audience, different form sections. Scope creep killer. | V1 is salaried only. Mark as future milestone. The architecture should not preclude adding it later, but don't build for it now. |
| A7 | **Filled PDF form export** | Generating a filled 1301 PDF requires exact pixel-level form mapping. Forms change between years. High effort, fragile, limited value since user still needs to submit online. | Export a structured summary (field number → value) that user can reference while filling the online form. PDF export can be a future enhancement. |
| A8 | **Mobile app** | Complexity of document upload + RTL form filling on mobile is poor UX. Form 1301 is inherently a desktop task (multiple documents, long form). | Desktop-first web app (Streamlit). Responsive enough to view on tablet, but not optimized for phone. |
| A9 | **Automated currency conversion from live rates** | RSU calculations need USD→ILS conversion at specific historical dates. Using live API adds dependency, cost, and potential errors for historical dates. | Use the official Bank of Israel published representative rates. User can verify/override. Store a static table of historical rates for common dates, or fetch from the Bank of Israel public data. |
| A10 | **Multi-user / family account management** | Adds authentication, data separation, and complexity. This is a personal tool, not a SaaS platform. | Single-user local app. Each family member can run their own instance. Spouse data is handled within the joint filing flow, not as separate accounts. |

---

## Feature Dependencies

```
T3 (Questionnaire) ─→ T1 (Wizard) — wizard structure depends on questionnaire answers
T4 (106 Upload) ──→ D7 (Smart Suggestions) — suggestions require extracted data
T5 (867 Upload) ──→ D7 (Smart Suggestions)
T9 (Year Selection) ─→ D1 (RAG) — RAG index is per-year
T9 (Year Selection) ─→ D5 (Multi-year) — rules/constants are per-year
T9 (Year Selection) ─→ T11 (Credit Points) — credit point values change per year
T10 (LLM Provider) ─→ D1 (RAG) — embeddings and chat use the LLM
T10 (LLM Provider) ─→ D2 (Contextual Chat)
T10 (LLM Provider) ─→ T4 (106 Upload) — Vision for scanned docs needs LLM
D1 (RAG) ───────→ T7 (Field Explanations) — explanations come from RAG
D1 (RAG) ───────→ D2 (Contextual Chat) — chat uses RAG for grounding
T4 (106 Upload) ──→ D3 (Joint Filing) — joint filing needs both spouses' 106s
D7 (Smart Suggestions) → D11 (Estimator) — estimator needs field values
T11 (Credit Points) ──→ D11 (Estimator) — estimator needs credit calculation
D4 (RSU Extraction) ──→ D7 (Smart Suggestions) — RSU data feeds into form fields
```

**Critical path for MVP:**
```
T10 (LLM) → T9 (Year) → D1 (RAG) → T7 (Explanations)
                                    → D2 (Chat)
T10 (LLM) → T4 (106) → T6 (Review) → D7 (Suggestions)
T3 (Questionnaire) → T1 (Wizard) → T8 (Save/Resume)
```

---

## MVP Recommendation

### Phase 1 — Core (must launch with):
1. **T10** LLM provider selection + API key
2. **T9** Tax year selection
3. **D1** RAG index of official guidelines (at least 2024 + 2025)
4. **T3** Preliminary questionnaire
5. **T1** Step-by-step wizard (basic structure, even if not all sections)
6. **T4** Form 106 upload + extraction
7. **T6** Extracted data review + manual correction
8. **T7** Contextual field explanations (via RAG)
9. **D2** Basic contextual chat
10. **T2** Hebrew RTL interface
11. **T8** Save and resume

### Phase 2 — Completeness:
1. **T5** Form 867 upload + extraction
2. **T11** Credit points calculator
3. **D7** Smart field suggestions
4. **D3** Spouse joint filing
5. **T12** Data validation
6. **D6** Rental income track advisor
7. **D9** Donation calculator

### Phase 3 — Differentiation:
1. **D4** RSU extraction (E*Trade/Schwab)
2. **D11** Refund/liability estimator
3. **D8** Prior year comparison
4. **D5** Multi-year support (2022-2023 indexes)
5. **D12** Additional LLM provider support (if not all in Phase 1)

### Defer indefinitely:
- A6 (Self-employed) — different product essentially
- A7 (PDF export) — nice-to-have, not core value
- A8 (Mobile) — poor UX for this use case

---

## Israeli Market Context

### No Direct Competitor
There is no Israeli equivalent of TurboTax. The market is dominated by:
- **CPAs/tax advisors** (רואי חשבון / יועצי מס) — charge ₪1,000–5,000 per filing
- **The IRS website itself** — bare-bones form filling, no guidance, no extraction
- **Generic tax calculators** — calculate rough liability but don't help fill the form
- **Facebook groups** — where people ask questions and get crowdsourced (unreliable) answers

This creates a unique opportunity: even basic guided filing with document extraction would be transformative for the Hebrew-speaking salaried worker market.

### Why Salaried Workers Specifically
- ~75% of Israeli workforce is salaried
- Most salaried workers who file do so for **tax refunds** (they overpaid via withholding)
- The form is intimidating but the actual complexity for salaried workers is manageable
- Self-employed add enormous complexity (business expenses, VAT, advance payments)

### The Joint Filing Challenge
Israeli joint filing is unlike US "married filing jointly." In Israel:
- One form, two columns (נישום = taxpayer, בן/בת זוג = spouse)
- Each spouse reports their own income separately
- The "higher earner" is designated as the primary taxpayer
- Credit points combine but income doesn't — it's a PARALLEL filing in one form
- This is deeply confusing and is the #1 reason couples use accountants

### Document Landscape
| Document | Source | Format | Availability |
|----------|--------|--------|--------------|
| טופס 106 | Employer | PDF (digital, text-extractable) | March of following year |
| טופס 867 | Bank/Broker | PDF | March–April of following year |
| RSU Report | E*Trade/Schwab/Morgan Stanley | PDF (varies widely) | January of following year |
| Donation receipts | Charity | PDF or scanned paper | Year-round |
| Pension/insurance certificates | Insurance company | PDF | March of following year |
| Previous 1301 | IRS website download or CPA | PDF | Anytime |

---

## Sources

- NerdWallet TurboTax Review 2026 (April 2026) — MEDIUM confidence on feature patterns
- TurboTax feature pages via NerdWallet analysis — MEDIUM confidence
- Wikipedia TurboTax article — HIGH confidence on historical patterns
- Israeli Tax Authority guidelines (IRS_Docs 2022-2025) — HIGH confidence on form structure
- PROJECT.md and REQUIREMENTS.md — HIGH confidence on user context and constraints
- Israeli tax filing process knowledge (training data) — MEDIUM confidence, verified against project context
