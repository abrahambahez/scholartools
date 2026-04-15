# spec: 013-ruff-fixes — eliminate all 28 pre-existing ruff errors

## findings

28 errors across 5 categories, all pre-existing before CLI work. Root causes:

| code | count | root cause |
|------|-------|-----------|
| F401 | 9 | `__init__.py` imports models for re-export but doesn't declare them as such |
| E501 | 12 | long strings/comments in source and test files exceed 88-char limit |
| F841 | 7 | dead variable assignments never read after creation |
| F821 | 1 | `compute_uid` called in `services/merge.py` but never imported |
| E741 | 1 | variable named `l` in `services/extract.py` (ambiguous: looks like `1` or `I`) |

## objective

Zero ruff errors. Each fix addresses the root cause of the error.

## fixes by category

### F401 — `scholartools/__init__.py` (9 imports)
`DeviceIdentity`, `FileRow`, `LinkResult`, `PeerRecord`, `PeerSettings`, `ReferenceRow`, `SyncConfig`, `UnlinkResult`, `VerifyEntryResult` are intentional public re-exports. Ruff cannot infer intent without explicit syntax.
**Fix:** append `as X` to each import (`LinkResult as LinkResult`, etc.) — PEP 484 explicit re-export convention.

### E501 — line too long (12 occurrences)
Long error message strings, docstrings, and comments across `__init__.py`, `config.py`, `citekeys.py`, `merge.py`, `peers.py`, `extract.py`, `scripts/bootstrap_identity.py`, and test files.
**Fix:** wrap each line. For string literals use implicit concatenation; for comments use line continuation.

### F841 — unused variable assignments (7 occurrences)
- `base` in `adapters/local.py:62` — assigned `Path(files_dir)` but inner closures use `files_dir` directly; dead code
- `known` in `services/merge.py:23` — computed set never read after assignment
- `ts1`, `ts2`, `before_counter` in `tests/unit/test_hlc.py` — intermediate values assigned but not asserted on
- `mock_upload`, `result` in `tests/unit/test_sync_service.py` — patch target and return value captured but never checked

**Fix:** remove each dead assignment. For test variables: if the value is needed to verify behavior, add an assertion; if not, drop the assignment. These are dead code, not suppressed assertions.

### F821 — `compute_uid` undefined in `services/merge.py:105`
`compute_uid` is called but no import is present. The function lives in `services/uid.py` (introduced in feature #006-deduplication). The import was dropped at some point.
**Fix:** add `from scholartools.services.uid import compute_uid` to `merge.py`.

### E741 — ambiguous variable name `l` in `services/extract.py:56`
A loop or assignment uses `l` as a variable name.
**Fix:** rename to a descriptive name based on what the variable holds.

## tasks

- [x] task-01: fix F821 — add missing `compute_uid` import in `merge.py` (blocks: none)
- [x] task-02: fix F401 — add explicit re-export syntax to `__init__.py` (blocks: none)
- [x] task-03: fix F841 + E741 — remove dead assignments, rename `l` (blocks: none)
- [x] task-04: fix E501 — wrap all long lines (blocks: none)
- [x] task-05: verify — `uv run ruff check .` outputs zero errors; `uv run pytest` still green (blocks: task-01, task-02, task-03, task-04)

## ADR required?

No.

## risks

F821 is the only one with runtime consequence — `compute_uid` is called in a real code path in `merge.py`. The other errors are style/intent. Test changes only remove dead variable assignments; no assertions are modified.
