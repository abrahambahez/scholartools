# spec 005: configurable citekeys

## objective

Add optional `citekey` config block to `config.json` with pattern-based composition and disambiguation strategy selection, allowing researchers to match their existing naming conventions. Validation occurs at config load time. Changes are confined to `models.py`, `config.py`, and `citekeys.py`. Net code change is roughly neutral.

## acceptance criteria

- WHEN `config.json` omits the `citekey` block, the system MUST use defaults (`pattern="{author[2]}{year}"`, `separator="_"`, `etal="_etal"`, `disambiguation_suffix="letters"`) and reproduce current behavior exactly
- WHEN `CitekeySettings` is loaded, the system MUST validate all fields at config load time and raise `ValueError` on invalid pattern tokens, out-of-range separator/etal characters, or unknown `disambiguation_suffix`
- WHEN `generate(ref, settings)` is called, the system MUST parse the pattern, evaluate `{author[N]}` and `{year}` tokens against CSL-JSON metadata, and join author names with `separator`
- WHEN `{author[N]}` is evaluated and author count > N, the system MUST include the first author and append the configured `etal` string
- WHEN `{author[N]}` is evaluated and author count <= N, the system MUST include all author family names joined by `separator`
- WHEN author or year is missing after evaluation, the system MUST fall back to `ref{uuid6}` (unchanged)
- WHEN `resolve_collision(key, existing, settings)` is called with `disambiguation_suffix="letters"`, the system MUST append `a`, `b`, ..., `z`, `aa`, `ab`, ... (unchanged)
- WHEN `resolve_collision` is called with `disambiguation_suffix="title[N]"`, the system MUST append N significant words from the reference title on collision; WHEN title is missing or insufficient, it MUST fall back to letter suffixes
- WHEN `separator` or `etal` contain characters outside `[a-z0-9_-]`, or exceed length limits (3 and 8 respectively), the system MUST raise `ValueError` at config load
- WHEN a pattern contains unknown tokens, the system MUST raise `ValueError` at config load, not at runtime
- WHEN existing tests run against default settings, they MUST all pass without modification

## tasks

- [ ] task-01: add `CitekeySettings` Pydantic model to `models.py` with field validators for `pattern`, `separator`, `etal`, `disambiguation_suffix` (blocks: none)
- [ ] task-02: embed `CitekeySettings` in `Settings` as optional field with default factory; no change to `_REQUIRED_KEYS` (blocks: task-01)
- [ ] task-03: rewrite `citekeys.py`: `generate(ref, settings)` with flat token parser for `{author[N]}` and `{year}`; preserve `_normalize`, `_family`, `_issued_year` helpers (blocks: task-01)
- [ ] task-04: update `resolve_collision(key, existing, settings)` to dispatch on `disambiguation_suffix`; implement title-word extraction for `title[N]` mode with letter fallback (blocks: task-03)
- [ ] task-05: update all call sites (`services/store.py`, `services/merge.py`) to pass `settings` to `generate` and `resolve_collision` (blocks: task-03, task-04)
- [ ] task-06: extend `tests/unit/test_citekeys.py` with: custom separator, custom etal, author count edge cases, title disambiguation, config validation errors (blocks: task-03, task-04)
- [ ] task-07: run full test suite; confirm no regressions on default config (blocks: task-05, task-06)

## risks

- **Title "significant words"**: no stop-word list specified — use a minimal heuristic (skip articles: a, an, the, de, el, la) and lowercase+normalize same as author names
- **Pattern validation timing**: token parsing must run inside a Pydantic validator on `CitekeySettings`, not lazily in `generate()`
- **Call site coverage**: grep for all `citekeys.generate` and `citekeys.resolve_collision` usages before task-05 to avoid missing a call site
