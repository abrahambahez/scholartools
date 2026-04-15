# spec: 006-deduplication

## objective

Add uid computation and uid-based deduplication to scholartools. This establishes the stable identity layer required by the distributed sync protocol (RFC-001 phase 1). Changes are confined to three modules: model layer (two new fields), services layer (uid generation and dedup), and a one-time backfill script. The feature is transparent to public API users — uids are assigned automatically at intake and never exposed in the function signatures.

## acceptance criteria

- WHEN a reference enters staging (via `stage_reference()`), the system MUST compute `uid` and `uid_confidence` using `compute_uid()` before writing to staging
- WHEN `compute_uid()` evaluates a reference, the system MUST check tier-1 identifiers in order (DOI → arXiv → ISBN) and return the first non-null tier-1 uid with confidence `"authoritative"`
- WHEN no tier-1 identifier is present, the system MUST compute a tier-2 uid from canonical fields (normalized title, year, first author family, type) with confidence `"semantic"`
- WHEN `compute_uid()` normalizes text, the system MUST apply Unicode NFC, lowercase, remove Unicode punctuation/symbols (categories P* and S*), collapse whitespace, and strip leading/trailing space — matching RFC-001 spec exactly
- WHEN `compute_uid()` normalizes ISBN, the system MUST strip hyphens/spaces and convert ISBN-10 to ISBN-13
- WHEN required fields for tier-2 are missing, the system MUST derive uid from available canonical fields; confidence remains `"semantic"`
- WHEN `is_duplicate()` is called, the system MUST match on uid only; the existing normalized-title + ISBN logic is removed
- WHEN `uid_confidence` is `"semantic"`, the merge service MUST reject promotion and return an error requiring explicit confirmation (e.g., caller passes `allow_semantic=True`)
- WHEN the backfill script runs, the system MUST compute uid for all records missing the field and write them back in place; the script MUST be idempotent

## tasks

- [x] task-01: add `uid: str` and `uid_confidence: Literal["authoritative", "semantic"]` to `Reference` in `models.py` (blocks: none)

- [x] task-02: create `services/uid.py` with `compute_uid(ref: Reference) -> tuple[str, Literal["authoritative", "semantic"]]` and private helpers `_normalize_text()`, `_normalize_isbn()` (blocks: task-01)

- [x] task-03: call `compute_uid()` inside `stage_reference()` before writing to staging; never recompute if uid already present (blocks: task-02)

- [x] task-04: rewrite `is_duplicate()` in `services/duplicates.py` to match on uid only; remove title and ISBN logic (blocks: task-02)

- [x] task-05: gate semantic-confidence records in `merge()` — return error unless `allow_semantic=True` (blocks: task-02)

- [x] task-06: create `scripts/backfill_uid.py` with `--dry-run` and `--verbose` flags; idempotent (blocks: task-02)

- [x] task-07: full test suite green; update any tests that assumed old dedup logic (blocks: task-03, task-04, task-05, task-06)

## risks

- **Normalization is immutable once shipped.** Any future change to `_normalize_text()` invalidates all existing tier-2 uids across all peers. Treat as a versioned spec.
- **Breaking model change.** `uid` and `uid_confidence` are required fields — backfill script must be run before upgrading any library that will participate in sync.
- **Backfill ordering.** Must run before the first sync push. Document as a sync bootstrap prerequisite.
