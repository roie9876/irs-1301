# Domain Pitfalls

**Domain:** LLM-powered Israeli tax report assistant (1301 form)
**Researched:** 2026-04-10

---

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Hebrew PDF Text Comes Out Reversed or Garbled

**What goes wrong:** pdfplumber and pdfminer (which pdfplumber wraps) extract Hebrew/RTL text with characters in reversed order. "שלום" becomes "םולש". Numbers embedded in Hebrew text also get reversed or reordered incorrectly. This is a **known open bug** — pdfplumber issues [#794](https://github.com/jsvine/pdfplumber/issues/794), [#1159](https://github.com/jsvine/pdfplumber/issues/1159), [#1187](https://github.com/jsvine/pdfplumber/pull/1187) (still open as of 2026).

**Why it happens:** PDF internally stores text in "visual order" (how glyphs appear on screen), not "logical order" (reading order). RTL text extraction requires reversing this, and most Python PDF libraries don't handle it correctly — especially for mixed Hebrew+numbers+English content.

**Consequences:** Every downstream component fails. Wrong field names extracted from forms. RAG embeddings encode gibberish. LLM receives meaningless text. The entire pipeline produces garbage.

**Prevention:**
1. **Use PyMuPDF (fitz) as primary extractor** — it uses MuPDF under the hood, which has better (though not perfect) RTL handling with `page.get_text("text", sort=True)`.
2. **Build a validation layer** — after extraction, check that extracted text contains valid Hebrew character sequences (Unicode ranges \u0590-\u05FF). Detect reversed text by checking if common Hebrew words appear backwards.
3. **Create a normalization function** — apply `python-bidi` (bidiutils) + `unicodedata` to fix logical ordering. Handle mixed number/Hebrew sequences explicitly.
4. **Test with real 106 forms immediately** — don't build the pipeline on English test PDFs and discover Hebrew breaks later. Use actual Israeli tax documents from day one.

**Warning signs:**
- Extracted text fails Hebrew spell-check or string matching
- Numbers appear at the wrong end of a line
- Regex patterns that match Hebrew field names stop working

**Detection:** Write a test that extracts known text from a real 106 PDF and asserts the output matches expected Hebrew strings.

**Phase relevance:** PDF Processing phase — must be validated before any downstream work begins.

**Confidence:** HIGH — verified via pdfplumber issue tracker, multiple open bugs as of 2025-2026.

---

### Pitfall 2: Hebrew Tokenization Bloats Token Count, Degrading RAG Quality

**What goes wrong:** Hebrew text uses 3-5x more tokens than equivalent English text with OpenAI's tokenizer (cl100k_base / o200k_base). A single Hebrew word like "הכנסה" (income) takes 3-5 tokens. This means: (a) chunking by token count produces tiny semantic chunks, (b) embedding cost is 3-5x higher, (c) LLM context fills up 3-5x faster, (d) retrieval quality drops because chunks are too small to carry meaning.

**Why it happens:** BPE tokenizers (tiktoken) are trained primarily on English text. Hebrew characters are underrepresented in the training data, so the tokenizer doesn't learn common Hebrew word fragments as single tokens.

**Consequences:** RAG retrieval returns fragments that lack context. LLM explanations get truncated. Costs multiply. Users with cheaper API plans hit limits quickly.

**Prevention:**
1. **Chunk by semantic boundaries, not token count** — use paragraph/section breaks in the IRS guidance PDFs. The 1301 instructions already have clear section headers (חלק א', חלק ב', etc.). Split on these natural boundaries.
2. **Use larger chunks for Hebrew** — if you must use size-based chunking, use character count (not token count) and set it to 1500-2000 characters with 300 char overlap. This compensates for the tokenization tax.
3. **Benchmark embedding cost early** — index one year's guidance document and measure actual token consumption. Budget accordingly.
4. **Consider chunk metadata** — prepend section number and field name to each chunk as a header. This helps retrieval even if the chunk body is short.

**Warning signs:**
- RAG returns partial sentences as top results
- Cost per query is unexpectedly high
- Context window fills up with just 1-2 documents + system prompt

**Detection:** Tokenize a sample Hebrew paragraph and compare token count to English equivalent.

**Phase relevance:** RAG setup phase — chunk strategy must be designed before indexing.

**Confidence:** HIGH — tokenization behavior is verifiable with tiktoken, not speculation.

---

### Pitfall 3: Mixing Up Tax Years in RAG Retrieval

**What goes wrong:** The RAG system retrieves an explanation from the 2023 guidance document when the user is filling out their 2024 return. Tax rules change every year — exemption thresholds, deduction caps, new categories. A wrong-year answer is worse than no answer because the user trusts it.

**Why it happens:** If all guidance documents are in one vector store, or if year filtering isn't strictly enforced, the embedding similarity may return a 2023 chunk that's textually similar but legally wrong for 2024.

**Consequences:** User enters wrong amounts, claims wrong deductions, or misses new rules. Could result in penalties from the tax authority.

**Prevention:**
1. **Separate ChromaDB collection per tax year** — `collection_2022`, `collection_2023`, etc. Never query across years.
2. **Include year in every chunk's metadata AND text** — even if collections are separate, defense in depth.
3. **Lock the year in session state** — once the user selects a tax year, all RAG queries are scoped. No UI path should allow cross-year retrieval.
4. **Add a disclaimer** — "Based on 2024 guidance. Verify with the official document."

**Warning signs:**
- User asks about a field and gets a threshold number that doesn't match the official doc
- LLM response references rules that changed between years

**Detection:** Create a test with a known field that changed between years (e.g., personal credit point value) and verify the RAG returns the correct year's value.

**Phase relevance:** RAG indexing phase — collection architecture must enforce year isolation from the start.

**Confidence:** HIGH — this is a fundamental correctness requirement derived directly from the project requirements (RAG-2).

---

### Pitfall 4: Streamlit Has No Native RTL Support

**What goes wrong:** Streamlit renders everything left-to-right. Hebrew text appears left-aligned, text inputs have wrong cursor behavior, markdown renders Hebrew but left-aligned, form labels are misaligned. The app looks broken and unprofessional for Hebrew-speaking users.

**Why it happens:** Streamlit is built for English/LTR. There is no `direction` config option or RTL mode. The only approach is CSS injection via `st.markdown(unsafe_allow_html=True)`, which is fragile and can break on Streamlit version updates.

**Consequences:** Users have a poor experience. Reading flow is wrong. Form fields and labels don't align. Every Streamlit update could break the UI.

**Prevention:**
1. **Inject global RTL CSS at app startup** — use `st.markdown('<style>... direction: rtl; text-align: right; ...</style>', unsafe_allow_html=True)` at the top of every page. Cover `stApp`, `stMarkdown`, `stTextInput`, `stSelectbox`, etc.
2. **Create a `rtl_utils.py` module** — centralize all CSS hacks in one file. When Streamlit updates break something, fix it in one place.
3. **Pin the Streamlit version** — don't auto-upgrade. Test RTL rendering before any Streamlit version bump.
4. **Test components individually** — chat messages, dataframes, number inputs, select boxes, file uploaders all need separate RTL verification.
5. **Use `st.html()` for complex RTL-sensitive components** where `st.markdown` doesn't give enough control.

**Warning signs:**
- Hebrew text left-aligned in any component
- Cursor jumps to wrong position in text inputs
- Number inputs display digits in wrong order
- Chat messages render Hebrew from the wrong side

**Detection:** Visual inspection checklist after every Streamlit version update.

**Phase relevance:** UI phase — establish RTL foundation before building any UI components. Don't build 10 screens and then try to RTL-ify them.

**Confidence:** HIGH — the Streamlit community forum confirms no native RTL support. CSS injection is the only path.

---

## Moderate Pitfalls

### Pitfall 5: Vision API Responses Are Not Structured — Extraction Requires Explicit Schemas

**What goes wrong:** Sending a scanned 106 form image to GPT-4o Vision or Gemini with "extract the data" returns free-text descriptions instead of structured data. The LLM might say "The gross income appears to be around 180,000 NIS" instead of returning `{"gross_income": 180000}`. Parsing this free text introduces another failure point.

**Why it happens:** Without explicit output format instructions, Vision models describe what they see narratively. Different form layouts or image quality levels produce different response structures.

**Prevention:**
1. **Always use structured output** — use JSON mode or function calling to force the Vision API to return a predefined schema. Define a Pydantic model per document type (Form106, Form867, etc.).
2. **Provide a visual reference** — include in the prompt: "This is an Israeli form 106. Extract fields in the following JSON format: {field_name: value, ...}". List exact field names in Hebrew.
3. **Post-validate extracted values** — check that income > 0, tax withheld <= income, dates are valid, etc. Reject and re-prompt on validation failure.
4. **Handle multi-page forms** — some 106 forms span 2+ pages. Process each page and merge results, checking for duplicate fields.

**Warning signs:**
- Vision API returns narrative text instead of structured data
- Same form produces different field names on different runs
- Values extracted as strings when they should be numbers

**Phase relevance:** Document processing phase — output schema must be defined before any Vision integration.

**Confidence:** MEDIUM — based on common LLM integration patterns; specific Vision+Hebrew behavior needs empirical validation.

---

### Pitfall 6: Multi-Provider LLM Abstraction Becomes a Maintenance Tax

**What goes wrong:** Building a custom wrapper for OpenAI + Azure OpenAI + Gemini + Claude means maintaining 4 different SDK integrations, handling 4 different error types, 4 different rate-limiting behaviors, 4 different streaming formats, and 4 different Vision API interfaces. Every provider SDK update potentially breaks one path.

**Why it happens:** Each provider's SDK has different authentication patterns (API key vs OAuth vs service account), different model naming conventions, different structured output support (some support JSON schema, some don't), and different multimodal input formats.

**Prevention:**
1. **Use LiteLLM** — it provides a unified `completion()` interface for 100+ providers with consistent response format, error handling, and streaming. Already solves the exact multi-provider problem.
2. **If building custom:** abstract at the right level — wrap only `chat_completion(messages, model) -> response` and `embed(text) -> vector`. Don't try to unify every feature. Accept that some features are provider-specific.
3. **Validate Hebrew output quality per provider** — not all models handle Hebrew equally well. Claude and GPT-4o are generally strong. Gemini varies by model. Test with Hebrew tax prompts before claiming provider support.
4. **Don't abstract Vision separately from chat** — use models that support multimodal natively (GPT-4o, Gemini, Claude) rather than separate Vision APIs.

**Warning signs:**
- More than 100 lines of code in the LLM abstraction layer
- Provider-specific `if/elif` chains growing longer
- Different providers returning different quality answers for the same Hebrew prompt

**Phase relevance:** LLM integration phase — choose abstraction strategy early, before building features on top.

**Confidence:** MEDIUM — LiteLLM is well-established (verified via docs), but Hebrew-specific quality differences need empirical testing.

---

### Pitfall 7: Joint Filing (Spouse) Wizard Logic Explodes in Complexity

**What goes wrong:** Treating the spouse as a simple "copy-paste" of the primary filer's flow leads to edge cases everywhere. Israeli tax law has specific rules for joint returns: who is the "assessee" (נישום) vs "spouse" (בן/בת זוג), which income is attributed to whom, different credit point calculations per spouse, different pension contribution limits if one spouse is self-employed, and the election to file jointly vs separately for capital gains.

**Why it happens:** Developers model it as "times two" when it's actually "a different set of rules that interact with the primary filer's data." Fields like personal credit points depend on whether the spouse works, has children, etc. — creating cross-dependencies between the two column's data.

**Prevention:**
1. **Model the tax return as a single entity with two income streams** — not two separate returns merged. The data model should have `primary_income`, `spouse_income`, and shared fields (children, joint_capital_gains_election).
2. **Start with a single filer first** — get the wizard working for one person before adding spouse support. This is explicitly an MVP scoping decision.
3. **Don't hardcode tax rules** — load tax brackets, credit values, and thresholds from a per-year config file (JSON/YAML). When 2026 rules change, update the config, not the code.
4. **Test with real previous returns** — the user has returns from 2021-2024 filed by an accountant. Use these as ground truth for validation.

**Warning signs:**
- Conditional logic with >3 nesting levels involving spouse fields
- The same spouse question appears in multiple wizard steps
- Calculated fields don't match the accountant's numbers from previous years

**Phase relevance:** Wizard phase — design the data model before building the UI. Joint filing should be planned but implemented after single-filer wizard works.

**Confidence:** HIGH — derived directly from Israeli tax law complexity and the 1301 form structure.

---

### Pitfall 8: PDF Text Extraction Succeeds but Table Data Is Wrong

**What goes wrong:** Form 106 is a structured table. Text extraction preserves the characters but loses the spatial relationships — you get "18000045000" instead of "180,000" in column A and "45,000" in column B. Field values merge with their labels. Row/column alignment is lost.

**Why it happens:** `get_text()` returns a flat text stream. Tables need spatial awareness — which text belongs to which cell. Even `find_tables()` (PyMuPDF) or `extract_table()` (pdfplumber) can fail on forms that use complex layouts with merged cells, nested tables, or fixed-width columns without visible grid lines.

**Prevention:**
1. **Use table extraction methods, not text extraction** — PyMuPDF's `page.find_tables()` or pdfplumber's `page.extract_table()`. These detect table structures from line graphics.
2. **If tables have no visible lines** (common in Israeli government forms) — use pdfplumber's `extract_table()` with custom `table_settings` to define explicit column boundaries.
3. **Map known form layouts** — Form 106 has a fixed layout per year. Define expected column positions per form type/year. This is more reliable than auto-detection.
4. **Prefer Vision API for complex forms** — for forms that resist programmatic extraction, sending the image to GPT-4o with a structured output schema may be more reliable than fighting with PDF parsers.
5. **Always show extracted data for user confirmation** (requirement DOC-7) — never auto-populate the return without human review.

**Warning signs:**
- Extracted number doesn't match what's visible in the PDF
- Multi-digit numbers appear merged or split
- Column headers don't align with their values

**Detection:** Extract a known form and compare extracted field values to manually read values.

**Phase relevance:** PDF processing phase — table extraction strategy must be validated with real 106 forms before building downstream features.

**Confidence:** HIGH — table extraction from PDFs is a universally acknowledged hard problem, compounded by Hebrew RTL issues.

---

### Pitfall 9: ChromaDB Collection Lock-in Makes Embedding Model Switches Expensive

**What goes wrong:** After indexing all guidance documents with `text-embedding-3-small`, you discover that the Hebrew retrieval quality is poor and want to switch to a multilingual model (e.g., `multilingual-e5-large` or `text-embedding-3-large`). But you can't mix embedding models in one collection — all existing embeddings must be regenerated.

**Why it happens:** Embeddings from different models have different dimensions and occupy different vector spaces. They're not comparable. Switching models means re-indexing everything.

**Prevention:**
1. **Evaluate embedding quality on Hebrew before committing** — create a small test set of 20 questions about the tax guidance with known correct chunks. Test retrieval accuracy with 2-3 embedding models before indexing all documents.
2. **Make re-indexing trivial** — the indexing pipeline should be a one-command script. Keep source PDFs and chunked text separate from embeddings. Re-indexing should take seconds for 4 documents.
3. **Store the model name in collection metadata** — so you always know which model was used.
4. **Consider that the user picks their LLM provider** — embedding model must work regardless of LLM choice. Using OpenAI embeddings when the user has only a Claude API key creates a dependency mismatch. Options: (a) require an OpenAI key just for embeddings, (b) use a free local embedding model (sentence-transformers), or (c) embed at index time (developer runs it) so users don't need embedding API access.

**Warning signs:**
- RAG returns irrelevant chunks for clear Hebrew questions
- Different embedding providers give wildly different retrieval quality
- Users need an API key from a provider they didn't choose just for embeddings

**Detection:** Run retrieval evaluation before building features on top of RAG.

**Phase relevance:** RAG setup phase — embedding model evaluation should happen before full indexing.

**Confidence:** MEDIUM — ChromaDB behavior is documented; Hebrew retrieval quality needs empirical testing.

---

## Minor Pitfalls

### Pitfall 10: LLM Hallucinating Tax Advice Despite RAG

**What goes wrong:** The LLM confidently states a deduction threshold or tax rate that isn't in the retrieved context — it's from its training data, which may be from the wrong year or wrong jurisdiction entirely.

**Prevention:**
1. Add a system prompt that says: "Answer ONLY based on the provided context. If the context doesn't contain the answer, say 'I don't have information about this in the [year] guidance document.'"
2. Display the source context alongside the answer so the user can verify.
3. Never present computed tax amounts as authoritative — always qualify with "estimated based on the guidance" and direct users to verify with the official document.

**Phase relevance:** LLM integration and chat phases.

**Confidence:** HIGH — hallucination is a universal LLM problem, amplified in domain-specific applications.

---

### Pitfall 11: State Management Corruption in Streamlit Session State

**What goes wrong:** Streamlit reruns the entire script on every interaction. Session state (`st.session_state`) can lose wizard progress if not carefully managed. Users lose filled-in data when navigating between pages, or data from a previous tax year leaks into the current one.

**Prevention:**
1. Persist state to a JSON file on disk (not just `st.session_state`) — fulfill requirement WIZ-7 from the start.
2. Use a clear state key naming convention: `{tax_year}_{section}_{field}`.
3. Add explicit save/load functions called on page transitions.
4. Never store raw PDF data in session state — store file paths and extracted results.

**Phase relevance:** Wizard/UI phase — architecture must support persistence before building the multi-step wizard.

**Confidence:** MEDIUM — well-known Streamlit pattern issue.

---

### Pitfall 12: API Key Exposure in Git or Session State

**What goes wrong:** The user's LLM API key ends up in committed code, debug logs, or exported session state. Since this is a local app with personal financial documents, security is critical.

**Prevention:**
1. Store API keys in `.env` only — never in JSON config, never in session state.
2. Add `.env`, `*.json` (config files with keys), and `user_data/` to `.gitignore` from day one.
3. Never log API keys or include them in error messages.
4. Use `st.secrets` or `python-dotenv` — not environment variables set in shell.

**Phase relevance:** Project setup phase — `.gitignore` and `.env.example` should exist before any code.

**Confidence:** HIGH — security hygiene.

---

### Pitfall 13: RSU/Stock Report Extraction Has Different Structure Than Tax Forms

**What goes wrong:** Developers assume the E*TRADE (or similar broker) RSU annual report has a standard format like Form 106. It doesn't. RSU reports from different brokers have wildly different layouts, and even E*TRADE changes their format between years. A parser built for the 2023 report breaks on 2024.

**Prevention:**
1. Use Vision API for RSU reports rather than programmatic extraction — the format variability makes template-based parsing fragile.
2. Define a clear output schema (sale date, quantity, proceeds, cost basis, gain/loss, tax withheld) and let the Vision API extract to that schema.
3. Validate extracted transactions against the total summary (sum of individual sales = total reported gain/loss).

**Phase relevance:** Document processing phase, specifically after basic 106 extraction works.

**Confidence:** MEDIUM — format variability is known from user context (E*TRADE RSU reports).

---

### Pitfall 14: Hebrew Government PDFs Have Inconsistent Internal Structure

**What goes wrong:** The IRS guidance PDFs (in `IRS_Docs/`) may use different internal PDF structures between years. One year might use native text objects, another might embed text as vector graphics, and another might use CID-keyed fonts that don't map to Unicode cleanly.

**Prevention:**
1. Test text extraction on ALL four guidance documents (2022-2025) during the PDF processing phase — don't assume they're all the same.
2. Have a fallback pipeline: try text extraction → if quality is low, use Vision API.
3. Quality check: after extraction, verify that expected section headers exist in the output (e.g., "חלק א'" through "חלק ל'").

**Phase relevance:** RAG indexing phase — extraction quality directly determines RAG quality.

**Confidence:** MEDIUM — inconsistency is common in government PDFs but needs empirical verification with these specific files.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Project Setup | API key exposure (#12) | `.gitignore` + `.env.example` from day one |
| PDF Processing | Hebrew text reversal (#1), table extraction (#8) | Validate with real 106 forms immediately |
| RAG Indexing | Year cross-contamination (#3), tokenization bloat (#2), embedding lock-in (#9) | Separate collections, semantic chunking, evaluate embeddings first |
| LLM Integration | Multi-provider maintenance (#6), hallucination (#10) | Use LiteLLM, add RAG-grounding guardrails |
| Wizard UI | Joint filing complexity (#7), state management (#11) | Single filer first, persist to disk |
| Streamlit RTL | No native RTL (#4), CSS fragility | Centralize RTL hacks, pin Streamlit version |
| Vision/OCR | Unstructured responses (#5), RSU format variability (#13) | Structured output schemas, per-document Pydantic models |
| Guidance PDF indexing | Inconsistent PDF internals (#14) | Test all 4 files individually |

## Sources

- pdfplumber RTL bugs: [#794](https://github.com/jsvine/pdfplumber/issues/794), [#1159](https://github.com/jsvine/pdfplumber/issues/1159), [#1187](https://github.com/jsvine/pdfplumber/pull/1187) — **verified, still open**
- PyMuPDF text extraction docs: [pymupdf.readthedocs.io/en/latest/recipes-text.html](https://pymupdf.readthedocs.io/en/latest/recipes-text.html)
- OpenAI Embeddings: [developers.openai.com/api/docs/guides/embeddings](https://developers.openai.com/api/docs/guides/embeddings) — "higher multilingual performance" for v3 models
- LiteLLM multi-provider: [docs.litellm.ai/docs](https://docs.litellm.ai/docs/) — verified unified interface for OpenAI/Anthropic/Gemini
- Streamlit RTL: no native support confirmed via community forum search and issue tracker — CSS injection is the only approach
- tiktoken Hebrew tokenization: verifiable via `tiktoken.get_encoding("cl100k_base").encode("הכנסה")` — returns 3-5 tokens per Hebrew word
