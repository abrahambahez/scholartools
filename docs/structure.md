# structure: loretools

## package layout

The codebase is organized as a core package plus optional plugin packages. Core and plugins may live as siblings in a monorepo or as separate repositories.

```
loretools/                     ← core package (this repo)
  src/loretools/
    __init__.py                   ← public API, sync wrappers, plugin wiring
    models.py                     ← all Pydantic models (core + plugin result types)
    ports.py                      ← Callable type aliases for ALL ports
    config.py                     ← Settings, plugin discovery via entry points
    services/                     ← async domain logic
    adapters/
      local.py                    ← local filesystem adapter (only adapter in core)
    apis/                         ← empty after refactor; all HTTP clients live in plugins

loretools-search/              ← optional plugin
  loretools_search/
    crossref.py
    semantic_scholar.py
    openalexfn.py
    plugin.py                     ← registers adapters under loretools.plugins

loretools-llm/                 ← optional plugin
loretools-cloud/               ← optional plugin
loretools-sync/                ← optional plugin
```

## naming conventions

- modules and files: `snake_case`
- classes and Pydantic models: `PascalCase`
- public functions (agent-facing): `snake_case` verbs — `search_references`, `fetch_reference`, `extract_from_file`
- constants: `UPPER_SNAKE_CASE`
- result types: `{Action}Result` — `SearchResult`, `FetchResult`, `ExtractResult`
- port type aliases: `{Action}{Target}` — `ReadAll`, `WriteAll`, `CopyFile`, `SearchFn`, `FetchFn`
- adapters: named after the backend they implement, not the port — `local.py`, `crossref.py`
- plugin packages (PyPI name): `loretools-{capability}` — `loretools-search`, `loretools-llm`
- plugin packages (import name): `loretools_{capability}` — `loretools_search`
- plugin entry point group: `loretools.plugins`

## layer rules

- **public API** (`__init__.py`): sync wrappers only. Wires config → adapters → services. Discovers and wires plugin adapters via entry points. Returns Result models, never raises. No business logic. No direct imports from plugin packages.
- **services** (`services/`): async, orchestrate domain logic. Never import from `adapters/` or any plugin package directly — receive all dependencies via `LibraryCtx`. Check `Optional` plugin port fields before calling; return `PluginNotAvailable` if `None`. No direct I/O.
- **ports** (`ports.py`): `Callable` type aliases for ALL ports, including plugin-provided ones. No implementation. Defines what plugins must implement. Core and plugin contracts live here.
- **adapters** (`adapters/`): core adapters only — local filesystem operations. No HTTP, no external auth, no network I/O of any kind. No business logic. No cross-adapter imports.
- **apis** (`apis/`): eliminated from core after refactor. This directory may be retained as empty or removed. All HTTP clients belong in plugin packages.
- **models** (`models.py`): pure Pydantic. No I/O, no service calls, no adapter imports. All models defined here — nowhere else. Plugin packages import result types from here; they never define their own.
- **plugins** (external packages): implement optional port contracts from core `ports.py`. May import from `loretools.models` and `loretools.ports`. Must never be imported by core. Own all HTTP calls, external auth, and non-portable dependencies. Register via `loretools.plugins` entry point group.

## portability invariant (enforcement)

Any code in the core package (`src/loretools/`) that imports `httpx`, `anthropic`, or any other network or authentication library is a bug. The rule is absolute. If a feature requires such an import, it belongs in a plugin package — there are no exceptions for convenience.

## test strategy

- **Core unit tests** (`tests/unit/`): mock `LibraryCtx` at the injection boundary. No real I/O, no network, no API keys. No `@pytest.mark.integration` needed — these are always green in any environment, including air-gapped ones.
- **Core adapter test** (`tests/unit/test_local_adapter.py`): tests the local adapter against real `tmp_path` fixtures. No network. Still always green.
- **Core integration tests**: none. Core has no external integrations to test.
- **Plugin integration tests**: each plugin package carries its own `tests/integration/` suite. Skipped by default with `@pytest.mark.integration`. Require network access and any plugin-specific credentials.
