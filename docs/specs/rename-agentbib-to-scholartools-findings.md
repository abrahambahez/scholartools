# findings: rename scholartools → scholartools

task: map the full blast radius of renaming `scholartools` → `scholartools`
date: 2026-03-09
status: complete — no implementation, read-only analysis

---

## files affected

### 1. Python package directory — src/scholartools/ → src/scholartools/

The entire directory must be renamed. Every file inside it contains intra-package imports that use `scholartools.*` and must be updated.

| file | reason |
|------|--------|
| `src/scholartools/__init__.py` | 9 import lines: `from scholartools.adapters…`, `from scholartools.apis…`, `from scholartools.config…`, `from scholartools.models…`, `from scholartools.services…`; also docstring on line 85 references `.scholartools/config.json` |
| `src/scholartools/config.py` | lines 50, 52, 55, 74, 76: env var names `SCHOLARTOOLS_CONFIG`, `SCHOLARTOOLS_LIBRARY_PATH`, `SCHOLARTOOLS_FILES_DIR`; config file paths `.scholartools/config.json` and `~/.config/scholartools/config.json` |
| `src/scholartools/models.py` | line 5: `from scholartools.ports import …` |
| `src/scholartools/ports.py` | no internal imports of package name, but lives inside the directory |
| `src/scholartools/adapters/local.py` | line 5: `from scholartools.ports import …` |
| `src/scholartools/services/extract.py` | line 9: `from scholartools.models import …` |
| `src/scholartools/services/fetch.py` | line 6: `from scholartools.models import …` |
| `src/scholartools/services/search.py` | line 6: `from scholartools.models import …` |
| `src/scholartools/services/files.py` | line 12: `from scholartools.models import …`; also line 3 prose comment mentions "scholartools original" |
| `src/scholartools/services/store.py` | line 3: `from scholartools.models import …`; line 13: `from scholartools.services import citekeys` |
| `src/scholartools/services/citekeys.py` | lives inside directory; verify no internal imports (not read, but affected by directory rename) |
| `src/scholartools/apis/anthropic_extract.py` | line 8: `from scholartools.ports import …` |
| `src/scholartools/apis/crossref.py` | line 3: `from scholartools.ports import …`; line 9: User-Agent header string `"scholartools/0.1 (mailto:{email})"` — this is also an externally visible identifier sent to Crossref API |
| `src/scholartools/apis/arxiv.py` | line 6: `from scholartools.ports import …` |
| `src/scholartools/apis/semantic_scholar.py` | line 3: `from scholartools.ports import …` |
| `src/scholartools/apis/google_books.py` | line 5: `from scholartools.ports import …` |
| `src/scholartools/apis/latindex.py` | line 3: `from scholartools.ports import …` |
| `src/scholartools/mcp.py` | referenced in manifest.json as entry point; must move to `src/scholartools/mcp.py` |

### 2. Python imports — tests/

| file | lines | reason |
|------|-------|--------|
| `tests/unit/test_search.py` | 5–6 | `from scholartools.models import …`, `from scholartools.services.search import …` |
| `tests/unit/test_fetch.py` | 3–4 | `from scholartools.models import …`, `from scholartools.services.fetch import …` |
| `tests/unit/test_config.py` | 5; 16, 37, 45, 55, 62, 69 | `from scholartools.config import …`; env var name `SCHOLARTOOLS_CONFIG` in 6 monkeypatch calls |
| `tests/unit/test_store.py` | 1–2 | `from scholartools.models import …`, `from scholartools.services.store import …` |
| `tests/unit/test_citekeys.py` | 1 | `from scholartools.services.citekeys import …` |
| `tests/unit/test_files.py` | 3–4 | `from scholartools.models import …`, `from scholartools.services.files import …` |
| `tests/unit/test_extract.py` | 5–6; 69, 95, 111, 123, 134 | `from scholartools.models import …`, `from scholartools.services.extract import …`; 5 `pytest.mock.patch` strings using `"scholartools.services.extract._extract_with_pdfplumber"` — these are dotted module path strings, not imports, and must match the installed package name exactly |
| `tests/unit/test_local_adapter.py` | 1 | `from scholartools.adapters.local import …` |
| `tests/unit/test_models.py` | 4 | `from scholartools.models import …` |

### 3. pyproject.toml and build config

| file | lines | reason |
|------|-------|--------|
| `pyproject.toml` | 6: `name = "scholartools"` | PyPI package name |
| `pyproject.toml` | 25: `packages = ["src/scholartools"]` | hatchling source package declaration |
| `uv.lock` | 6: `name = "scholartools"` | lockfile entry; regenerated automatically by `uv sync` after pyproject.toml change, but must be committed |

### 4. Config file paths — .scholartools/ discovery chain

| file | lines | reason |
|------|-------|--------|
| `src/scholartools/config.py` | 50: `SCHOLARTOOLS_CONFIG` env var | env var name; callers who set this must update their environment |
| `src/scholartools/config.py` | 52: `.scholartools/config.json` | project-local config discovery path |
| `src/scholartools/config.py` | 55: `~/.config/scholartools/config.json` | global config discovery path |
| `src/scholartools/config.py` | 74: `SCHOLARTOOLS_LIBRARY_PATH` | env var name |
| `src/scholartools/config.py` | 76: `SCHOLARTOOLS_FILES_DIR` | env var name |
| `/home/sabhz/archivo/idearium/.scholartools/config.json` | — | live runtime config file at vault root; if the discovery path changes to `.scholartools/config.json`, this file must be moved or the old path kept as a compatibility alias |
| `manifest.json` | 17–18, 31–43 | `SCHOLARTOOLS_LIBRARY_PATH`, `SCHOLARTOOLS_FILES_DIR` as user_config keys; these are the env vars injected into the MCP server process |

### 5. Docs — all .md files

| file | lines | reason |
|------|-------|--------|
| `CLAUDE.md` | 1, 6, 49, 50, 57, 82 | project heading, path references throughout |
| `README.md` | 1, 8–9, 15, 35–57, 68, 74 | package name in heading, git clone URL, import examples (`import scholartools`), config path `.scholartools/config.json`, MCP artifact name `scholartools.mcpb` |
| `docs/tech.md` | 1, 25, 31, 36, 66 | document heading; architecture diagram ASCII paths; prose |
| `docs/structure.md` | 1 | document heading |
| `docs/vision.md` | 1, 23 | heading and prose |
| `docs/product.md` | 1, 5, 33–34 | heading; prose; path `~/.scholartools/library.json`, `~/.scholartools/files/` |
| `docs/feats/001-core-library.md` | 8, 45, 62, 86, 243 | prose; field comment; config path in design doc |
| `docs/feats/002-staging-workflow.md` | 32, 38, 40, 43, 51, 70 | all `~/.scholartools/` path references in design doc |
| `docs/adr/001-hexagonal-result-types.md` | 7 | prose mention |
| `docs/adr/002-pdf-extraction.md` | 7 | prose mention |
| `docs/adr/003-httpx.md` | 7, 10 | prose mentions; `src/scholartools/apis/` path in doc |
| `docs/adr/004-pydantic-all-the-way.md` | 7, 12 | prose mention; `src/scholartools/models.py` path in doc |
| `specs/001-core-library.md` | 29 | `src/scholartools/` path in task description |
| `claude-progress.txt` | session 1 entry | multiple references to `src/scholartools/`, `scholartools.services`, etc. in completed task descriptions |

### 6. Tests — additional notes

Covered above under group 2. The `pytest.mock.patch` strings in `tests/unit/test_extract.py` at lines 69, 95, 111, 123, 134 (`"scholartools.services.extract._extract_with_pdfplumber"`) are runtime module path strings that Python resolves against the installed package. They will silently pass or fail to patch if not updated alongside the package rename.

### 7. Skills / shell scripts

**Inside the project (`scripts/scholartools/`):**

| file | lines | reason |
|------|-------|--------|
| `init.sh` | 8, 17 | echo string "scholartools health check"; `import scholartools` in inline python |

**Outside the project — vault-level (`/home/sabhz/archivo/idearium/`):**

| file | lines | reason |
|------|-------|--------|
| `scripts/research_session.py` | 1–3, 23, 55, 63, 90, 98, 121, 133, 138, 158, 178, 197, 217, 235 | docstring; `import scholartools`; 11 calls to `scholartools.*` functions |
| `scripts/rename_citekey.py` | 17, 34, 38 | `import scholartools`; 2 calls to `scholartools.*` functions |
| `scripts/backup_bib.sh` | 3, 11, 12, 43 | prose comment; `LIB_GIST_ID_FILE="$VAULT/.scholartools/gist_id"`; `LOG_FILE="$VAULT/.scholartools/backup_log.txt"`; gist description string "lib.json — idearium scholartools" |
| `claude/skills/scholartools/SKILL.md` | 2 | `name: scholartools-research` |
| `claude/skills/scholartools/research_session.py` | 2–3, 36, 41, 50, 73, 78, 86, 102, 110, 122, 127, 147–148, 168–169, 183, 189 | docstring; `import scholartools`; 10 calls to `scholartools.*` functions; this is a near-duplicate of `scripts/research_session.py` |
| `claude/skills/gestionar-citekeys/SKILL.md` | 35 | inline python one-liner: `import scholartools; print(scholartools.delete_reference(…))` |
| `CLAUDE.md` (vault root) | 77 | `.scholartools/gist_id` and `.scholartools/backup_log.txt` paths in backup instructions |

**Vault filesystem:**

| path | reason |
|------|--------|
| `/home/sabhz/archivo/idearium/.scholartools/config.json` | live runtime config directory used by `scripts/research_session.py`; if discovery path changes, this must move |
| `/home/sabhz/archivo/idearium/.scholartools/gist_id` | not confirmed to exist, but backup_bib.sh writes it here |
| `/home/sabhz/archivo/idearium/.scholartools/backup_log.txt` | not confirmed to exist, but backup_bib.sh writes it here |
| `claude/skills/scholartools/` | skill directory named after the package; may need to be renamed to `claude/skills/scholartools/` |

### 8. Other files

| file | lines | reason |
|------|-------|--------|
| `manifest.json` | 3, 11, 14, 17–18, 31, 37 | `"name": "scholartools"`; entry_point path `src/scholartools/mcp.py`; args path; three `SCHOLARTOOLS_*` env var keys |
| `feature_list.json` | — | no occurrences of `scholartools` — no change needed |
| `.venv/bin/activate` | 81, 101–102 | `VIRTUAL_ENV` path (absolute, self-corrects); `VIRTUAL_ENV_PROMPT="scholartools"` — cosmetic, auto-regenerated by `uv sync` |
| `.venv/bin/activate_this.py` | 49 | `"scholartools" or os.path.basename(base)` — cosmetic, auto-regenerated |
| `.venv/lib/python3.13/site-packages/_scholartools.pth` | — | filename contains package name; content is the `src/` path; auto-regenerated by `uv sync` after install |
| `.venv/lib/python3.13/site-packages/scholartools-0.2.0.dist-info/` | entire directory | dist-info directory named after package; all files inside (METADATA, RECORD, direct_url.json, uv_build.json, uv_cache.json) auto-regenerated by `uv sync` |
| `evals/rubric.md` | — | no occurrences of `scholartools` — no change needed |

---

## cross-dependencies

**Public import surface (callers outside the project):**
- `scripts/research_session.py`, `scripts/rename_citekey.py`, and both skill files do `import scholartools` at the top level. These resolve against the installed editable package. The rename breaks all of them simultaneously on the same `uv sync` that renames the package.
- `claude/skills/gestionar-citekeys/SKILL.md` contains a one-liner that does `import scholartools` — not a Python file but executed by copy-paste or shell eval.

**Env vars as implicit interface:**
- `SCHOLARTOOLS_CONFIG`, `SCHOLARTOOLS_LIBRARY_PATH`, `SCHOLARTOOLS_FILES_DIR` are read in `config.py` and declared in `manifest.json`. Any researcher's shell profile, `.env`, or MCP config that sets these will break silently — the library will fall back to defaults without warning.

**pytest.mock.patch strings:**
- The 5 patch strings in `tests/unit/test_extract.py` (`"scholartools.services.extract._extract_with_pdfplumber"`) are dotted import paths as strings. They are not caught by an IDE rename and will fail silently (patch applies to wrong module) rather than raising ImportError.

**MCP artifact name:**
- `README.md` line 74 references `scholartools.mcpb` as the distributed artifact name. If this is also the published binary name, downstream users' instructions would break.

**User-Agent header:**
- `src/scholartools/apis/crossref.py` line 9: `f"scholartools/0.1 (mailto:{email})"` — sent to Crossref's API on every request. Crossref uses this for rate-limit tracking and contact. Changing it is safe but means a new identity in their logs.

---

## data/schema implications

**Runtime config file path:**
- The discovery chain in `config.py` looks for `.scholartools/config.json` (project-local) and `~/.config/scholartools/config.json` (global). The live vault config lives at `/home/sabhz/archivo/idearium/.scholartools/config.json`. If the rename changes these discovery paths to `.scholartools/config.json` and `~/.config/scholartools/config.json`, the existing config file becomes invisible and the library silently falls back to defaults (no error, no warning). This is a silent runtime regression.

**No schema changes to data files:**
- `lib.json`, `library.json`, and any stored reference JSON use CSL-JSON + the `_file` / `_warnings` fields from the `Reference` model. None of these fields embed the package name. Data files survive the rename untouched.

**dist-info directory name:**
- `scholartools-0.2.0.dist-info/` is named by convention `{name}-{version}.dist-info`. After rename and `uv sync`, uv will install `scholartools-0.2.0.dist-info/`. The old dist-info directory will be left behind unless `uv sync` cleans it up — worth verifying.

---

## risks

1. **Silent config loss** (HIGH): The config discovery path `.scholartools/config.json` is hardcoded. If it changes to `.scholartools/config.json`, the live vault config at `/home/sabhz/archivo/idearium/.scholartools/config.json` becomes invisible. The library falls back to defaults with no error. This silently changes `library_path` and `files_dir` for every live operation.

2. **Silent mock patch failure in tests** (MEDIUM): The 5 `pytest.mock.patch("scholartools.services.extract._extract_with_pdfplumber", …)` strings in `test_extract.py` will not raise an ImportError if not updated — they will patch the wrong or nonexistent module, causing tests to pass while not actually mocking the target. The test suite would show green with broken test coverage.

3. **Vault-level scripts break simultaneously** (MEDIUM): `scripts/research_session.py` and `scripts/rename_citekey.py` both do `import scholartools` at module level. They will fail with `ModuleNotFoundError` immediately after `uv sync` completes the rename, before any other changes are made to those files. Since these scripts are used by the researcher daily, there is zero tolerance window.

4. **Env vars set in researcher's environment** (MEDIUM): `SCHOLARTOOLS_CONFIG`, `SCHOLARTOOLS_LIBRARY_PATH`, `SCHOLARTOOLS_FILES_DIR` may be set in the researcher's `.zshrc`, `.env`, or Claude Desktop MCP config. These are external to the repository and cannot be found by grep. After rename, if env var names change to `SCHOLARTOOLS_*`, those variables will stop being read silently.

5. **Old dist-info leftover** (LOW): `.venv/lib/python3.13/site-packages/scholartools-0.2.0.dist-info/` may persist after the rename if uv does not automatically clean it up. Two dist-infos for different names pointing to the same editable install could confuse tooling.

6. **MCP artifact name in README** (LOW): `scholartools.mcpb` is mentioned as the distribution artifact. If this file is actually published or shared, downstream users would need to be notified.

7. **Crossref User-Agent string** (LOW): The string `"scholartools/0.1 (mailto:{email})"` is sent externally. Not a breaking change, but worth updating for consistency and honest identification.

8. **`claude/skills/scholartools/` directory name** (LOW): The skill directory is named `scholartools`. Renaming it is optional (it's not a Python import path), but leaving it creates a confusing inconsistency.

---

## open questions

1. **Config path strategy** — should the discovery chain change from `.scholartools/` to `.scholartools/`, or should both paths be checked for backward compatibility? The live vault config at `/home/sabhz/archivo/idearium/.scholartools/config.json` is the immediate concern. **Decision required before implementation.** If both paths are supported, this adds a permanent compatibility shim that conflicts with the lean code principle.

2. **Env var names** — should `SCHOLARTOOLS_CONFIG`, `SCHOLARTOOLS_LIBRARY_PATH`, `SCHOLARTOOLS_FILES_DIR` be renamed to `SCHOLARTOOLS_*`? The researcher may have these set in their environment outside the repo. Renaming them is a breaking change to any external configuration. **Explicit decision required — affects `config.py`, `manifest.json`, `tests/unit/test_config.py`, and any environment not under version control.**

3. **Vault `.scholartools/` directory migration** — if config paths change, the directory `/home/sabhz/archivo/idearium/.scholartools/` must be renamed to `.scholartools/`. This directory also contains `gist_id` and `backup_log.txt` used by `scripts/backup_bib.sh`. **Decision required: rename directory, update backup_bib.sh, or decouple backup dir from config dir.**

4. **`scripts/research_session.py` vs `claude/skills/scholartools/research_session.py`** — these appear to be near-duplicates. Should both be updated, and should the skill directory be renamed? **Not a blocker but must be decided to avoid inconsistency.**

5. **ADR required?** — the env var naming convention and config file path schema are architectural decisions that affect external integrators (researchers setting env vars, MCP users). If `SCHOLARTOOLS_*` → `SCHOLARTOOLS_*` and `.scholartools/` → `.scholartools/`, this is a breaking public API change in the configuration surface. **An ADR is recommended** to record the decision, rationale, and migration path. Suggested: `docs/adr/005-rename-to-scholartools.md`.

6. **Version bump** — the rename constitutes a breaking change in the package name (a new PyPI name). Should the version go from `0.2.0` to `0.3.0` or `1.0.0`? **Decision required before updating `pyproject.toml`.**

7. **GitHub repository name** — `README.md` contains `git clone https://github.com/abrahambahez/scholartools`. If the GitHub repo is also renamed, the clone URL changes. If not, the discrepancy between repo name and package name must be documented.
