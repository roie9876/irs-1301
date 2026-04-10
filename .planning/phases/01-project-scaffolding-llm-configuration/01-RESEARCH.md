# Phase 1: Project Scaffolding & LLM Configuration - Research

**Researched:** 2026-04-10
**Domain:** React+Vite frontend + FastAPI backend scaffolding, LLM multi-provider configuration, Hebrew RTL
**Confidence:** HIGH

## Summary

Phase 1 creates the application shell: a React+Vite+TypeScript frontend with shadcn/ui components in full Hebrew RTL, and a FastAPI backend that wraps LiteLLM for multi-provider LLM connectivity. The user's locked decisions override the earlier Streamlit research — the app is now a React/FastAPI monorepo.

The core technical challenges are: (1) establishing proper RTL support from day one using Tailwind CSS logical properties and `dir="rtl"` on the HTML element, (2) building a Settings page with provider card selection and connection testing via LiteLLM, and (3) persisting API keys in a `.env` file that the backend reads/writes at runtime.

**Primary recommendation:** Use `create vite` with React+TypeScript template, install shadcn/ui via its CLI, set up FastAPI with a clean router-based structure, and use `python-dotenv`'s `set_key()` for runtime `.env` mutation. Use `concurrently` npm package at root level to start both servers with one command.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Single command (`make run` or npm script) starts both frontend (Vite dev server on port 5173) and backend (uvicorn on port 8000) concurrently.
- **D-02:** Frontend proxies `/api/*` requests to the backend — no CORS issues in dev.
- **D-03:** A `Makefile` at root orchestrates common tasks (run, install, test, lint).
- **D-04:** Dedicated Settings page (not a modal) — accessible from sidebar or header navigation.
- **D-05:** On first launch with no provider configured, the app redirects to Settings as the landing page.
- **D-06:** Provider selection: card-based picker with 4 cards (OpenAI, Azure OpenAI, Gemini, Claude) showing provider logo/icon. Selecting a card reveals model dropdown + API key input below.
- **D-07:** Model selection: dropdown populated with common models per provider (e.g., gpt-4o, gpt-4o-mini for OpenAI; claude-sonnet-4 for Claude). User can also type a custom model name.
- **D-08:** "Test Connection" button next to API key field. Triggers a minimal LiteLLM `completion()` call with a short Hebrew prompt.
- **D-09:** Inline status indicator: green checkmark + "חיבור תקין" on success, red X + error message on failure. No toast or modal — immediate inline feedback.
- **D-10:** Backend validates the key on save — stores only after successful test.
- **D-11:** Monorepo layout: `/frontend` (React+Vite+TypeScript) and `/backend` (Python+FastAPI) as top-level siblings.
- **D-12:** Root `Makefile` with targets: `install`, `run`, `lint`, `test`.
- **D-13:** Backend dependencies: `requirements.txt` in `/backend` (no Poetry — keep it simple for a local app).
- **D-14:** Frontend package manager: npm with `package.json` in `/frontend`.
- **D-15:** shadcn/ui for component library — provides professional, accessible, RTL-compatible components.
- **D-16:** API keys and provider settings stored in `/backend/.env` file (dotenv). Loaded by FastAPI on startup.
- **D-17:** `.gitignore` already excludes `.env` files and personal data — verified in existing project setup.

### Agent's Discretion
- Color scheme, specific component styling — agent decides based on shadcn/ui defaults with RTL adjustments.
- Exact LiteLLM test prompt content — agent picks something short and Hebrew.
- Error message wording for connection failures — agent writes appropriate Hebrew text.
- FastAPI project structure (routers, schemas, etc.) — agent follows standard patterns.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LLM-01 | User selects LLM provider from: OpenAI, Azure OpenAI, Google Gemini, Anthropic Claude | LiteLLM provider prefixes, card-based UI pattern with shadcn/ui Card component |
| LLM-02 | User enters personal API key stored locally in .env | `python-dotenv` `set_key()` for runtime write, `load_dotenv()` for read |
| LLM-03 | User selects specific model from provider (gpt-4o, claude-sonnet, gemini-2.0-flash etc.) | LiteLLM model naming conventions, Combobox pattern for type+select |
| LLM-04 | System validates API key on setup (connection test) | LiteLLM `completion()` with short Hebrew prompt, error handling patterns |
| LLM-05 | Provider and model settings persist locally without re-entry | `.env` file persistence via `set_key()`, FastAPI reads on startup |
| INF-01 | Full Hebrew RTL interface | `dir="rtl"` on HTML, Tailwind CSS logical properties, Hebrew font |
| INF-02 | Runs locally on macOS (Apple Silicon) | Node v25, Python 3.14 verified available, no Docker needed |
| INF-03 | Personal documents excluded from GitHub | `.gitignore` already configured for `.env`, uploads, personal data |
| INF-04 | API Keys stored in local .env only | `backend/.env` file, never committed, `set_key()` for write |

</phase_requirements>

## Project Constraints (from copilot-instructions.md)

The `copilot-instructions.md` file contains the same project description and constraints as PROJECT.md. Key directives:
- Privacy: personal documents never committed to git
- Local only: no cloud servers, only LLM API calls
- Mac (Apple Silicon): local development environment
- Hebrew: full RTL interface
- Multi-provider: user chooses their own LLM provider and API key

**Important stack override:** The earlier STACK.md research recommended Streamlit (and explicitly listed FastAPI as "What NOT to Use"). The user overrode this during the discussion phase, choosing React + Vite + FastAPI for a more professional UI with full RTL control. PROJECT.md Key Decisions confirms: "React + Vite + FastAPI | ✓ Good". This is the locked decision — Streamlit is no longer relevant for this project.

## Standard Stack

### Frontend Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | 19.2.5 | UI framework | Latest stable, ecosystem standard |
| react-dom | 19.2.5 | DOM rendering | Required companion to React |
| typescript | 6.0.2 | Type safety | Catches bugs at compile time, better DX |
| vite | 8.0.8 | Build tool + dev server | Fastest HMR, built-in proxy, ESM-native |
| @vitejs/plugin-react | 6.0.1 | React integration for Vite | Official plugin, enables JSX transform |

### Frontend UI
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tailwindcss | 4.2.2 | Utility CSS framework | RTL support via logical properties, shadcn/ui requirement |
| shadcn/ui | latest CLI | Component library | Accessible Radix-based components, copies source code into project |
| lucide-react | 1.8.0 | Icon library | shadcn/ui default icon set |
| class-variance-authority | 0.7.1 | Variant styling | shadcn/ui dependency for component variants |
| clsx | 2.1.1 | Class merging | Conditional className composition |
| tailwind-merge | 3.5.0 | Tailwind class deduplication | Prevents conflicting Tailwind classes |
| react-router-dom | 7.14.0 | Client-side routing | Settings page routing, navigation |

### Backend Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.135.3 | API framework | Async, auto-docs, Pydantic integration |
| uvicorn | 0.44.0 | ASGI server | Standard FastAPI server |
| pydantic | 2.12.5 | Data validation/schemas | FastAPI's native validation layer |
| python-dotenv | 1.2.2 | .env file management | Read AND write .env files at runtime |
| litellm | 1.83.4 | Multi-provider LLM abstraction | Single `completion()` for all 4 providers |

### Dev Tooling
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| concurrently | (npm) | Run frontend+backend together | Cross-platform parallel process runner |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| shadcn/ui | Ant Design / MUI | shadcn/ui gives source ownership, smaller bundle, RTL via Radix primitives |
| react-router-dom | TanStack Router | react-router is simpler for a small app with 2-3 routes |
| concurrently | npm-run-all2 | concurrently has better output formatting, both work fine |
| python-dotenv | pydantic-settings | pydantic-settings is overkill for 4 env vars; dotenv's `set_key()` handles runtime writes |

**Installation:**

Frontend:
```bash
cd frontend
npm create vite@latest . -- --template react-ts
npx shadcn@latest init
npm install react-router-dom lucide-react
```

Backend:
```bash
cd backend
pip install fastapi uvicorn python-dotenv litellm pydantic
```

## Architecture Patterns

### Recommended Project Structure
```
irs-1301/
├── Makefile                  # Root orchestrator (install, run, test, lint)
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts        # Proxy config for /api/*
│   ├── index.html            # dir="rtl" lang="he"
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx           # Router setup
│   │   ├── components/
│   │   │   └── ui/           # shadcn/ui components (auto-generated)
│   │   ├── pages/
│   │   │   └── SettingsPage.tsx
│   │   ├── lib/
│   │   │   ├── utils.ts      # cn() helper (shadcn/ui)
│   │   │   └── api.ts        # Fetch wrapper for /api/* calls
│   │   └── styles/
│   │       └── globals.css   # Tailwind imports + Hebrew font
│   └── components.json       # shadcn/ui config
├── backend/
│   ├── requirements.txt
│   ├── .env                  # API keys (gitignored)
│   ├── .env.example          # Template (committed)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI app creation, CORS, startup
│   │   ├── routers/
│   │   │   └── settings.py   # GET/POST /api/settings, POST /api/settings/test
│   │   ├── schemas/
│   │   │   └── settings.py   # Pydantic models for settings request/response
│   │   └── services/
│   │       └── llm.py        # LiteLLM wrapper: test_connection(), get_provider_models()
│   └── tests/
│       └── test_settings.py
├── IRS_Docs/                 # Existing — tax guidance documents
├── .gitignore                # Existing — already excludes .env, personal data
└── copilot-instructions.md   # Existing — project context
```

### Pattern 1: Vite Proxy Configuration
**What:** Frontend proxies all `/api/*` requests to the FastAPI backend during development.
**When to use:** Always in dev mode. Eliminates CORS configuration.
**Example:**
```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### Pattern 2: RTL Setup (HTML + Tailwind)
**What:** Full RTL support using HTML `dir` attribute and Tailwind CSS logical properties.
**When to use:** From the very first page render.
**Example:**
```html
<!-- index.html -->
<!DOCTYPE html>
<html lang="he" dir="rtl">
  <head>
    <meta charset="UTF-8" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link href="https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700&display=swap" rel="stylesheet" />
    <title>עוזר דוח שנתי 1301</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

```css
/* globals.css */
@import "tailwindcss";

:root {
  font-family: "Assistant", system-ui, sans-serif;
}
```

**Key insight:** With `dir="rtl"` on `<html>`, Radix UI primitives (used by shadcn/ui) automatically flip their layout. Tailwind CSS 4.x supports logical properties natively — use `ms-*` (margin-inline-start) instead of `ml-*`, `me-*` instead of `mr-*`, `ps-*` instead of `pl-*`, `pe-*` instead of `pr-*`. This ensures all spacing adapts to RTL automatically.

### Pattern 3: FastAPI Router Organization
**What:** Separate router module for settings endpoints.
**When to use:** Standard FastAPI pattern for modular apps.
**Example:**
```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import settings

app = FastAPI(title="עוזר דוח שנתי 1301")

# CORS for production (Vite proxy handles dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(settings.router, prefix="/api")
```

### Pattern 4: LiteLLM Provider Model Naming
**What:** LiteLLM uses provider-prefixed model names for routing.
**When to use:** Every `completion()` call.
**Example:**
```python
import litellm

# OpenAI — no prefix needed (default provider)
litellm.completion(model="gpt-4o", messages=[...], api_key="sk-...")

# Anthropic Claude — prefix with "anthropic/"
litellm.completion(model="anthropic/claude-sonnet-4-20250514", messages=[...], api_key="sk-ant-...")

# Google Gemini — prefix with "gemini/"
litellm.completion(model="gemini/gemini-2.0-flash", messages=[...], api_key="AIza...")

# Azure OpenAI — prefix with "azure/" + requires api_base
litellm.completion(
    model="azure/gpt-4o",  # deployment name
    messages=[...],
    api_key="...",
    api_base="https://your-resource.openai.azure.com/"
)
```

### Pattern 5: Settings Persistence with python-dotenv
**What:** Read and write `.env` file at runtime for settings persistence.
**When to use:** Save/load provider, model, API key on settings page.
**Example:**
```python
from dotenv import load_dotenv, set_key
import os

ENV_PATH = os.path.join(os.path.dirname(__file__), '..', '.env')

def load_settings():
    load_dotenv(ENV_PATH, override=True)
    return {
        "provider": os.getenv("LLM_PROVIDER", ""),
        "model": os.getenv("LLM_MODEL", ""),
        "has_api_key": bool(os.getenv("LLM_API_KEY")),
        # Azure-specific
        "api_base": os.getenv("AZURE_API_BASE", ""),
    }

def save_settings(provider: str, model: str, api_key: str, api_base: str = ""):
    set_key(ENV_PATH, "LLM_PROVIDER", provider)
    set_key(ENV_PATH, "LLM_MODEL", model)
    set_key(ENV_PATH, "LLM_API_KEY", api_key)
    if api_base:
        set_key(ENV_PATH, "AZURE_API_BASE", api_base)
    # Reload into environment
    load_dotenv(ENV_PATH, override=True)
```

### Anti-Patterns to Avoid
- **Don't use separate env vars per provider** (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` simultaneously). Use one `LLM_API_KEY` + `LLM_PROVIDER` — the user uses one provider at a time.
- **Don't return the API key in GET responses.** Return `has_api_key: true/false` instead. The frontend never needs to display the full key.
- **Don't use `ml-*`/`mr-*`/`pl-*`/`pr-*` Tailwind classes.** Always use logical properties (`ms-*`/`me-*`/`ps-*`/`pe-*`) so layout works in RTL.
- **Don't hardcode provider model lists in the backend.** Keep them in a simple JSON/dict structure in the frontend — they're display-only and change frequently.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-provider LLM calls | Custom SDK wrapper for 4 providers | LiteLLM `completion()` | 4 SDKs × 4 error formats × 4 auth patterns = maintenance nightmare |
| UI component library | Custom buttons, inputs, cards from scratch | shadcn/ui (Radix primitives) | Accessibility, RTL support, consistent design out of the box |
| .env file read/write | Custom file parser | python-dotenv `load_dotenv()` + `set_key()` | Handles quoting, escaping, comments, multiline values |
| Concurrent process runner | Shell `&` + `wait` | `concurrently` npm package | Better output formatting, colored prefixes, proper signal handling |
| RTL CSS framework | Manual CSS overrides per component | Tailwind logical properties + `dir="rtl"` | Radix/shadcn already respect `dir` attribute; Tailwind logical props handle spacing |
| Client routing | Manual URL parsing / conditional rendering | react-router-dom | Handles history, redirects, nested routes, lazy loading |

**Key insight:** This phase is pure scaffolding. Every component has a mature off-the-shelf solution. The only custom code should be: (1) the Settings page UI composition, (2) the LiteLLM test_connection service function, and (3) the .env read/write service.

## Common Pitfalls

### Pitfall 1: shadcn/ui Components Don't Flip in RTL
**What goes wrong:** Icons, chevrons, and padding appear on the wrong side. Dropdown menus open in the wrong direction.
**Why it happens:** shadcn/ui itself doesn't add RTL-specific CSS. It relies on Radix UI primitives which DO respect `dir="rtl"` on a parent element, but only for positioning behavior — visual spacing still uses physical properties.
**How to avoid:** 
1. Set `dir="rtl"` on `<html>` (not just a wrapper div) so ALL Radix primitives detect it.
2. When customizing shadcn/ui components, replace `ml-*`/`mr-*` with `ms-*`/`me-*` (logical properties).
3. Flip chevron icons manually where needed (`<ChevronLeft>` becomes the "forward" arrow in RTL).
**Warning signs:** Dropdowns open from the wrong edge. Card action buttons cluster on the wrong side.

### Pitfall 2: Azure OpenAI Requires Extra Configuration
**What goes wrong:** User enters Azure OpenAI API key but connection fails because `api_base` (resource URL) is missing.
**Why it happens:** Unlike other providers, Azure OpenAI requires both an API key AND a deployment endpoint URL. LiteLLM needs `api_base` parameter for Azure.
**How to avoid:** When user selects "Azure OpenAI" provider, show an additional "Endpoint URL" input field (e.g., `https://your-resource.openai.azure.com/`). Pass both `api_key` and `api_base` to LiteLLM.
**Warning signs:** "AuthenticationError" or "Resource not found" when Azure is selected but api_base is missing.

### Pitfall 3: LiteLLM Test Call Costs Money and Takes Time
**What goes wrong:** Each "Test Connection" click makes a real API call. Users click multiple times. Slow models (some Gemini variants) take 5+ seconds to respond. Users think it's broken and click again.
**Why it happens:** There's no way to validate an API key without making a real call to most providers.
**How to avoid:**
1. Use the cheapest/fastest model for the test (e.g., `gpt-4o-mini` for OpenAI, `gemini-2.0-flash` for Gemini).
2. Keep the test prompt minimal: 1-2 tokens response. Use `max_tokens=5`.
3. Show a loading spinner immediately on click.
4. Disable the "Test" button while a test is in progress.
5. Catch and translate common errors to Hebrew: "מפתח לא תקף", "ספק לא זמין", "שגיאת רשת".
**Warning signs:** Multiple identical API calls in quick succession. Users complaining about delay.

### Pitfall 4: python-dotenv `set_key()` Creates File If Missing
**What goes wrong:** On first launch, there's no `backend/.env` file. `set_key()` creates it without issues, but `load_dotenv()` on subsequent startup may fail silently if the path is wrong, leading to empty environment variables.
**Why it happens:** Relative path resolution differs between `uvicorn app.main:app` (from `/backend`) vs running from project root.
**How to avoid:** Use an absolute path for the `.env` file, computed relative to the Python module:
```python
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
```
**Warning signs:** Settings "forget" after restart. `os.getenv()` returns `None` for keys that are in the file.

### Pitfall 5: Vite Proxy Only Works in Dev Mode
**What goes wrong:** Everything works in dev, but when someone runs `vite build` and serves the static files, API calls fail with 404.
**Why it happens:** Vite's proxy is a dev server feature only. Production builds output static HTML/JS/CSS with no proxy.
**How to avoid:** This is a local dev app — it will always run in dev mode with `vite dev`. Don't worry about production builds for v1. If ever needed, FastAPI can serve the built frontend as static files.
**Warning signs:** N/A for this phase — dev mode is the production mode for a local app.

### Pitfall 6: Hebrew Font Not Loading or Falling Back to System Font
**What goes wrong:** Google Fonts CDN is blocked, slow, or the `@import` is wrong. Hebrew text renders in default sans-serif which looks unprofessional.
**Why it happens:** Network dependency on Google Fonts CDN. Some network environments block it.
**How to avoid:** Use the `<link>` tag in `index.html` (not `@import` in CSS — it blocks rendering). "Assistant" is a good Hebrew font — designed for screen readability, supports all Hebrew characters, free on Google Fonts. Fallback to system-ui.
**Warning signs:** Font flicker on page load (FOUT). Different font rendering between first load and cached load.

## Code Examples

### Settings API Endpoints
```python
# backend/app/routers/settings.py
from fastapi import APIRouter, HTTPException
from app.schemas.settings import SettingsRequest, SettingsResponse, TestResult
from app.services.llm import test_connection, load_settings, save_settings

router = APIRouter(tags=["settings"])

@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    settings = load_settings()
    return settings  # Note: never return the actual API key

@router.post("/settings/test", response_model=TestResult)
async def test_settings(request: SettingsRequest):
    try:
        result = await test_connection(
            provider=request.provider,
            model=request.model,
            api_key=request.api_key,
            api_base=request.api_base,
        )
        return TestResult(success=True, message="חיבור תקין")
    except Exception as e:
        return TestResult(success=False, message=str(e))

@router.post("/settings", response_model=SettingsResponse)
async def save_settings_endpoint(request: SettingsRequest):
    # Validate connection before saving
    try:
        await test_connection(
            provider=request.provider,
            model=request.model,
            api_key=request.api_key,
            api_base=request.api_base,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"חיבור נכשל: {e}")
    
    save_settings(
        provider=request.provider,
        model=request.model,
        api_key=request.api_key,
        api_base=request.api_base,
    )
    return load_settings()
```

### LiteLLM Connection Test
```python
# backend/app/services/llm.py
import litellm
from litellm import completion

PROVIDER_MODEL_MAP = {
    "openai": "gpt-4o-mini",       # cheapest for test
    "azure": "azure/gpt-4o-mini",  # needs api_base
    "gemini": "gemini/gemini-2.0-flash",
    "anthropic": "anthropic/claude-sonnet-4-20250514",
}

async def test_connection(provider: str, model: str, api_key: str, api_base: str = "") -> dict:
    """Test LLM connection with a minimal Hebrew prompt."""
    # Build the model string for LiteLLM
    if provider == "openai":
        llm_model = model  # OpenAI needs no prefix
    elif provider == "azure":
        llm_model = f"azure/{model}"
    elif provider == "gemini":
        llm_model = f"gemini/{model}"
    elif provider == "anthropic":
        llm_model = f"anthropic/{model}"
    else:
        raise ValueError(f"ספק לא מוכר: {provider}")
    
    kwargs = {
        "model": llm_model,
        "messages": [{"role": "user", "content": "מה זה טופס 1301? ענה במשפט אחד."}],
        "api_key": api_key,
        "max_tokens": 30,
    }
    if provider == "azure" and api_base:
        kwargs["api_base"] = api_base
    
    response = completion(**kwargs)
    return {"content": response.choices[0].message.content}
```

### Provider Card UI Component
```tsx
// Conceptual pattern for the Settings page provider cards
const PROVIDERS = [
  { id: "openai", name: "OpenAI", models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"] },
  { id: "azure", name: "Azure OpenAI", models: ["gpt-4o", "gpt-4o-mini"], needsApiBase: true },
  { id: "gemini", name: "Google Gemini", models: ["gemini-2.0-flash", "gemini-2.5-pro"] },
  { id: "anthropic", name: "Anthropic Claude", models: ["claude-sonnet-4-20250514", "claude-haiku-35-20250620"] },
]

// Card selected → reveal model dropdown + API key input below
// Azure selected → also reveal Endpoint URL input
```

### Makefile Pattern
```makefile
.PHONY: install run lint test

install:
	cd frontend && npm install
	cd backend && pip install -r requirements.txt

run:
	cd frontend && npm run dev & \
	cd backend && uvicorn app.main:app --reload --port 8000 & \
	wait

# Or with concurrently (better output):
run:
	npx concurrently \
		"cd frontend && npm run dev" \
		"cd backend && uvicorn app.main:app --reload --port 8000"

lint:
	cd frontend && npx tsc --noEmit
	cd backend && python -m ruff check .

test:
	cd frontend && npx vitest run
	cd backend && python -m pytest
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CRA (Create React App) | Vite | 2023 | Vite is the React community standard. CRA is deprecated |
| Tailwind CSS v3 (config file) | Tailwind CSS v4 (CSS-first config) | 2025 | v4 uses `@import "tailwindcss"` in CSS instead of `tailwind.config.js`. No `content` array needed |
| shadcn/ui v0 (manual copy) | shadcn CLI (`npx shadcn@latest`) | 2024 | CLI handles installation, dependencies, and path configuration |
| Physical CSS properties (ml/mr) | Logical CSS properties (ms/me) | Tailwind v3+ | Logical properties auto-flip in RTL without additional plugins |
| LiteLLM provider-specific env vars | LiteLLM unified `api_key` param | 2024 | Can pass `api_key` directly in `completion()` call instead of environment variables |

**Deprecated/outdated:**
- `@tailwindcss/rtl` plugin — no longer needed. Tailwind CSS v4 supports logical properties natively.
- `tailwind.config.js` — Tailwind v4 uses CSS-first configuration. The config file approach still works but is legacy.
- `npx create-react-app` — deprecated, use `npm create vite@latest` instead.

## Open Questions

1. **shadcn/ui + Tailwind v4 compatibility**
   - What we know: shadcn/ui CLI supports Tailwind v4 initialization since early 2025. The `npx shadcn@latest init` handles the setup.
   - What's unclear: Some older shadcn/ui components may still use physical properties (ml, mr) in their generated code.
   - Recommendation: After installing shadcn/ui components, grep for `ml-` and `mr-` and replace with `ms-` and `me-` where appropriate. This is a one-time per-component fix.

2. **LiteLLM async support**
   - What we know: LiteLLM offers `acompletion()` for async calls, which is preferred inside FastAPI async endpoints.
   - What's unclear: Whether `acompletion()` handles all providers identically to `completion()`.
   - Recommendation: Use `acompletion()` in FastAPI endpoints. Fall back to `completion()` wrapped in `asyncio.to_thread()` if any provider fails with async.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Frontend build + dev server | ✓ | v25.2.1 | — |
| npm | Package management | ✓ | 11.6.2 | — |
| Python 3 | Backend runtime | ✓ | 3.14.1 | — |
| pip | Python package management | ✓ | 25.3 | — |
| make | Build orchestration | ✓ | 3.81 | — |
| git | Version control | ✓ | 2.50.1 | — |
| .venv | Python virtual environment | ✓ | exists at .venv/ | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

All required tools are available. The Python venv already exists with PyMuPDF installed (not needed for Phase 1 but confirms venv is functional).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (Frontend) | Vitest (bundled with Vite ecosystem) |
| Framework (Backend) | pytest |
| Config file (Frontend) | `frontend/vite.config.ts` (vitest uses same config) |
| Config file (Backend) | `backend/pytest.ini` or `pyproject.toml` (Wave 0) |
| Quick run command | `cd backend && python -m pytest tests/ -x` |
| Full suite command | `make test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LLM-01 | Provider selection persists correctly | unit | `pytest tests/test_settings.py::test_provider_selection -x` | ❌ Wave 0 |
| LLM-02 | API key stored in .env, not exposed in GET | unit | `pytest tests/test_settings.py::test_api_key_storage -x` | ❌ Wave 0 |
| LLM-03 | Model selection works for each provider | unit | `pytest tests/test_settings.py::test_model_selection -x` | ❌ Wave 0 |
| LLM-04 | Connection test returns success/failure correctly | integration | `pytest tests/test_settings.py::test_connection_validation -x` | ❌ Wave 0 |
| LLM-05 | Settings persist across restarts (env file RW) | unit | `pytest tests/test_settings.py::test_settings_persistence -x` | ❌ Wave 0 |
| INF-01 | HTML has dir="rtl" and lang="he" | manual | Visual inspection of index.html | N/A |
| INF-02 | App starts on macOS | smoke | `make run` smoke test | N/A |
| INF-03 | .gitignore excludes .env and personal data | unit | `grep -q ".env" .gitignore` | ✅ Exists |
| INF-04 | API key only in .env, not in responses | unit | `pytest tests/test_settings.py::test_no_key_in_response -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/ -x --tb=short`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_settings.py` — covers LLM-01..05, INF-04
- [ ] `backend/tests/conftest.py` — shared fixtures (test .env file, mock LiteLLM)
- [ ] `backend/pytest.ini` or test config section
- [ ] Vitest config in frontend (for future frontend tests)

## Sources

### Primary (HIGH confidence)
- npm registry — verified versions for all frontend packages (2026-04-10)
- PyPI — verified versions for all backend packages (2026-04-10)
- LiteLLM docs: https://docs.litellm.ai/docs/providers — provider prefixes and model naming
- python-dotenv: https://pypi.org/project/python-dotenv/ — `set_key()` API for runtime write

### Secondary (MEDIUM confidence)
- Tailwind CSS v4 logical properties support — based on official Tailwind v4 release notes
- shadcn/ui Radix RTL compatibility — based on Radix UI's documented `dir` attribute support
- Vite proxy configuration — based on Vite official documentation

### Tertiary (LOW confidence)
- Specific shadcn/ui component RTL behavior after v4 migration — needs empirical validation during implementation
- LiteLLM `acompletion()` parity with `completion()` across all 4 providers — needs testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against npm/PyPI registries
- Architecture: HIGH — React+Vite+FastAPI monorepo is a well-documented pattern
- RTL support: MEDIUM — Radix/Tailwind logical properties are well-documented but need component-level validation
- LiteLLM patterns: HIGH — provider prefixes and `completion()` API verified via official docs
- Pitfalls: HIGH — derived from known RTL challenges and LiteLLM provider quirks

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (30 days — stable ecosystem, no fast-moving dependencies)
