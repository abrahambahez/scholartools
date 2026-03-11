# scholartools

Reference management library built for AI agents. Local-first, no GUI, no human workflows — clean functions an agent can call with confidence.

## install

```bash
git clone https://github.com/abrahambahez/scholartools
cd scholartools
uv pip install -e .
```

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

`library_dir` controls where `library.json`, `files/`, and `staging/` are stored. All other paths are derived from it.

Set `apis.email` to identify your requests to Crossref and OpenAlex (recommended — unlocks polite-pool rate limits).

API keys are never stored in config — set them as environment variables:

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | No | PDF metadata extraction via Claude vision (fallback when pdfplumber fails) |
| `GBOOKS_API_KEY` | No | Enables Google Books as a search/fetch source |
| `SEMANTIC_SCHOLAR_API_KEY` | No | Raises Semantic Scholar rate limits |

Without these keys the features degrade gracefully: LLM extraction is skipped, Google Books source is disabled.

## usage

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

## search sources

Crossref · Semantic Scholar · arXiv · OpenAlex · DOAJ · Google Books — queried concurrently, results normalized to CSL-JSON. All sources retry up to 3 times with a 5s delay on rate limits or server errors.

## Claude Desktop (MCPB)

Download `scholartools.mcpb` from GitHub Releases and double-click it. Claude Desktop handles Python and dependencies via uv automatically — no terminal required.

To build the bundle from source:

```bash
npm install -g @anthropic-ai/mcpb   # one-time
mcpb pack                            # produces scholartools.mcpb
```

## dev

```bash
uv sync
bash init.sh       # health check
uv run pytest      # full test suite
```
