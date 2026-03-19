# scholartools

Reference management library built for AI agents. Local-first, no GUI, no human workflows — clean functions an agent can call with confidence.

## install

macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/abrahambahez/scholartools/main/install.sh | bash
```

Windows (elevated PowerShell):

```powershell
irm https://raw.githubusercontent.com/abrahambahez/scholartools/main/install.ps1 | iex
```

Re-running the script updates the binary in place.

## config

Config is loaded from `~/.config/scholartools/config.json`. If the file doesn't exist it is created automatically with defaults.

```json
{
  "backend": "local",
  "local": {
    "library_dir": "~/.local/share/scholartools"
  },
  "apis": {
    "email": "you@example.com",
    "sources": [
      { "name": "crossref", "enabled": true },
      { "name": "semantic_scholar", "enabled": true },
      { "name": "arxiv", "enabled": true },
      { "name": "openalex", "enabled": true },
      { "name": "doaj", "enabled": true },
      { "name": "google_books", "enabled": true }
    ]
  },
  "llm": {
    "model": "claude-sonnet-4-6"
  }
}
```

When `sync` is configured, a `peer` block is also required (see [peer identity & distributed sync](#peer-identity--distributed-sync) below).

`library_dir` controls where `library.json`, `files/`, and `staging/` are stored. All other paths are derived from it.

Set `apis.email` to identify your requests to Crossref and OpenAlex (recommended — unlocks polite-pool rate limits).

API keys are never stored in config — set them as environment variables:

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | No | PDF metadata extraction via Claude vision (fallback when pdfplumber fails) |
| `GBOOKS_API_KEY` | No | Enables Google Books as a search/fetch source |
| `SEMANTIC_SCHOLAR_API_KEY` | No | Raises Semantic Scholar rate limits |

Without these keys the features degrade gracefully: LLM extraction is skipped, Google Books source is disabled.

## CLI

`scht` is a full command-line interface that mirrors every public API function. All commands output JSON envelopes for agent consumption.

```bash
# references
scht refs add '{"type":"article-journal","title":"...","author":[{"family":"Smith"}],"issued":{"date-parts":[[2020]]}}'
scht refs get --citekey vaswani2017
scht refs update vaswani2017 '{"note":"foundational"}'
scht refs rename vaswani2017 vaswani_etal2017
scht refs delete vaswani2017
scht refs list
scht refs filter --query attention --year 2017

# discover / fetch / extract
scht discover "transformer attention mechanism" --limit 5
scht fetch 10.48550/arXiv.1706.03762
scht extract papers/vaswani2017.pdf

# file archive
scht files link vaswani2017 papers/vaswani2017.pdf
scht files unlink vaswani2017
scht files get vaswani2017
scht files move vaswani2017 attention.pdf
scht files list

# staging
scht staging stage '{"title":"..."}' --file papers/draft.pdf
scht staging list
scht staging delete draft2024
scht staging merge
scht staging merge --omit draft2024

# sync
scht sync push
scht sync pull
scht sync snapshot
scht sync conflicts
scht sync resolve <uid> title "Corrected Title"
scht sync restore vaswani2017

# peers
scht peers init alice laptop
scht peers register-self
scht peers register alice '{"peer_id":"alice","device_id":"laptop","pubkey_hex":"..."}'
scht peers add-device bob '{"peer_id":"bob","device_id":"phone","pubkey_hex":"..."}'
scht peers revoke-device bob old-tablet
scht peers revoke bob
```

Every command exits 0 on success, 1 on error; JSON is always written to stdout.

## usage (Python API)

```python
import scholartools

# discover references from external sources (Crossref, Semantic Scholar, arXiv, OpenAlex, DOAJ, Google Books)
result = scholartools.discover_references("transformer attention mechanism", limit=5)

# fetch full record by DOI, arXiv ID, or ISSN
result = scholartools.fetch_reference("10.48550/arXiv.1706.03762")

# extract metadata from a local PDF
result = scholartools.extract_from_file("papers/vaswani2017.pdf")

# CRUD
scholartools.add_reference({"type": "article-journal", "title": "Attention Is All You Need", ...})
scholartools.get_reference("vaswani2017")
scholartools.update_reference("vaswani2017", {"note": "foundational"})
scholartools.rename_reference("vaswani2017", "vaswani_etal2017")
scholartools.delete_reference("vaswani2017")
scholartools.list_references(page=1)

# filter local library
scholartools.filter_references(query="attention")               # title substring
scholartools.filter_references(author="vaswani", year=2017)     # field predicates (ANDed)
scholartools.filter_references(ref_type="book", has_file=True)  # type and file presence
scholartools.filter_references(query="draft", staging=True)     # search staging store instead

# file archive
scholartools.link_file("vaswani2017", "papers/vaswani2017.pdf")
scholartools.unlink_file("vaswani2017")
scholartools.move_file("vaswani2017", "attention.pdf")
scholartools.list_files(page=1)

# staging — review before committing to the library
scholartools.stage_reference({"title": "..."}, file_path="papers/draft.pdf")
scholartools.list_staged(page=1)
scholartools.delete_staged("draft2024")
scholartools.merge()                    # moves all staged refs into the main library
scholartools.merge(omit=["draft2024"]) # skip specific citekeys
```

Every function returns a typed Result model — never raises.

## peer identity & distributed sync

```python
import scholartools

# initialise a local peer identity (generates Ed25519 keypair)
scholartools.peer_init(peer_id="alice", device_id="laptop")

# bootstrap admin on an empty peer directory (first-time setup)
scholartools.peer_register_self()

# register another peer (requires admin role)
scholartools.peer_register(peer_id="bob", pubkey_hex="<hex>")

# device lifecycle
scholartools.peer_add_device(peer_id="bob", device_id="phone", pubkey_hex="<hex>")
scholartools.peer_revoke_device(peer_id="bob", device_id="old-tablet")
scholartools.peer_revoke(peer_id="bob")   # revoke entire peer
```

To enable sync, add `peer` and `sync` blocks to `config.json`:

```json
{
  "peer": {
    "peer_id": "alice",
    "device_id": "laptop"
  },
  "sync": {
    "bucket": "my-library-sync",
    "access_key": "AKIAIOSFODNN7EXAMPLE",
    "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "endpoint": "https://s3.example.com"
  }
}
```

`peer` is required when `sync` is present. Omitting `endpoint` targets AWS S3. Without a `sync` block the library runs local-only and the functions below are no-ops.

```python
# push local change log entries to remote backend
scholartools.push()

# pull and replay remote entries (LWW per field, HLC causality)
scholartools.pull()

# upload a snapshot for peer bootstrapping
scholartools.create_snapshot()

# conflict management (concurrent field edits within 60 s window)
scholartools.list_conflicts()
scholartools.resolve_conflict(uid="sha256:abc", field="title", winning_value="Corrected Title")
scholartools.restore_reference("vaswani2017")   # undo a remote delete
```

## search sources

Crossref · Semantic Scholar · arXiv · OpenAlex · DOAJ · Google Books — queried concurrently, results normalized to CSL-JSON. All sources retry up to 3 times with a 5s delay on rate limits or server errors.

## dev

```bash
uv sync
bash init.sh       # health check
uv run pytest      # full test suite
```
