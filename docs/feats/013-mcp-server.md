# feat 013: MCP server

version: 0.2
status: deprecated

> **Deprecated (2026-03-19):** MCP support is being removed. The test surface was too brittle for researchers and the integration added maintenance cost without clear user benefit. MCP-based agent access will be reconsidered in a future iteration with a cleaner integration model. See docs/specs/015-remove-mcp.md.

## what this is

An MCP (Model Context Protocol) server that exposes the scholartools library to Claude Desktop and any MCP-compatible client. The design goal is the minimum number of tools an agent needs to execute the full research workflow without ambiguity — 7 tools, organized by workflow phase rather than function name.

The CLI structure (one command per function) is wrong for MCP. CLI optimizes for human typing; MCP optimizes for agent selection confidence. The agent must choose the right tool from a list of names + descriptions alone — so tools are organized around cognitive tasks, not implementation units.

## the seven tools

The research workflow has a natural pipeline: discover → stage → curate → promote → query → cite. Tool boundaries follow phase transitions, not function boundaries.

```
external sources / local files
        ↓
  discover / fetch / ingest_file     ← surface candidates, auto-stage
        ↓
      staging                        ← review, trim, promote
        ↓
      library                        ← read-only queries on committed refs
        ↓
  manage_reference                   ← write mutations on committed refs
        ↓
       files                         ← attach/detach/list PDFs
```

### 1. `discover`

**Trigger**: "find papers about X", "search for references on Y", "what has been published about Z"

Fans out across all configured external APIs (Crossref, Semantic Scholar, arXiv, OpenAlex, DOAJ) and returns candidates. Results land in staging automatically — the agent does not need to call `staging` to store them.

```
params:
  query: str           — keywords or natural language topic
  sources: list[str]?  — limit to specific APIs; default: all enabled
  limit: int?          — max results per source; default: 10

returns: SearchResult
  references: list[Reference]   — candidates now in staging
  sources_queried: list[str]
  total_found: int
  errors: list[str]             — per-source failures, non-fatal
```

### 2. `fetch`

**Trigger**: "get this DOI", "fetch arXiv:XXXX", "I have an ISBN", any specific identifier

Resolves a single identifier (DOI, arXiv ID, ISBN, PubMed ID) against the appropriate API, normalizes to CSL-JSON, and auto-stages the result. Use this when the agent has a concrete identifier, not a topic. Prefer this over `discover` when an exact record is needed.

```
params:
  identifier: str   — DOI, arXiv ID, ISBN, or PubMed ID; type is auto-detected

returns: FetchResult
  reference: Reference | None   — staged if successful
  source: str | None            — which API resolved it
  error: str | None
```

### 3. `ingest_file`

**Trigger**: "I have a PDF", "extract metadata from this file", a local file path is mentioned

Runs PDF/EPUB metadata extraction (pdfplumber primary, Claude vision fallback) and auto-stages the result. The file is linked to the staged reference so it travels with the record through the merge gate.

```
params:
  file_path: str   — absolute path to a local PDF or EPUB

returns: ExtractResult
  reference: Reference | None   — staged if successful
  method_used: "pdfplumber" | "llm" | None
  confidence: float | None       — 0.0–1.0
  error: str | None
```

### 4. `staging`

**Trigger**: "show what I've staged", "remove X from staging", "promote to library", "merge staged refs"

Manages the staging buffer. This is the curation step between discovery and commitment. The agent reviews what's in staging, drops unwanted candidates, then calls merge to promote the rest.

```
params:
  action: "list" | "delete" | "merge"

  — for action "list":
    page: int?   — default: 1

  — for action "delete":
    citekey: str

  — for action "merge":
    omit: list[str]?           — citekeys to skip even if staged
    allow_semantic: bool?      — promote near-duplicates; default: false

returns:
  "list"   → ListStagedResult   (references: list[ReferenceRow], total, page, pages)
  "delete" → DeleteStagedResult (deleted: bool, error: str | None)
  "merge"  → MergeResult        (promoted: list[str], skipped: list[str], errors: list[str])
```

### 5. `library`

**Trigger**: "find references to X in my library", "do I have anything by Smith?", "list what I have on quantum computing", "get the full record for citekey Y"

Read-only queries on the committed library. Never modifies. Use `manage_reference` for writes.

```
params:
  action: "filter" | "get" | "list"

  — for action "filter":
    query: str?       — full-text keyword match on title/abstract
    author: str?      — partial match on any author family name
    year: int?        — exact year match
    ref_type: str?    — CSL type: "article-journal", "book", etc.
    has_file: bool?   — filter to refs with/without attached files
    page: int?        — default: 1

  — for action "get":
    citekey: str

  — for action "list":
    page: int?        — default: 1

returns:
  "filter" / "list" → ListResult  (references: list[ReferenceRow], total, page, pages)
  "get"             → GetResult   (reference: Reference | None, error: str | None)
```

### 6. `manage_reference`

**Trigger**: "update the title of X", "delete Y from my library", "add this reference manually", "rename citekey"

Write mutations on committed library records. Separate from `library` to make the read/write boundary explicit — the agent should reach for `library` first and only call this when modification is the actual intent.

```
params:
  action: "add" | "update" | "delete" | "rename"

  — for action "add":
    ref: dict   — CSL-JSON fields; id (citekey) is optional, generated if absent

  — for action "update":
    citekey: str
    fields: dict   — partial update; only provided fields are changed

  — for action "delete":
    citekey: str

  — for action "rename":
    old_key: str
    new_key: str

returns:
  "add"    → AddResult     (citekey: str | None, error: str | None)
  "update" → UpdateResult  (citekey: str | None, error: str | None)
  "delete" → DeleteResult  (deleted: bool, error: str | None)
  "rename" → RenameResult  (old_key: str | None, new_key: str | None, error: str | None)
```

### 7. `files`

**Trigger**: "attach this PDF to reference X", "list all files in my library", "detach the file from Y"

Manages the file archive for committed library records. Operates on `~/.scholartools/files/`. Does not touch staging files — those are managed implicitly by `ingest_file` and `staging`.

```
params:
  action: "link" | "unlink" | "move" | "list"

  — for action "link":
    citekey: str
    file_path: str   — source file; copied into the archive, original untouched

  — for action "unlink":
    citekey: str

  — for action "move":
    citekey: str
    dest_name: str   — new filename within the archive (no path, just name.ext)

  — for action "list":
    page: int?       — default: 1

returns:
  "link"   → LinkResult       (citekey: str | None, file_record: FileRecord | None, error: str | None)
  "unlink" → UnlinkResult     (unlinked: bool, error: str | None)
  "move"   → MoveResult       (new_path: str | None, error: str | None)
  "list"   → FilesListResult  (files: list[FileRow], total, page, pages)
```

## scope

In:
- `mcp>=1.0` added as an optional dependency: `mcp = ["mcp>=1.0"]` — server packaged using Anthropic's MCP Python SDK (`FastMCP`)
- MCP server module at `scholartools/mcp_server.py`
- stdio transport (Claude Desktop default)
- All 7 tools above with trigger-condition descriptions
- `pyproject.toml` entry point: `scht-mcp` → `scholartools.mcp_server:main`
- Claude Desktop config snippet in `docs/manuals/claude-desktop-setup.md`

Out (deferred):
- Sync tools (push, pull, create_snapshot, list_conflicts, resolve_conflict) — setup-time ops, not research-session ops
- Peer management tools — ditto
- SSE or HTTP transport
- Authentication / API key management through MCP
- Prompt templates or MCP resources

## decisions (locked)

- **Auto-stage on discovery**: `discover`, `fetch`, and `ingest_file` all write to staging automatically. The agent never needs to call `staging` just to record a found reference — staging is the scratchpad that absorbs all inbound candidates. This matches the product model and reduces tool calls for the common path.
- **Read/write split on library**: `library` is read-only, `manage_reference` is write-only. This is intentional friction — the agent must explicitly reach for the write tool, which makes mutations visible in the conversation.
- **Action dispatch over tool proliferation**: `staging`, `library`, `manage_reference`, and `files` each use an `action` param rather than being split into per-operation tools. This keeps the tool list at 7, which is below the selection-confidence threshold where agents start making wrong choices.
- **No sync/peer tools in v1**: Sync and peer management are setup-time operations that don't belong in a research session tool set. They will be added as a separate MCP server or as an `admin` tool group if demand surfaces.
- **Single server module**: The MCP server is a thin wrapper over the existing public API. All business logic stays in the service layer.
- **Transport**: stdio only. Claude Desktop expects stdio. SSE is deferred.

## tool description format

Tool descriptions must be trigger-condition statements. The agent reads the description to decide which tool to call — so descriptions answer "when would I reach for this?" not "what does this do?"

Template:
```
Use when [trigger condition]. [One sentence on what it does differently from similar tools.]
[State it writes to, if relevant.]
```

Example for `discover`:
> Use when you need to find new references on a topic or keyword. Returns candidates in staging — not committed to the library. Prefer `fetch` when you already have a specific identifier (DOI, arXiv ID, ISBN).

## package structure

```
scholartools/
  mcp_server.py     ← new: MCP server entry point, tool definitions, stdio loop
docs/
  manuals/
    claude-desktop-setup.md   ← new: config snippet for Claude Desktop users
```

No new services, no new models, no new adapters. The MCP server calls the same public API functions as any other consumer.

## claude desktop setup

The server ships as a `uv`-runnable script. Users add one block to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "scholartools": {
      "command": "uvx",
      "args": ["--from", "scholartools", "scht-mcp"]
    }
  }
}
```

Or, for a local development install:

```json
{
  "mcpServers": {
    "scholartools": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/scholartools", "scht-mcp"]
    }
  }
}
```
