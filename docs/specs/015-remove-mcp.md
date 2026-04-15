# spec: remove MCP support

## findings

- `scholartools/mcp_server.py` — FastMCP stdio server, 7 tools wrapping the public API
- `tests/unit/test_mcp_server.py` — 34 unit tests (mock-heavy, fragile)
- `tests/integration/test_mcp_tools.py` — 17 integration tests
- `dist/scholartools.mcpb` — bundled artifact
- `.mcpbignore` — bundle exclude list
- `docs/manuals/claude-desktop-setup.md` — user-facing setup guide
- `docs/feats/013-mcp-server.md` — already marked deprecated (v0.2)
- `pyproject.toml` entry point: `scht-mcp` and optional dep group `mcp`
- `manifest.json` — mcpb bundle manifest

## objective

Remove all MCP server code, tests, artifacts, and documentation from the repository. The MCP integration produced a brittle test surface that was not viable for researchers, and the maintenance cost outweighed the benefit. The CLI (`scht`) remains the primary interface. Future agent integration will be reconsidered with a cleaner model.

## acceptance criteria (EARS format)

- when `uv run pytest` runs, the system must pass with no MCP-related test files present
- when `uv build` runs, the system must succeed with no `scht-mcp` entry point
- when `pyproject.toml` is read, the system must contain no `mcp` optional dependency group and no `scht-mcp` script entry
- when `docs/manuals/claude-desktop-setup.md` is read, the system must not contain setup instructions (file removed or replaced with a deprecation notice)
- when the package is installed, the system must not expose a `scht-mcp` command
- when `uv run ruff check .` runs, the system must report no errors

## tasks

- [ ] task-01: delete `scholartools/mcp_server.py`, `tests/unit/test_mcp_server.py`, `tests/integration/test_mcp_tools.py` (blocks: none)
- [ ] task-02: remove `scht-mcp` script entry and `mcp` optional dependency group from `pyproject.toml` (blocks: task-01)
- [ ] task-03: delete `dist/scholartools.mcpb`, `.mcpbignore`, `manifest.json` (blocks: none)
- [ ] task-04: remove or replace `docs/manuals/claude-desktop-setup.md` with a one-line deprecation notice (blocks: none)
- [ ] task-05: run `uv run pytest` and `uv run ruff check .` to verify clean state; update `feature_list.json` entry for `mcp-server` to `passes: false` with removal note (blocks: task-01, task-02, task-03, task-04)

## ADR required?

no

## risks

- `manifest.json` may be used by tooling outside mcpb — verify before deleting (check git history and any CI references)
- removing the `mcp` dep group may affect `uv.lock` — run `uv sync` after pyproject edit to keep lock consistent
