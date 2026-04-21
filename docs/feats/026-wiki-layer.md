---
id: 026-wiki-layer
title: Wiki Layer — reference notes and permanent knowledge
status: design
created: 2026-04-20
---

# Wiki Layer

## Problem

The reading skills (structural-reading, analytical-reading) produce `@citekey.md` notes and permanent concept notes. Loretools currently has no location, no settings path, no API, and no adapter to support any of this. The agent is forced to use raw filesystem operations in the user's vault with no library-aware context, making prerequisite checks ("does this note have a Structure section with real content?") impossible via the API.

## What it is

A `wiki/` directory alongside `sources/` and `staging/` in the loretools library root. It stores knowledge artifacts the Human-AI dyad produces:

- `wiki/refs/` — one `@citekey.md` per reference (structural and analytical reading output)
- `wiki/notes/` — permanent concept notes that references point to with `[[wikilinks]]`

`sources/` is input material (files you didn't write). `wiki/` is output knowledge (what the reading workflow produced). The distinction is architectural, not just organizational.

## Directory layout

```
.lore/
  config.json
library.json
sources/
  raw/          ← original PDFs, EPUBs
  read/         ← extracted text (citekey.source.md / .txt)
staging/
  staging.json
  staging/
wiki/
  refs/         ← @citekey.md reference notes
  notes/        ← permanent concept notes
```

## Note format

Reference notes follow Obsidian-compatible ATX markdown with YAML frontmatter. The section scaffold is fixed — the reading skills depend on exact section names.

```markdown
---
citekey: smithjones2023
title: "Title of the Work"
authors: "Smith, Jones"
year: 2023
type: book
summary: ""
---

## Context

## Structure

## Author's Terms

## Terms and Arguments
```

Rules:
- `summary` lives in frontmatter — a one-paragraph string field, written by the analytical reading skill, machine-readable
- Frontmatter fields come from the reference library record at note creation time; `summary` starts empty
- `[[wikilinks]]` are plain text in the note body — no parser needed to write them, only to resolve them
- Section names are stable across languages: the EN and ES skills use the same section keys in code, surface-translated in the note body (spec must decide: use EN keys in code, allow translated headers in files, or keep headers in the user's language)

## Adapter (`adapters/wiki.py`)

Module of plain functions — no classes. The adapter touches files; the service decides.

Functions needed:
- `make_wiki_refs_reader(wiki_refs_dir)` → `ReadNote` port (reads `@citekey.md` content)
- `make_wiki_refs_writer(wiki_refs_dir)` → `WriteNote` port (writes `@citekey.md` content)
- `make_wiki_notes_searcher(wiki_notes_dir)` → `SearchNotes` port (grep-style search by keyword)
- `note_path(citekey, wiki_refs_dir)` → `Path` (pure, no I/O)

Markdown section parsing lives in the service layer, not the adapter. The adapter only reads/writes raw strings.

## Service (`services/wiki.py`)

Async functions receiving `ctx: LibraryCtx`. Handles:
- `scaffold_note(citekey, ctx)` — builds skeleton content from reference metadata
- `create_reference_note(citekey, ctx)` — scaffold + write; error if already exists
- `get_reference_note(citekey, ctx)` — read raw content; error if missing
- `section_has_content(note_content, section_name)` → bool — prerequisite check for reading skills
- `update_note_section(citekey, section_name, content, ctx)` — read → splice → write
- `search_permanent_notes(query, ctx)` — delegate to `SearchNotes` port

Section parsing: split on `\n## ` delimiters; find target section; check if it has non-whitespace content beyond the header.

## CLI (`lore wiki`)

Skills call the CLI — never Python internals. Subcommands:

```sh
lore wiki create <citekey>
# Scaffold @citekey.md in wiki/refs/ from library metadata. Errors if note exists.

lore wiki get <citekey>
# Print raw note content to stdout.

lore wiki update <citekey> <section> '<content>'
# Replace the named section body. Section name is the header text (e.g. "Context").

lore wiki section-ready <citekey> <section>
# Exit 0 if section has non-whitespace content, exit 1 otherwise.
# Used by skill prerequisite checks.

lore wiki search <query>
# Keyword search across wiki/notes/. Returns matching note titles, one per line.
```

## Python API

Sync wrappers in `__init__.py` back the CLI. Skills never call these directly.
- `create_note(citekey)` → `NoteResult`
- `get_note(citekey)` → `NoteResult`
- `update_note_section(citekey, section, content)` → `NoteResult`
- `note_section_ready(citekey, section)` → `bool`
- `search_notes(query)` → `NoteSearchResult`

## Models

In `models.py`:
- `NoteResult(citekey, path, content, error)` — always returned, never raises
- `NoteSearchResult(matches: list[str], total: int)` — matches are note titles or paths

## LibraryCtx additions

```python
wiki_refs_dir: str
wiki_notes_dir: str
read_note: ReadNote           # Callable[[str], str | None]
write_note: WriteNote         # Callable[[str, str], None]
search_notes: SearchNotes     # Callable[[str], list[str]]
```

## Decisions (locked)

1. **Section header language**: EN headers always in files (`## Context`, `## Structure`, etc.), regardless of the skill's language. Content inside sections is in the user's language; headers are stable code keys. The `lore wiki update` command accepts the EN header name.

2. **Permanent notes**: defer creation to a future spec. Minimum contract for `wiki/notes/` files: YAML frontmatter with at least `title:`, body may contain `[[wikilinks]]`. `lore wiki search` searches this directory by keyword; matching returns absolute file paths (one per line).

3. **CLI as primary interface**: `lore wiki` subcommands are what skills call. Python API backs the CLI but is not exposed to agents or skills.

4. **`lore wiki create` validates library**: before scaffolding, the command checks that the citekey has a record in the library. Errors if not found — same guarantee as `lore refs get`.

5. **Section parsing edge cases**: section content is everything between its `\n## Header\n` and the next `\n## ` or EOF, stripped of leading/trailing whitespace. A section is "has content" if that stripped string is non-empty. A section not found in the file returns `false` from `section-ready` without error.

6. **`summary` update**: `lore wiki update <citekey> summary '<text>'` writes to the frontmatter `summary:` field, not a markdown section. The command treats `summary` as a reserved key that maps to frontmatter.

7. **`wiki_dir` configurable**: defer to a later version. Default: `library_dir / "wiki"`.

8. **SearchNotes output**: `list[str]` of absolute file paths. Agent resolves titles from frontmatter or filename as needed.

## What this does NOT include

- NotebookLM or any external notebook integration
- Semantic search / embeddings (future spec)
- Note graph / backlink resolution
- EPUB or non-PDF source format support (separate markitdown spec)
- CLI subcommands for wiki operations (defer)
