# 024 — Rename push/pull to push_changelog/pull_changelog

## context

`push` and `pull` mislead users and agents into thinking they sync everything
(like Git does). In reality they only move the change log — file blobs require
separate commands. Renaming to `push_changelog`/`pull_changelog` makes the
scope explicit at the call site, improving agent tool-selection accuracy.

## acceptance criteria

- [ ] AC-01: `scholartools.push_changelog()` exists and behaves identically to the old `push()`
- [ ] AC-02: `scholartools.pull_changelog()` exists and behaves identically to the old `pull()`
- [ ] AC-03: `push()` and `pull()` no longer exist in the public API
- [ ] AC-04: `scht sync push-changelog` and `scht sync pull-changelog` are the CLI subcommands
- [ ] AC-05: `scht sync push` and `scht sync pull` no longer exist
- [ ] AC-06: `sync_service.push_changelog()` and `sync_service.pull_changelog()` are the service functions
- [ ] AC-07: All tests updated — no reference to old names remains
- [ ] AC-08: All tests pass

## tasks

- [ ] task-01: rename `push` → `push_changelog` and `pull` → `pull_changelog` in `scholartools/services/sync.py`
- [ ] task-02: update `scholartools/__init__.py` — rename wrappers and update `sync_service.push/pull` call sites
- [ ] task-03: update `scholartools/cli/sync.py` — rename handlers and subcommand strings
- [ ] task-04: update all tests (`tests/unit/cli/test_sync.py`, `tests/unit/test_sync_api.py`, `tests/integration/test_distributed_sync.py`, `tests/integration/test_blob_sync.py`)
- [ ] task-05: update `README.md` — any push/pull command examples
- [ ] task-06: update `docs/remote-setup.md` — any push/pull references
- [ ] task-07: update `docs/feats/009-blob-sync.md` — push/pull references in feature doc
- [ ] task-08: verify full test suite passes

## files in scope

- `scholartools/services/sync.py`
- `scholartools/__init__.py`
- `scholartools/cli/sync.py`
- `tests/unit/cli/test_sync.py`
- `tests/unit/test_sync_api.py`
- `tests/integration/test_distributed_sync.py`
- `tests/integration/test_blob_sync.py`
- `README.md`
- `docs/remote-setup.md`
- `docs/feats/009-blob-sync.md`
