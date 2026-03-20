---
name: scholartools-config
description: scholartools configuration reference — file location, settings structure, env vars, citekey pattern tokens, and computed data paths. Use this whenever the user asks how to set up scholartools, change any configuration option, enable or disable an API source (Crossref, Google Books, Semantic Scholar, etc.), configure LLM PDF extraction, customize citekey generation, or when any scholartools function fails due to a missing or misconfigured setting.
---

Config file path:

| OS | Path |
|----|------|
| Linux / macOS | `~/.config/scholartools/config.json` |
| Windows | `C:\Users\<user>\.config\scholartools\config.json` |

Auto-created with defaults on first use. Edit manually; call `reset()` after changes at runtime.

## Settings structure

```json
{
  "backend": "local",
  "local": { "library_dir": "~/.local/share/scholartools" },
  "apis": {
    "email": "you@example.com",
    "sources": [
      {"name": "crossref", "enabled": true},
      {"name": "semantic_scholar", "enabled": true},
      {"name": "arxiv", "enabled": true},
      {"name": "openalex", "enabled": true},
      {"name": "doaj", "enabled": true},
      {"name": "google_books", "enabled": true}
    ]
  },
  "llm": { "model": "claude-sonnet-4-6" },
  "citekey": {
    "pattern": "{author[2]}{year}",
    "separator": "_",
    "etal": "_etal",
    "disambiguation_suffix": "letters"
  }
}
```

## Env vars

| Var | Purpose |
|-----|---------|
| `ANTHROPIC_API_KEY` | LLM fallback for scanned PDF extraction |
| `GBOOKS_API_KEY` | Google Books source |
| `SEMANTIC_SCHOLAR_API_KEY` | Higher Semantic Scholar rate limits |

## Citekey tokens

- `{author[N]}` — first N author surnames joined by `separator`
- `{year}` — 4-digit year
- `etal` — appended when authors > N
- `disambiguation_suffix`: `"letters"` (a/b/c) or `"title[1-9]"` (first N title words)

## Function

```python
reset() -> None
# Clears cached config and ctx. Required after editing config.json at runtime.
```

## Computed paths (relative to library_dir)

| Path | Purpose |
|------|---------|
| `library.json` | Production library |
| `files/` | Archived files |
| `staging.json` | Staged references |
| `staging/` | Staged files |
| `peers/` | Peer registry |
