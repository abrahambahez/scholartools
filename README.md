![scholartools](scholartools-banner.jpg)

Reference management library built for AI agents. Local-first, no GUI, no human workflows — clean functions an agent can call with confidence.

## install skills

macOS / Linux (default: English):

```bash
curl -fsSL https://raw.githubusercontent.com/abrahambahez/scholartools/main/install-skills.sh | bash
```

Spanish skills:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/abrahambahez/scholartools/main/install-skills.sh) --lang es
```

Windows (elevated PowerShell):

```powershell
irm https://raw.githubusercontent.com/abrahambahez/scholartools/main/install-skills.ps1 | iex
```

To uninstall:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/abrahambahez/scholartools/main/install-skills.sh) --uninstall
```

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/abrahambahez/scholartools/main/install-skills.ps1))) -Uninstall
```

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

To uninstall:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/abrahambahez/scholartools/main/install.sh) --uninstall
```

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/abrahambahez/scholartools/main/install.ps1))) -Uninstall
```

## config

Config is loaded from `~/.config/scholartools/config.json` (Windows: `C:\Users\<user>\.config\scholartools\config.json`). Created automatically with defaults on first use.

```jsonc
{
  "backend": "local",

  // Where library.json, files/, and staging/ are stored.
  // All paths are derived from this — it's the only path you ever need to set.
  "local": {
    "library_dir": "~/.local/share/scholartools"
  },

  "apis": {
    // Recommended: identifies your requests to Crossref and OpenAlex,
    // unlocking polite-pool rate limits on both sources.
    "email": "you@example.com",

    // All six sources are enabled by default.
    // Set "enabled": false on any source you want to disable.
    // google_books also requires the GBOOKS_API_KEY env var to activate.
    "sources": [
      { "name": "crossref",         "enabled": true },
      { "name": "semantic_scholar", "enabled": true },
      { "name": "arxiv",            "enabled": true },
      { "name": "openalex",         "enabled": true },
      { "name": "doaj",             "enabled": true },
      { "name": "google_books",     "enabled": true }
    ]
  },

  // Optional. Model used for PDF extraction via Claude vision
  // (fallback when pdfplumber cannot extract selectable text).
  // Requires ANTHROPIC_API_KEY. Omit this block to use the default.
  "llm": {
    "model": "claude-sonnet-4-6"
  },

  // Optional. Controls how citekeys are generated at merge time.
  // Omit this block to use the defaults shown here.
  "citekey": {
    // Tokens: {author[N]} = first N surnames, {year} = 4-digit year.
    "pattern": "{author[2]}{year}",
    // Joins multiple author surnames (e.g. "smith_jones2021").
    "separator": "_",
    // Appended when authors exceed the N in {author[N]}.
    "etal": "_etal",
    // How to disambiguate identical keys: "letters" (a/b/c)
    // or "title[1-9]" (first N words of the title).
    "disambiguation_suffix": "letters"
  },

  // Optional. Required when sync is present — identifies this device.
  // peer_id = who you are (e.g. your name), device_id = this machine.
  "peer": {
    "peer_id": "alice",
    "device_id": "laptop"
  },

  // Optional. Enables S3-backed distributed sync across devices.
  // Works with AWS S3, Cloudflare R2, Backblaze B2, or MinIO.
  // endpoint: null targets AWS S3; set a URL for any other provider.
  // Omit this block entirely for local-only operation.
  "sync": {
    "bucket": "my-scholartools-bucket",
    "access_key": "YOUR_ACCESS_KEY",
    "secret_key": "YOUR_SECRET_KEY",
    "endpoint": null
  }
}
```

API keys are never stored in config — set them as environment variables:

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | PDF metadata extraction via Claude vision (fallback when pdfplumber fails) |
| `GBOOKS_API_KEY` | Enables Google Books as a search/fetch source |
| `SEMANTIC_SCHOLAR_API_KEY` | Raises Semantic Scholar rate limits |

Without these keys features degrade gracefully: LLM extraction is skipped, Google Books is disabled.

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
scht files attach vaswani2017 papers/vaswani2017.pdf
scht files detach vaswani2017
scht files get vaswani2017
scht files move vaswani2017 attention.pdf
scht files list
scht files reindex

# staging
scht staging stage '{"title":"..."}' --file papers/draft.pdf
scht staging list
scht staging delete draft2024
scht staging merge
scht staging merge --omit draft2024

# sync
scht sync push-changelog
scht sync pull-changelog
scht sync snapshot
scht sync conflicts
scht sync resolve <uid> title "Corrected Title"
scht sync restore vaswani2017
scht sync sync-file vaswani2017
scht sync unsync-file vaswani2017

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
scholartools.attach_file("vaswani2017", "papers/vaswani2017.pdf")
scholartools.sync_file("vaswani2017")            # upload to S3
scholartools.get_file("vaswani2017")             # resolve local or cached path
scholartools.unsync_file("vaswani2017")          # clear blob_ref, keep local
scholartools.detach_file("vaswani2017")          # remove local copy
scholartools.move_file("vaswani2017", "attention.pdf")
scholartools.list_files(page=1)
scholartools.reindex_files()                     # repair stale paths after library move

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

To enable sync, add `peer` and `sync` blocks to `config.json` (see [config](#config) above). Without a `sync` block the library runs local-only and the functions below are no-ops.

```python
# push local change log entries to remote backend
scholartools.push_changelog()

# pull and replay remote entries (LWW per field, HLC causality)
scholartools.pull_changelog()

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
