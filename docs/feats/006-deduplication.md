# 006: deduplication — uid-based record identity

## context

The uid design is specified in full in `docs/rfc/001-distributed-sync.md` (record identity section). This feat covers what changes in the codebase to implement it: model, generation, and dedup.

## what changes

### `Reference` model (`models.py`)

Two new required fields:

```python
uid: str
uid_confidence: Literal["authoritative", "semantic"]
```

### uid generation (`services/uid.py`)

New module with a single public function:

```python
def compute_uid(ref: Reference) -> tuple[str, Literal["authoritative", "semantic"]]
```

Implements the tier-1 → tier-2 cascade from the RFC. Normalization rules (`normalize_text`, `normalize_isbn`) live here and match the RFC spec exactly.

Called by `stage_reference()` immediately after CSL-JSON normalization. uid is written into the staged record and never recomputed.

### dedup (`services/duplicates.py`)

`is_duplicate()` matches on uid only — the existing normalized-title + ISBN logic is removed.

### migration (`scripts/backfill_uid.py`)

One-time script to backfill `uid` and `uid_confidence` on existing library and staging records. Reads `library.json` and `staging.json`, computes uid for each record using `compute_uid`, writes back in place.

## out of scope

- cross-peer merge using uid (sync feature, RFC phase 1)
