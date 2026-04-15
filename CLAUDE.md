# scholartools

## stack
- language: Python 3.12+
- architecture: Hexagonal (Ports & Adapters) — see docs/tech.md
- data validation: Pydantic v2 — all models in src/scholartools/models.py
- pdf extraction: pdfplumber (primary) + Anthropic SDK vision (fallback)
- http client: httpx (async-first)
- testing: pytest
- package manager: uv

## commands
- dev: uv sync
- test: uv run pytest
- test (unit only): uv run pytest tests/unit
- test (with integration): uv run pytest --run-integration
- build: uv build
- lint: uv run ruff check .
- lint-fix: uv run ruff check --fix .

## CI/CD
- the build-release workflow triggers ONLY on `v*` tags — pushing to main does NOT trigger it
- to release: `git tag vX.Y.Z[-rcN] && git push origin vX.Y.Z[-rcN]`
- skill zips (`scholartools-{skill-name}-{lang}-vX.Y.Z.zip`, one per skill) are published automatically when any file under `skills/` changed since the previous tag; install scripts download them to the user's Documents folder

## changelog discipline
- every CHANGELOG.md entry must follow "Keep a Changelog" with semantic versioning
- if any file under `skills/` changed in a release, the CHANGELOG entry MUST include a `### Skills` subsection with one sentence per changed skill describing what was updated — this is the signal users need to know whether to re-run `install-skills.sh`

## workflow
This project uses RPI-SDD workflow.

Session startup (mandatory, every session):
1. Read claude-progress.txt to understand last session state
2. Read feature_list.json and identify highest-priority feature with passes: false
3. Run init.sh to confirm the environment is healthy
4. Only then begin work

Before implementing any non-trivial feature:
1. Write or iterate docs/feats/[feature].md (your design thinking)
2. Run /design [feature] if you want feedback on your thinking (optional)
3. Run /research [feature] to map blast radius
4. Run /spec [feature] to produce acceptance criteria and task DAG
5. Get explicit approval before /task commands
6. Run /review after each task commit
7. Only flip passes: true in feature_list.json after verified end-to-end testing
8. Run /eval before any production deploy

Session end (mandatory):
- Append a progress entry to claude-progress.txt
- Commit all work-in-progress with descriptive message
- Never leave a feature half-implemented and uncommitted

Use "ultrathink" for architecture decisions.

## conventions
- functional Python style throughout — modules of functions, not classes with methods
- all public agent-facing functions are re-exported from src/scholartools/__init__.py — never tell users to import from submodules
- all Pydantic models live in src/scholartools/models.py — no inline model definitions elsewhere
- services are modules of `async def` functions that take `ctx: LibraryCtx` as a parameter
- public functions in __init__.py are sync wrappers via asyncio.run() — agents never see ctx
- every public function returns a Result model — never raises at the public boundary
- adapters are modules of plain functions matching port Protocol signatures — no adapter classes
- all config and paths come from the Settings model loaded via config.py — no hardcoded paths
- all HTTP calls go through httpx in apis/ — never instantiate httpx outside those modules
- all LLM calls go through src/scholartools/apis/ — never instantiate Anthropic() outside that layer
- integration tests are marked with `@pytest.mark.integration` and skipped by default

## do not
- do not write service classes or adapter classes — use module-level functions only
- do not use OOP inheritance anywhere in the codebase — composition and protocols only
- do not raise exceptions at the public API boundary — catch at the adapter level, surface via result.errors
- do not access adapters inside services directly — receive them through ctx: LibraryCtx
- do not add sync/await to __init__.py functions — they are sync wrappers only
- do not hardcode file paths — everything through Settings
- do not define Pydantic models outside models.py
- do not add dependencies without asking the user
- do not catch bare Exception — catch specific exception types at adapter boundaries
- do not write business logic inside adapters — adapters translate, services decide

## context
- docs/product.md: what it is, who it's for, success criteria
- docs/vision.md: aspirational long-term scope
- docs/tech.md: stack decisions, architecture diagram, module map, ADR index
- docs/structure.md: directory layout, naming conventions, layer rules, test structure
- docs/adr/: architecture decision records — read before questioning a stack choice
- docs/feats/: canonical feature docs (your design thinking, versioned) — numbered like ADRs: 001-core-library.md, 002-fastapi-server.md, etc. Pass the full numbered name to /design and /spec (e.g. /design 003-mcp-server)
- feature_list.json: cross-session feature state — read every session start
- claude-progress.txt: append-only session log — read every session start
- docs/specs/: active acceptance criteria and task DAGs — numbered like ADRs and feats: 001-core-library.md, 002-fastapi-server.md, etc. Pass the full numbered name to /spec (e.g. /spec 003-mcp-server)
- skills/: user-facing workflow skills shipped to researchers alongside scholartools.mcpb — DO NOT confuse with .claude/skills/ (dev workflow, not shipped)
