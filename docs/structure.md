# structure: scholartools

## naming conventions

- modules and files: `snake_case`
- classes and Pydantic models: `PascalCase`
- public functions (agent-facing): `snake_case` verbs — `search_references`, `fetch_reference`, `extract_from_file`
- constants: `UPPER_SNAKE_CASE`
- result types: `{Action}Result` — `SearchResult`, `FetchResult`, `ExtractResult`
- port type aliases: `{Action}{Target}` — `ReadAll`, `WriteAll`, `CopyFile`, `SearchFn`, `FetchFn`
- adapters: named after the backend they implement, not the port — `local.py`
- api clients: named after the external service — `crossref.py`, `semantic_scholar.py`

## layer rules

- **public API** (`__init__.py`): sync wrappers only. Wires config → adapters → services. Returns Result models, never raises. No business logic.
- **services** (`services/`): async, orchestrate domain logic. Never import from `adapters/` or `apis/` directly — receive them as injected dependencies via `LibraryCtx`. No direct I/O.
- **ports** (`ports.py`): `Callable` type aliases only. No implementation. No imports from adapters or apis.
- **adapters** (`adapters/`): implement port contracts. Own all filesystem I/O. No business logic. No cross-adapter imports.
- **apis** (`apis/`): own HTTP calls and response normalization to CSL-JSON dicts. No storage access. All HTTP via httpx.
- **models** (`models.py`): pure Pydantic. No I/O, no service calls, no adapter imports. All models defined here — nowhere else.

## test strategy

- unit tests mock ctx at the injection boundary — no real I/O, no network
- `tests/unit/test_local_adapter.py` is the exception: tests the local adapter against real `tmp_path` fixtures
- integration tests in `tests/integration/` are opt-in, skipped by default: `pytest --run-integration`
