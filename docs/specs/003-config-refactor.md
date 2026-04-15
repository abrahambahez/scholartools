# spec: 003-config-refactor

## objective

Simplify configuration by establishing a single authoritative config file at
`~/.config/scholartools/config.json` for all behavior settings, and moving all
API keys exclusively to environment variables. The config file is mandatory — if
absent on first load, the library creates it with defaults. Introduce a single
`library_dir` setting that owns all library-related paths — preparing for
002-staging-workflow.

## current state

- Config lookup chain: `SCHOLARTOOLS_CONFIG` env var → `.scholartools/config.json` → `~/.config/scholartools/config.json`
- `api_key` lives inside `SourceConfig`; `anthropic_api_key` inside `LlmSettings` — both can be stored in the config file
- Separate `library_path` (file) and `files_dir` settings — no unified library root
- Ad-hoc env var overrides: `SCHOLARTOOLS_LIBRARY_PATH`, `SCHOLARTOOLS_FILES_DIR`

## target state

- Single config location: `~/.config/scholartools/config.json` — mandatory, created with defaults on first run
- No `SCHOLARTOOLS_CONFIG`, no local `.scholartools/config.json` lookup
- API keys strictly from env vars: `ANTHROPIC_API_KEY`, `GBOOKS_API_KEY`
- `api_key` and `anthropic_api_key` removed from all Pydantic models
- `library_path` + `files_dir` replaced by a single `library_dir` (default: `~/.local/share/scholartools`)
- All library files derived from `library_dir`:
  - `{library_dir}/library.json` — main library
  - `{library_dir}/files/` — archived PDFs/ebooks
  - `{library_dir}/staging.json` — (reserved for 002-staging-workflow)
  - `{library_dir}/staging/` — (reserved for 002-staging-workflow)
- `reset_settings()` retained for test isolation

## directory layout (post-refactor)

```
{library_dir}/          # configurable, defaults to ~/.local/share/scholartools
  library.json
  files/
  staging.json          # future
  staging/              # future
```

## acceptance criteria

- WHEN no config file exists, MUST create `~/.config/scholartools/config.json` with default values (creating parent dirs as needed), then load it.
- WHEN `~/.config/scholartools/config.json` exists, MUST read and validate it — no merging with defaults for missing fields; the file is the source of truth.
- WHEN `library_dir` is set in config, MUST use it as root for all derived paths.
- WHEN `library_dir` is absent from config, MUST default to `~/.local/share/scholartools`.
- WHEN `ANTHROPIC_API_KEY` env var is set, MUST use it for LLM extraction.
- WHEN `GBOOKS_API_KEY` env var is set, MUST use it for Google Books API.
- WHEN neither key env var is set, MUST disable the respective service without error.
- WHEN `reset_settings()` is called, MUST clear cached settings; next access reloads from disk/env.
- WHEN config file contains an `api_key` or `anthropic_api_key` field, MUST raise a Pydantic validation error (extra="forbid").
- WHEN `SCHOLARTOOLS_CONFIG`, `SCHOLARTOOLS_LIBRARY_PATH`, or `SCHOLARTOOLS_FILES_DIR` env vars are set, MUST ignore them silently.

## tasks

- [ ] task-01: update Settings models in config.py
  - Remove `api_key` from `SourceConfig`; add `extra="forbid"`
  - Remove `anthropic_api_key` from `LlmSettings`; add `extra="forbid"`
  - Replace `LocalSettings.library_path` + `LocalSettings.files_dir` with `library_dir: Path`
  - Add derived properties `library.json`, `files_dir` computed from `library_dir`
  - Default `library_dir` to `~/.local/share/scholartools`

- [ ] task-02: simplify load_settings() and remove _find_config()
  - Config path is a constant: `~/.config/scholartools/config.json`
  - If absent, write defaults to disk, then load
  - Remove all env var overrides except `ANTHROPIC_API_KEY` and `GBOOKS_API_KEY`
  - Read API keys from env at load time, pass to callers — do not store on models

- [ ] task-03: update __init__.py context builder
  - `_build_ctx()` reads API keys directly from `os.environ`
  - Pass to `make_*()` adapter factories; handle `None` gracefully (disable service)

- [ ] task-04: update tests
  - Update `test_config.py` to reflect new model shape and single config path
  - Add test: config file with `api_key` field raises `ValidationError`
  - Add test: when config absent, file is created on disk with defaults and then loaded
  - Add test: `library_dir` derives correct `library.json` and `files_dir` paths
  - Use `monkeypatch` for env vars in all API key tests

## risks

1. **Breaking change for existing users**: config files with `api_key`/`anthropic_api_key` will now raise on load. Mitigation: document migration in CHANGELOG.
2. **`library_dir` default changes existing path**: users relying on relative `library.json` will need to migrate. Mitigation: note in CHANGELOG; keep old path as documented alternative in config.
3. **002-staging-workflow dependency**: this spec reserves `staging.json` and `staging/` inside `library_dir` but does not implement them. Do not implement staging logic here.

## notes

- `library_dir` is a soft blocker for 002-staging-workflow — that spec must derive its paths from `Settings.library_dir`
- ADR recommended: document why `library_dir` unifies library root and why API keys are env-only
