# scholartools

Reference management library built for AI agents. Local-first, no GUI, no human workflows — clean functions an agent can call with confidence.

## install

```bash
git clone https://github.com/abrahambahez/scholartools
cd scholartools
uv pip install -e .
```

## config

Create `.scholartools/config.json` in your project, or `~/.config/scholartools/config.json` for global defaults. Without a config file, local defaults apply (`data/library.json`, `data/files/`).

```json
{
  "backend": "local",
  "local": {
    "library_path": "data/library.json",
    "files_dir": "data/files"
  },
  "llm": {
    "anthropic_api_key": null
  }
}
```

`anthropic_api_key` falls back to the `ANTHROPIC_API_KEY` env var.

## usage

```python
import scholartools

# search external sources
result = scholartools.search_references("transformer attention mechanism", limit=5)

# fetch full record by DOI, arXiv ID, or ISSN
result = scholartools.fetch_reference("10.48550/arXiv.1706.03762")

# store a reference
result = scholartools.add_reference({"type": "article-journal", "title": "Attention Is All You Need", ...})

# extract metadata from a local PDF
result = scholartools.extract_from_file("papers/vaswani2017.pdf")

# CRUD
scholartools.get_reference("vaswani2017")
scholartools.update_reference("vaswani2017", {"note": "foundational"})
scholartools.delete_reference("vaswani2017")
scholartools.list_references()

# file archive
scholartools.link_file("vaswani2017", "papers/vaswani2017.pdf")
scholartools.list_files()
```

Every function returns a typed Result model — never raises.

## search sources

Latindex · Crossref · Semantic Scholar · arXiv — queried concurrently, results normalized to CSL-JSON.

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
