# scholartools for Claude Desktop

scholartools gives Claude a persistent, structured reference library. Instead of re-searching for papers each session, Claude builds a library you own — local JSON files, no cloud dependency, no GUI required.

This manual covers installation and the opinionated workflow scholartools is built around.

---

## Installation

### Install the bundle

Download `scholartools.mcpb` and drag it onto the Claude Desktop window, or double-click it. Claude Desktop will prompt you for three optional settings:

| Setting | Purpose | Default |
|---|---|---|
| Anthropic API Key | LLM fallback for PDF metadata extraction when pdfplumber fails | none (pdfplumber only) |
| Library Path | Where your `library.json` lives | `~/.scholartools/library.json` |
| Files Directory | Where your PDF archive lives | `~/.scholartools/files/` |

Restart Claude Desktop after installation.

### Verify

Send Claude this message:

> Use the discover tool to find 3 papers about transformer attention mechanisms.

If you see a list of references with titles and authors, the server is working.

### Local development install

If you're running from source instead of the bundle:

```json
{
  "mcpServers": {
    "scholartools": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/scholartools", "scht-mcp"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

Config file location:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/claude/claude_desktop_config.json`

---

## The workflow

scholartools enforces a two-state model: **staging** and **library**.

- **Staging** is a scratchpad. References land here from discovery, fetch, or PDF extraction. Nothing in staging is permanent.
- **Library** is the committed record. References enter it only after a merge/QA pass that validates schema, detects duplicates, moves files to the archive, and assigns a citekey.

This separation means Claude can explore freely — pulling in dozens of candidates — without polluting your library. You decide what stays.

```
external sources / local PDFs
        ↓
  discover / fetch / ingest_file   ← candidates land in staging
        ↓
      staging list → review        ← you tell Claude what to keep
        ↓
      staging merge                ← QA, dedup, citekey assignment
        ↓
      library                      ← your committed reference record
```

---

## Phase 1: Surface candidates

There are three ways to bring references into staging.

### Search by topic

Use this when you have a research question, not a specific paper in mind.

> Find papers about federated learning and differential privacy. Limit to 5 per source.

Claude calls `discover` and fans out across Crossref, Semantic Scholar, OpenAlex, arXiv, and DOAJ. All results land in staging automatically.

### Fetch by identifier

Use this when you have a DOI, arXiv ID, ISBN, or PubMed ID.

> Fetch this paper: 10.48550/arXiv.1706.03762

Claude calls `fetch`, resolves the identifier against the appropriate API, normalizes the record to CSL-JSON, and stages it. Prefer this over `discover` when you have an exact identifier — it's faster and returns a single authoritative record.

### Extract from a local file

Use this when you have a PDF on disk.

> Extract the reference metadata from /Users/you/Downloads/vaswani2017.pdf

Claude calls `ingest_file`, runs pdfplumber first, falls back to LLM vision if confidence is low, and stages the result with the file linked to it. The file travels with the record through the merge gate into the archive.

---

## Phase 2: Review staging

After surfacing candidates, ask Claude to show what's there:

> List what's in staging.

Claude calls `staging list` and returns a paginated view of all candidates. Review the titles and decide what to keep. For anything you don't want:

> Remove smith2019 from staging.

Claude calls `staging delete` with the citekey. Repeat until staging contains only the references you want to promote.

---

## Phase 3: Merge to library

When staging is curated, promote the records:

> Merge staging into the library.

Claude calls `staging merge`, which runs the QA pipeline:

1. Schema validation — incomplete records are flagged in `errors`, not silently promoted
2. Duplicate detection — records already in the library are moved to `skipped`
3. File archival — any linked files are moved into `~/.scholartools/files/`
4. Citekey assignment — each record gets a stable, human-readable citekey (e.g. `vaswani2017attention`)

The result tells you what was `promoted`, what was `skipped` (duplicates), and any `errors`.

You can also skip specific citekeys during merge:

> Merge staging but skip jones2021 and lee2023.

---

## Phase 4: Query the library

Once references are in the library, Claude can retrieve them in several ways.

### Filter by topic, author, or year

> Do I have anything on attention mechanisms published after 2020?

> Find all references by Goodfellow in my library.

Claude calls `library filter` with the relevant parameters.

### Get a full record

> Show me the full record for vaswani2017attention.

Claude calls `library get` with the citekey and returns the complete CSL-JSON record.

### List everything

> List all references in my library.

Claude calls `library list` with pagination support.

---

## Phase 5: Maintain the library

### Edit a record

> Update the title of smith2019 to "Attention Is All You Need (revised)".

Claude calls `manage_reference update` with the citekey and the fields to change. Only the provided fields are modified.

### Add a reference manually

> Add this reference: title "Deep Learning", authors LeCun, Bengio, Hinton, year 2015, type book.

Claude calls `manage_reference add` with the CSL-JSON fields you provide.

### Delete or rename

> Delete jones2021 from my library.

> Rename smith2019 to vaswani2017attention.

Claude calls `manage_reference delete` or `manage_reference rename`.

### Manage attached files

> Attach /Users/you/papers/lecun2015.pdf to lecun2015deep.

> List all files in my library.

> Detach the file from jones2021.

Claude calls `files link`, `files list`, or `files unlink`. Files are copied into the archive on link — the original is untouched.

---

## Troubleshooting

**Server not appearing in Claude Desktop** — Reinstall the bundle. If using the manual config, confirm the JSON is valid (no trailing commas, matching braces) and restart Claude Desktop after saving.

**`uv` not found** — Claude Desktop inherits PATH from the shell that launched it, not from your current terminal. Add `uv` to PATH in `~/.zshrc` or `~/.bash_profile`, then restart Claude Desktop from that shell (not from Spotlight or the Dock on macOS).

**PDF extraction returns low confidence** — Set an `ANTHROPIC_API_KEY` to enable LLM vision fallback. Without it, extraction relies on pdfplumber alone, which struggles with scanned or non-embedded PDFs.

**Duplicate not detected at merge** — Duplicate detection matches on title similarity and author overlap. Records with very different metadata representations of the same paper (e.g. preprint vs. published version with different titles) may both be promoted. Use `staging delete` to manually drop the copy before merging, or rename the promoted record afterward.
