---
phase: 01
slug: project-scaffolding-llm-configuration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-10
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), Vitest (frontend) |
| **Config file** | `backend/pytest.ini` (Wave 0), `frontend/vite.config.ts` |
| **Quick run command** | `cd backend && python -m pytest tests/ -x --tb=short` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x --tb=short`
- **After every plan wave:** Run `make test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | INF-01 | manual | Visual inspection of `index.html` for `dir="rtl"` `lang="he"` | N/A | ⬜ pending |
| 01-01-02 | 01 | 1 | INF-02 | smoke | `make run` smoke test | N/A | ⬜ pending |
| 01-01-03 | 01 | 1 | INF-03 | unit | `grep -q ".env" .gitignore` | ✅ | ⬜ pending |
| 01-02-01 | 02 | 1 | LLM-01 | unit | `pytest tests/test_settings.py::test_provider_selection -x` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | LLM-02 | unit | `pytest tests/test_settings.py::test_api_key_storage -x` | ❌ W0 | ⬜ pending |
| 01-02-03 | 02 | 1 | LLM-03 | unit | `pytest tests/test_settings.py::test_model_selection -x` | ❌ W0 | ⬜ pending |
| 01-02-04 | 02 | 1 | LLM-04 | integration | `pytest tests/test_settings.py::test_connection_validation -x` | ❌ W0 | ⬜ pending |
| 01-02-05 | 02 | 1 | LLM-05 | unit | `pytest tests/test_settings.py::test_settings_persistence -x` | ❌ W0 | ⬜ pending |
| 01-02-06 | 02 | 1 | INF-04 | unit | `pytest tests/test_settings.py::test_no_key_in_response -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_settings.py` — stubs for LLM-01..05, INF-04
- [ ] `backend/tests/conftest.py` — shared fixtures (test .env file, mock LiteLLM)
- [ ] `backend/pytest.ini` — test configuration
- [ ] Vitest setup in frontend (for future frontend tests)

*Wave 0 creates test stubs before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hebrew RTL layout renders correctly | INF-01 | Visual layout, font rendering, RTL direction | Open browser, verify `dir="rtl"` in DOM, check text flows right-to-left, confirm Hebrew font loads |
| App launches on macOS | INF-02 | System-level smoke test | Run `make run`, verify both ports respond |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
