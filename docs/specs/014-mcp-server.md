# spec: 013-mcp-server
version: 1.0
status: approved

## objective

Build an MCP server that exposes the scholartools library to Claude Desktop and MCP-compatible clients through 7 workflow-phase tools. The server is a thin wrapper over the existing public API — no new services, no new models, no new adapters. Success is an agent confidently selecting the correct tool first, executing a full research workflow end-to-end, with no exceptions leaking across the MCP boundary.

## acceptance criteria

- WHEN `scht-mcp` is invoked, the system MUST initialize stdio transport via FastMCP and register exactly 7 tools with trigger-condition descriptions — never raise on startup.
- WHEN a `discover` call is received with `query`, optional `sources`, and optional `limit`, the system MUST call `scholartools.discover_references()`, return staged references in `SearchResult`, and NOT require a subsequent `staging` call to persist candidates.
- WHEN a `fetch` call is received with `identifier`, the system MUST call `scholartools.fetch_reference()`, auto-stage the result, and return `FetchResult` with `reference`, `source`, and `error` — identifier type is auto-detected by the public API.
- WHEN an `ingest_file` call is received with `file_path`, the system MUST call `scholartools.extract_from_file()`, auto-stage the result with its linked file, and return `ExtractResult` with `reference`, `method_used`, `confidence`, and `error`.
- WHEN a `staging` call is received with `action="list"` and optional `page`, the system MUST call `scholartools.list_staged()` and return paginated `ListStagedResult`.
- WHEN a `staging` call is received with `action="delete"` and `citekey`, the system MUST call `scholartools.delete_staged()` and return `DeleteStagedResult`.
- WHEN a `staging` call is received with `action="merge"` and optional `omit` and `allow_semantic`, the system MUST call `scholartools.merge()` and return `MergeResult` with promoted and skipped citekeys.
- WHEN a `library` call is received with `action="filter"` and any combination of `query`, `author`, `year`, `ref_type`, `has_file`, `page`, the system MUST call `scholartools.filter_references()` and return paginated `ListResult`.
- WHEN a `library` call is received with `action="get"` and `citekey`, the system MUST call `scholartools.get_reference()` and return `GetResult` with the full Reference or error.
- WHEN a `library` call is received with `action="list"` and optional `page`, the system MUST call `scholartools.list_references()` and return paginated `ListResult`.
- WHEN a `manage_reference` call is received with `action="add"` and `ref` dict, the system MUST call `scholartools.add_reference()` and return `AddResult` with citekey or error.
- WHEN a `manage_reference` call is received with `action="update"`, `citekey`, and `fields` dict, the system MUST call `scholartools.update_reference()` and return `UpdateResult`.
- WHEN a `manage_reference` call is received with `action="delete"` and `citekey`, the system MUST call `scholartools.delete_reference()` and return `DeleteResult`.
- WHEN a `manage_reference` call is received with `action="rename"`, `old_key`, and `new_key`, the system MUST call `scholartools.rename_reference()` and return `RenameResult`.
- WHEN a `files` call is received with `action="link"`, `citekey`, and `file_path`, the system MUST call `scholartools.link_file()` and return `LinkResult`.
- WHEN a `files` call is received with `action="unlink"` and `citekey`, the system MUST call `scholartools.unlink_file()` and return `UnlinkResult`.
- WHEN a `files` call is received with `action="move"`, `citekey`, and `dest_name`, the system MUST call `scholartools.move_file()` and return `MoveResult`.
- WHEN a `files` call is received with `action="list"` and optional `page`, the system MUST call `scholartools.list_files()` and return paginated `FilesListResult`.
- WHEN any tool call fails (library error, missing param, unknown action), the system MUST return a result with `error` populated — never raise an exception across the MCP boundary.
- WHEN `file_path` is provided to `ingest_file` or `files link`, the system MUST reject paths containing `..` before calling the public API.

## tasks

- [x] task-01: scaffold mcp_server.py and entry point (blocks: none)
  - Create `scholartools/mcp_server.py` with FastMCP instance and `main()` that calls `mcp.run()`
  - Add `mcp>=1.0` to `pyproject.toml` optional dependencies: `[project.optional-dependencies] mcp = ["mcp>=1.0"]`
  - Add entry point to `pyproject.toml`: `scht-mcp = "scholartools.mcp_server:main"`
  - Tests: module imports without error; `main` is callable; FastMCP instance is registered

- [x] task-02: implement discover, fetch, ingest_file tools (blocks: task-01)
  - `discover(query, sources=None, limit=10)` — calls `st.discover_references()`, trigger-condition description
  - `fetch(identifier)` — calls `st.fetch_reference()`, trigger-condition description distinguishing from `discover`
  - `ingest_file(file_path)` — calls `st.extract_from_file()`, rejects `..` in path
  - Register all three with `@mcp.tool()`
  - Tests: each returns correct dict; file path with `..` returns error; descriptions present in tool schema

- [x] task-03: implement staging tool (blocks: task-01)
  - `staging(action, page=1, citekey=None, omit=None, allow_semantic=False)`
  - Routes `list` → `st.list_staged()`, `delete` → `st.delete_staged()`, `merge` → `st.merge()`
  - Unknown action returns `{"error": "unknown action: <action>"}` — no exception
  - Register with `@mcp.tool()`
  - Tests: each action path; unknown action; missing `citekey` on delete returns error

- [x] task-04: implement library tool (blocks: task-01)
  - `library(action, query=None, author=None, year=None, ref_type=None, has_file=None, citekey=None, page=1)`
  - Routes `filter` → `st.filter_references()`, `get` → `st.get_reference()`, `list` → `st.list_references()`
  - Unknown action returns `{"error": "unknown action: <action>"}`
  - Register with `@mcp.tool()`
  - Tests: each action path; `get` with missing citekey returns error; filter with all params combined

- [x] task-05: implement manage_reference tool (blocks: task-01)
  - `manage_reference(action, ref=None, citekey=None, fields=None, old_key=None, new_key=None)`
  - Routes `add` → `st.add_reference()`, `update` → `st.update_reference()`, `delete` → `st.delete_reference()`, `rename` → `st.rename_reference()`
  - Unknown action returns `{"error": "unknown action: <action>"}`
  - Register with `@mcp.tool()`
  - Tests: each action path; `add` with missing `ref` returns error; `update` with missing `citekey` returns error

- [x] task-06: implement files tool (blocks: task-01)
  - `files(action, citekey=None, file_path=None, dest_name=None, page=1)`
  - Routes `link` → `st.link_file()`, `unlink` → `st.unlink_file()`, `move` → `st.move_file()`, `list` → `st.list_files()`
  - Rejects `..` in `file_path` before forwarding; unknown action returns error
  - Register with `@mcp.tool()`
  - Tests: each action path; path traversal rejection; missing required params per action

- [x] task-07: Claude Desktop setup documentation (blocks: none)
  - Create `docs/manuals/claude-desktop-setup.md` with:
    - `uvx` install config block (production)
    - `uv run --project` config block (local dev)
    - Required env vars (`ANTHROPIC_API_KEY`, optionally `SEMANTIC_SCHOLAR_API_KEY`, `GBOOKS_API_KEY`)
    - Quick-start: "call `discover` with a topic to verify the server is working"
    - Troubleshooting: stdio not found, config path, env var resolution order

- [x] task-08: integration tests and smoke test (blocks: task-02, task-03, task-04, task-05, task-06)
  - Integration test: each of the 7 tools called with valid params against a test library; verify public API is called and result serializes to dict
  - Smoke test: `uv run scht-mcp` starts without error; exits cleanly on SIGINT
  - Run full test suite: `uv run pytest && uv run ruff check .` — no regressions

## ADR required?

No. The MCP server is a translation layer over existing architecture. All relevant decisions are locked in docs/adr/.

## risks

1. **FastMCP breaking changes** — `mcp` SDK is actively developed; pin to minor version in pyproject.toml and monitor releases.
2. **`library` vs `manage_reference` tool confusion** — agents may pick the wrong one; validate with real Claude Desktop sessions after task-08 and tighten descriptions if needed.
3. **Result type drift** — if public API Result types change, MCP tool return dicts must stay in sync; MCP layer should call `.model_dump()` on public Result objects rather than reconstruct fields manually.
4. **Staging accumulation** — `discover`, `fetch`, and `ingest_file` all auto-stage; agents that call these repeatedly without merging will accumulate staging records; document the behavior and rely on agent judgment for v1.
5. **Path safety** — `ingest_file` and `files link` accept user-supplied paths; reject `..` at the MCP boundary; absolute path enforcement handled by the public API's Settings layer.
