# Phase 1: Project Scaffolding & LLM Configuration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-10
**Phase:** 01-project-scaffolding-llm-configuration
**Areas discussed:** App Launch & Dev Workflow, LLM Settings UI, API Key Validation UX, Project Structure
**Mode:** auto (all recommended defaults selected)

---

## App Launch & Dev Workflow

| Option | Description | Selected |
|--------|-------------|----------|
| Single command (make run) | Starts both frontend and backend concurrently | ✓ |
| Separate terminals | User starts frontend and backend manually | |
| Docker Compose | Containerized dev environment | |

**User's choice:** [auto] Single command — recommended for local dev simplicity
**Notes:** Vite on 5173, uvicorn on 8000, frontend proxies /api/* to backend

## LLM Settings UI

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated Settings page | Full page, landing on first launch | ✓ |
| Modal dialog | Overlay on any page | |
| Onboarding wizard | Multi-step first-run flow | |

**User's choice:** [auto] Dedicated Settings page — recommended for discoverability and space for 4 provider cards
**Notes:** Card-based provider picker with logos, model dropdown + API key input below selected card

## API Key Validation UX

| Option | Description | Selected |
|--------|-------------|----------|
| Inline indicator + Test button | Green check / red X next to field | ✓ |
| Toast notification | Transient popup message | |
| Separate test page | Dedicated connection diagnostics | |

**User's choice:** [auto] Inline indicator — recommended for immediate, contextual feedback
**Notes:** LiteLLM completion() call with short Hebrew prompt. Backend validates before saving.

## Project Structure

| Option | Description | Selected |
|--------|-------------|----------|
| /frontend + /backend siblings | Monorepo with root Makefile | ✓ |
| Single directory | Combined Python+JS in one tree | |
| Separate repos | Independent frontend/backend repos | |

**User's choice:** [auto] Siblings monorepo — recommended for single-developer local app
**Notes:** requirements.txt (not Poetry), npm (not yarn/pnpm), Makefile for orchestration

## Agent's Discretion

- Color scheme and component styling (shadcn/ui defaults + RTL)
- LiteLLM test prompt content
- Error message wording (Hebrew)
- FastAPI internal structure (routers, schemas)

## Deferred Ideas

None
