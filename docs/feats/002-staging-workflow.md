# feat 002: staging workflow

version: 0.1
status: draft

## problem

The current library is single-state: every ingested reference is immediately a committed record. This does not match how research actually works. Exploration is iterative — references are gathered before their value is known, evaluated during reading, and only a subset earns a permanent place in the library. Without a staging layer, the library accumulates noise and the human must curate manually.

The original bib-file workflow had this problem: no QA gate meant the file drifted messy over time. CSL-JSON solves format drift, but only if normalization happens at the point of intake, not at commit time.

## the workflow this feature replicates

```
[external source / local PDF]
        ↓
    stage()           ← normalize to CSL-JSON immediately
        ↓
  [evaluate: read, annotate, discard or keep]
        ↓               ← iterative, not sequential
    merge()           ← QA gate: validate schema, detect duplicates,
        ↓                 archive file, assign citekey
   [library]          ← production, ground truth
        ↓
   export()           ← pandoc / Word XML / Google Docs XML
```

Staging and reading are interleaved: new references surface during reading and re-enter staging. The cycle repeats until writing begins, at which point all needed references must be in the library.

## two-store model

**Staging store** (`~/.scholartools/staging.json`)
- CSL-JSON records with an added `_stage` metadata block
- `_stage.status`: `new` | `reading` | `accepted` | `rejected`
- `_stage.added_at`: ISO timestamp
- `_stage.source`: how it entered (`doi`, `isbn`, `arxiv`, `pdf`, `freeform`)
- No citekey — citekeys are assigned at merge time
- Files live in `~/.scholartools/staging/` (unconverted, as received)

**Library store** (`~/.scholartools/library.json`)
- Current production store — unchanged
- Full CSL-JSON records with assigned citekeys
- Files live in `~/.scholartools/files/`

## merge/QA gate

`merge(citekeys?)` promotes staged records with `status: accepted` (or a provided list) through:

1. **Schema validation** — required CSL-JSON fields present and typed correctly
2. **Duplicate detection** — check against library by DOI, title similarity, or existing citekey
3. **File archival** — if a staging file exists, move it to `~/.scholartools/files/` and update the record's `URL` or `note` field
4. **Citekey assignment** — generate and assign a citekey if absent
5. **Promotion** — write to library, remove from staging

On any QA failure, the record stays in staging with `_stage.qa_errors` populated. The agent surfaces these to the human and waits for resolution.

## export

`export(format, citekeys?)` serializes library records (or a subset) for writing tools:
- `pandoc` — CSL-JSON passthrough, already valid
- `word` — OOXML bibliography XML (`<b:Sources>` schema)
- `googledoc` — Google Docs citation XML

Export is read-only and does not modify the library.

## open questions

1. Should staging support bulk status update (`mark_accepted(filter)`) or only per-record? The iterative reading pattern suggests bulk is important.
2. Does the staging store need a separate adapter, or is it the same adapter as the library with a different path? Preference: same adapter, different path — avoids duplication.
3. PDF-to-text conversion for the reading phase: is this in scope for scholartools or handled by the reading skills layer above it? Tentative answer: out of scope for this feature, the reading skills call scholartools only for staging/merge.
4. Should `merge` be callable without arguments (merge all accepted) or require explicit selection? Safer default: require explicit citekey list or status filter — prevents accidental bulk promotion.

## impact on MCP tool contract

The 5-tool proposal from the MCP design session predates this feature. With staging:
- `add_reference` → writes to staging by default, not library
- A new `merge_references` tool is needed (or `add_reference` gets a `target` parameter)
- `find_references` needs a `store` parameter to disambiguate staging vs library queries
- `audit_library` should optionally include a staging summary

The MCP contract should not be finalized until this feature is specced and approved.
