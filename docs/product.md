# product: scholartools

## what it is

scholartools is a Python library for academic reference management built exclusively for AI agents. Local-first by default (CSL-JSON database, local file archive), with optional cloud backends configurable via a single config file — it gives agents a reliable, composable, deterministic interface to search, fetch, store, manage, and archive bibliographic references and their associated files across research domains: academic, legal, pharmaceutical, and beyond. Think Zotero rebuilt as a machine-native primitive: no GUI, no human-oriented workflows, just clean functions an agent can call with confidence.

References flow through two states: **staging** (exploration and evaluation) and **library** (production). Every record is normalized to CSL-JSON at the moment it enters staging — format ambiguity never propagates downstream. Promotion from staging to library is gated by a merge/QA step that validates schema completeness, detects duplicates, moves files to the archive, and assigns a citekey.

## who it's for

The primary user is the agent-human dyad operating in any research-intensive context. The agent is the direct consumer of the library; the human is the beneficiary. Our optimization target is the dyad as a unit: agent effectiveness (reliability, token efficiency, composability) in service of human goals (zero search-management friction, improved discoverability, better curation, expanded thinking space). Secondary users are developers building research-assistant products who need a dependency they can trust.

## the core problem

Existing reference managers — Zotero, Mendeley, JabRef — are designed for human hands: GUIs, manual workflows, personal conventions. When an AI agent tries to assist with research, it has to work around tools that were never designed for it:

- No programmatic interface built for agent consumption — CLIs and APIs are afterthoughts
- Human workflows are informal and personal, making them unreliable for agents to replicate
- No standard for what "a reference operation" looks like as an atomic, composable unit
- Deduplication, auditing, and citekey management require manual human judgment today
- There is no local-first reference store an agent can own and operate without a running GUI application
- Agents cannot reliably extract references from PDFs or manage the file archive alongside the metadata
- No staging area exists for references under evaluation — everything is committed immediately, making exploration messy and libraries drift into inconsistency
- Format normalization happens late or not at all, so bib files and ad-hoc formats accumulate errors that compound over time

## what it does

1. search — query academic references by topic or keywords across external APIs (Crossref, Semantic Scholar, OpenAlex, etc.)
2. fetch — retrieve full bibliographic metadata for a given identifier (DOI, arXiv ID, ISBN) and normalize to CSL-JSON
3. extract — parse a local PDF or ebook and extract bibliographic metadata, normalized to CSL-JSON
4. stage — add references to the staging area (from any source: identifier, PDF, free-form); all records are CSL-JSON from intake
5. merge — promote staged records to the library after QA: schema validation, duplicate detection, file archival, citekey assignment
6. store — CRUD operations on the production library (`~/.scholartools/library.json`)
7. files — manage associated files (`~/.scholartools/files/`): link, move, rename, audit
8. citekeys — generate, assign, and manage human-readable citekeys consistently
9. deduplicate — detect and resolve duplicate records
10. audit — validate library integrity (schema issues, missing fields, orphaned files) and report to the agent
11. export — serialize references for external tools: pandoc-compatible CSL-JSON, Word XML (OOXML), Google Docs citation XML
12. interface — all capabilities exposed as direct Python functions; other distribution channels (MCP server, REST API) are secondary

## storage backends

Defaults are local. All backends are configured via `config.json`:

- **local** (default): `data/library.json` for metadata, `data/files/` for PDFs and EPUBs
- **cloud option A**: DynamoDB (metadata) + S3 (files)
- **cloud option B**: MongoDB (metadata) + Google Cloud Storage (files)

Switching backends does not change the function interface.

## non-goals

- No graphical or human-operated UI
- No note-taking or knowledge-graph features
- No Zotero/Mendeley sync or migration tooling
- CLI is not a primary interface — it may exist as a thin wrapper but is not the design target

## success criteria

An agent can, across an iterative research session with human checkpoints:
1. receive a research topic, keywords, or a local PDF/ebook and stage candidate references — normalized to CSL-JSON immediately, regardless of source format
2. search external sources, stage results without committing, and present them to the human for selection
3. run a merge/QA pass on selected staged records: validate schema, detect duplicates against the library, archive files, assign citekeys — then promote clean records to the library
4. retrieve, filter, and cite library references on demand with consistent citekeys
5. audit the library: report integrity issues, missing fields, orphaned files
6. export references for writing tools: pandoc CSL-JSON, Word XML, Google Docs XML
7. switch storage backend via config without changing any agent code

The library is the ground truth for committed references. Staging is the scratchpad for exploration. The agent never has to guess which state a reference is in.
