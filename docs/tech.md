# tech: loretools

## stack decisions

### uv for package management
Fast, reliable, PEP-compliant. Replaces pip + virtualenv in one tool. Chosen for speed and lockfile determinism — critical for a library that will be used as a dependency. Each plugin package has its own `pyproject.toml` and lockfile.

### Pydantic for all modeling
Reference objects, result types, config, and API responses are all Pydantic models. No separate domain objects — Pydantic all the way down. Gives typed validation, free JSON serialization, and self-documenting schemas agents can introspect. Plugin packages use core models — they never define their own.

### pdfplumber for PDF extraction
Best-in-class text extraction for structured (text-based) PDFs. Used as the primary extraction path for any PDF with selectable text. This is a **core dependency** — it is local, deterministic, and has no network requirement.

### Anthropic SDK for LLM/vision extraction *(plugin only)*
Fallback for scanned or complex PDFs where pdfplumber yields garbage, and for LLM-assisted knowledge layer operations (synthesis, concept inference). Lives in `loretools-llm` — never imported by core. Core extraction works without it; the fallback path is simply unavailable.

### httpx for external API calls *(plugin only)*
Async-native HTTP client. Used by plugin packages (`loretools-search`, `loretools-cloud`, `loretools-sync`) for their external calls. **Core has no httpx dependency.** This is the portability invariant made concrete: if a module imports httpx, it belongs in a plugin.

### pytest for testing
Standard. Core unit tests mock at port boundaries and require no network, no API keys, no integration markers — they are always green in any environment. Plugin packages carry their own `tests/integration/` suites, skipped by default with `@pytest.mark.integration`.

## architecture

loretools uses **Hexagonal Architecture** (Ports & Adapters) implemented in **functional Python style** — no service classes, no OOP inheritance. The domain core is pure Pydantic data. All logic lives in module-level functions.

The architecture has a hard boundary between **core** and **plugins**:

- **Core** (`loretools` package): all local, deterministic operations. Zero network dependencies. Zero external authentication. Ships as a standalone installable that is fully useful in isolation.
- **Plugins** (separate packages): optional adapters for external services, cloud backends, and LLM operations. They implement port contracts defined in core. Core never imports from plugins.

```
  [agent: direct function calls]
              ↓
  ┌───────────────────────────────────────────────┐  ← loretools (core)
  │           PUBLIC API  (__init__.py)            │
  │   sync wrappers · result types · plugin wiring │
  └──────────────────┬────────────────────────────┘
                     ↓
  ┌───────────────────────────────────────────────┐
  │         SERVICES  (services/)                  │
  │   async functions · receive LibraryCtx         │
  └──────┬────────────────────────┬───────────────┘
         ↓                        ↓
  ┌─────────────────┐    ┌──────────────────────────────┐
  │  CORE PORTS     │    │  PLUGIN PORTS                │
  │  (ports.py)     │    │  Optional[PluginPort] = None │
  └──────┬──────────┘    └──────────────┬───────────────┘
         ↓                              ↓ (None if plugin not installed)
  ┌─────────────────┐    ╔══════════════════════════════════╗
  │  LOCAL ADAPTERS │    ║  PLUGIN ADAPTERS (ext. packages) ║
  │  adapters/      │    ║  loretools-search             ║
  └─────────────────┘    ║  loretools-llm                ║
                         ║  loretools-cloud              ║
                         ║  loretools-sync               ║
                         ╚══════════════════════════════════╝
```

### functional style — no service classes

Services are **modules of functions**, not classes. Adapters are **modules of functions** that match port `Callable` type aliases. No `__init__`, no `self`.

### dependency injection via LibraryCtx

`LibraryCtx` is a Pydantic model holding references to the active adapter functions. Core ports are required fields; plugin ports are `Optional` fields defaulting to `None`. Services check plugin port availability before calling and return `PluginNotAvailable` if the required plugin is not installed.

The public API wires `LibraryCtx` lazily from config on first call. Plugin adapters are discovered via Python entry points under the `loretools.plugins` group — if a plugin package is installed, its adapters are registered automatically. Agents never see `LibraryCtx`.

### result types at the public boundary

Every public function returns a typed Result model — never raises. Agents read results; they don't catch exceptions. Non-fatal per-source errors surface in `errors: list[str]` fields, not exceptions. `PluginNotAvailable` is a result, not an exception.

### async-first services, sync public API

Service functions are `async def` — enabling parallel fan-out (e.g., a search plugin querying multiple sources via `asyncio.gather()`). Public functions in `__init__.py` are sync wrappers using `asyncio.run()`. Callers who want async can import from `loretools.services` directly and pass their own `ctx`.

### portability invariant

The core package must run identically on any machine that can run Python, regardless of network access, authentication state, or environment. This invariant is enforced by the rule: **if a module imports `httpx`, `anthropic`, or any other network/auth dependency, it belongs in a plugin package, not core.** There are no exceptions.

## ADRs

- ADR-001: hexagonal architecture with result types at public boundary — docs/adr/001-hexagonal-result-types.md
- ADR-002: pdfplumber + LLM vision as two-stage PDF extraction — docs/adr/002-pdf-extraction.md
- ADR-003: httpx over requests for async-first HTTP — docs/adr/003-httpx.md
- ADR-004: Pydantic for all modeling, no separate domain objects — docs/adr/004-pydantic-all-the-way.md
- ADR-005: plugin architecture — portability invariant and epistemological neutrality — docs/adr/005-plugin-architecture.md
