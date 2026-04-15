# feat 002: staging workflow

version: 0.5
status: current

## problem

The current library is single-state: every ingested reference is immediately a committed record. This does not match how research actually works. Exploration is iterative — references are gathered before their value is known, evaluated during reading, and only a subset earns a permanent place in the library. Without a staging layer, the library accumulates noise and the human must curate manually.

## the workflow this feature replicates

```
[external source / local PDF]
        ↓
    stage()           ← normalize to CSL-JSON, assign citekey immediately
        ↓
  [evaluate: read, annotate, discard or keep]
        ↓               ← iterative, not sequential
    merge()           ← QA gate: normalize, detect duplicates,
        ↓                 validate schema, archive file
   [library]          ← production, ground truth
```

Staging and reading are interleaved: new references surface during reading and re-enter staging. The cycle repeats until writing begins, at which point all needed references must be in the library.

## two-store model

Both stores use the same `Reference` model — no schema changes. Status is implicit from location: records in `staging.json` are staged; records in `library.json` are production. Files follow the same rule.

**Staging store** (`~/.scholartools/staging.json`)
- Same `Reference` schema as the library — citekey assigned at stage time
- Files live in `~/.scholartools/staging/`

**Library store** (`~/.scholartools/library.json`)
- Current production store — unchanged
- Files live in `~/.scholartools/files/`

Same adapter, different path — no separate adapter needed.

## merge/QA gate

`merge(omit?)` promotes all staged records by default; pass an optional list of citekeys to skip. Steps run per record:

1. **Normalization** — translate fields from other conventions (BibTeX, RIS, etc.) to CSL-JSON; strip non-CSL fields
2. **Duplicate detection** — check against library by normalized title or ISBN (see below)
3. **Schema validation** — required CSL-JSON fields present and typed correctly
4. **File archival** — if a staging file exists, rename it to `{citekey}.{ext}` and copy to `~/.scholartools/files/`; original staging file deleted after promotion
5. **Promotion** — write to library, remove from staging

Errors are transient — returned in the `MergeResult` but never persisted. A record that fails any step is not promoted and stays in staging. The agent surfaces errors and the human must fix or delete the record. No stored error state, no `qa_errors` field on `Reference`.

## duplicate detection

> **Updated in feat 006 (v0.7):** Duplicate detection is now uid-based. The normalized-title + ISBN logic described below has been replaced.

A staged record is a duplicate if its `uid` matches an existing library record's `uid`. UIDs are computed by `services/uid.py` using a tier-1 → tier-2 cascade:

- **Tier 1 (authoritative):** `uid_confidence = "authoritative"` — derived from DOI, arXiv ID, or ISBN-13. Exact match only.
- **Tier 2 (semantic):** `uid_confidence = "semantic"` — derived from a normalized title + first-author hash. Merge is gated on `allow_semantic=True` to prevent accidental promotions.

UIDs are assigned once at `stage_reference()` time and never recomputed.

## decisions

- `merge()` is bulk by default; `omit` is the exception — matches the organic multi-record nature of staging
- `list_staged(page=1)` returns `ReferenceRow` projections, sorted by citekey ascending, 10 per page — same contract as `list_references`. Use `get_reference` for the full staged record.
- PDF-to-text conversion: out of scope — the reading skills layer calls scholartools only for staging/merge
