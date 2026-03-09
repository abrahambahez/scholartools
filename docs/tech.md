# tech: scholartools

## stack decisions

### uv for package management
Fast, reliable, PEP-compliant. Replaces pip + virtualenv in one tool. Chosen for speed and lockfile determinism — critical for a library that will be used as a dependency.

### Pydantic for all modeling
Reference objects, result types, config, and API responses are all Pydantic models. No separate domain objects — Pydantic all the way down. Gives typed validation, free JSON serialization, and self-documenting schemas agents can introspect.

### pdfplumber for PDF extraction
Best-in-class text extraction for structured (text-based) PDFs. Used as the primary extraction path for any PDF with selectable text.

### Anthropic SDK for LLM/vision extraction
Fallback for scanned or complex PDFs where pdfplumber yields garbage. Claude accepts PDFs natively via the vision API — no separate OCR dependency. Also handles semantic inference (ambiguous author order, non-standard title pages).

### httpx for external API calls
Async-native, API-compatible with requests. Chosen because services are async-first and frequently fan out across multiple sources simultaneously (Crossref + Semantic Scholar + ArXiv in parallel).

### pytest for testing
Standard. Unit tests mock at port boundaries. Integration tests are opt-in (skipped by default, require network + API keys).

## architecture

scholartools uses **Hexagonal Architecture** (Ports & Adapters) implemented in **functional Python style** — no service classes, no OOP inheritance. The domain core is pure Pydantic data. All logic lives in module-level functions.

```
  [agent: direct function calls]   [future: MCP server, REST API]
              ↓                               ↓
       ┌──────────────────────────────────────────┐
       │         PUBLIC API  (src/scholartools/)       │
       │   sync wrappers · result types · wiring   │
       └──────────────────┬───────────────────────┘
                          ↓
       ┌──────────────────────────────────────────┐
       │      SERVICES  (src/scholartools/services/)   │
       │  modules of async functions · take LibraryCtx  │
       └──────┬───────────────────────────┬────────┘
              ↓                           ↓
       ┌─────────────┐           ┌────────────────┐
       │    PORTS    │           │      PORTS     │
       │  (Callable  │           │   (Callable    │
       │  type hints)│           │   type hints)  │
       └──────┬──────┘           └───────┬────────┘
              ↓                          ↓
   ┌──────────────────┐      ┌───────────────────────┐
   │    ADAPTERS      │      │     API CLIENTS       │
   │  adapters/       │      │  apis/                │
   └──────────────────┘      └───────────────────────┘
```

### functional style — no service classes

Services are **modules of functions**, not classes. Adapters are **modules of functions** that match port `Callable` type aliases. No `__init__`, no `self`.

### dependency injection via LibraryCtx

`LibraryCtx` is a Pydantic model holding references to the active adapter functions. Services receive it as a parameter. The public API wires it lazily from config on first call — agents never see it. Tests inject a different ctx directly — no monkeypatching needed.

### result types at the public boundary

Every public function returns a typed Result model — never raises. Agents read results; they don't catch exceptions. Non-fatal per-source errors surface in `errors: list[str]` fields, not exceptions.

### async-first services, sync public API

Service functions are `async def` — enabling parallel fan-out across APIs via `asyncio.gather()`. Public functions in `__init__.py` are sync wrappers using `asyncio.run()`. Callers who want async can import from `scholartools.services` directly and pass their own `ctx`.

## ADRs

- ADR-001: hexagonal architecture with result types at public boundary — docs/adr/001-hexagonal-result-types.md
- ADR-002: pdfplumber + LLM vision as two-stage PDF extraction — docs/adr/002-pdf-extraction.md
- ADR-003: httpx over requests for async-first HTTP — docs/adr/003-httpx.md
- ADR-004: Pydantic for all modeling, no separate domain objects — docs/adr/004-pydantic-all-the-way.md
