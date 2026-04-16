# spec: 028-cli-help-descriptions — Improve CLI help text for agent consumption

## findings

The current CLI (completed in spec 012) has minimal help text. Subcommands and arguments lack domain-specific documentation that explains:
- **Domain terminology** — what is a "reference", "citekey", "staging", "library", "uid", "authority"?
- **Concrete inputs and outputs** — what format does `json` expect? What fields are required? What does merging actually do?
- **When to use each command** — `stage` vs `merge`, `attach` vs `reindex`?
- **Epistemological context** — why does loretools exist as distinct from other reference managers?

Current state (from loretools/cli/*.py):
- `refs` group: "manage references in the library" — vague, no arg help
- `extract` group: "extract metadata from a local file" — no detail on inputs/outputs
- `files` group: "manage files linked to references" — no explanation of attach/reindex workflow
- `staging` group: "manage staged references before merging" — no clarity on the staging workflow itself
- All subcommands (`add`, `list`, `filter`, etc.) lack `help=` text
- All arguments (`json`, `citekey`, `path`, etc.) lack `help=` text describing the format and domain role

An AI agent calling `lore --help` or `lore refs --help` cannot infer what a "citekey" is, why staging exists as a separate layer, or what the merge workflow validates. The agent reads product.md to learn context, but the CLI itself is opaque.

## objective

Add comprehensive, agent-friendly help text to every subcommand and argument across `loretools/cli/__init__.py`, `loretools/cli/refs.py`, `loretools/cli/files.py`, `loretools/cli/staging.py`, and `loretools/cli/extract.py`. Help text must:

1. Define domain terms inline (reference, citekey, staging, library, uid, authority, epistemological framework)
2. Specify concrete input/output formats (CSL-JSON structure for refs, expected return types)
3. Explain when and why to use each command in relation to others
4. Use "tool description" language: focus on what the command *does* and *returns*, not internal logic
5. Keep descriptions concise (1-2 sentences per command, 1 sentence per arg) while being specific
6. Mirror the epistemic perspective from product.md: references as claim structures, not database records

This is purely additive — no logic changes, no refactoring, no new dependencies. Every `add_parser()` call gets a `help=` parameter; every `add_argument()` call with a meaningful purpose gets `help=`.

Success: An agent reading `lore --help`, `lore refs --help`, `lore refs add --help`, etc., understands the domain model and can compose commands correctly without reading product.md.

## acceptance criteria (EARS format)

- when `lore --help` is called, the system must display all command groups with descriptions that define loretools' epistemic stance (e.g., references as claim structures, not database records)
- when `lore refs --help` is called, the system must list all `refs` subcommands with help text explaining what each does (e.g., `add` creates a new reference, `get` retrieves by citekey, `filter` searches by multiple predicates)
- when `lore refs add --help` is called, the system must show help text explaining that `json` argument expects CSL-JSON-compatible data and is required or stdin-readable, and should list example required fields
- when `lore refs get --help` is called, the system must show help text defining "citekey" as the human-readable identifier assigned during merge
- when `lore refs filter --help` is called, the system must show help text for each flag (`--query`, `--author`, `--year`, `--type`, `--has-file`, `--staging`, `--page`) explaining what each predicate does and when to combine them
- when `lore staging stage --help` is called, the system must explain that staging is the evaluation layer before library promotion, accepting the same JSON as `refs add` but not committing to the library
- when `lore staging merge --help` is called, the system must explain the merge workflow: schema validation, duplicate detection, file archival, citekey assignment, then library promotion; and `--omit` and `--allow-semantic` flag purposes
- when `lore files attach --help` is called, the system must explain that `citekey` refers to the reference identifier and `path` is the filesystem location of the file to link
- when `lore files reindex --help` is called, the system must explain that this audits the file archive and updates indexes (when to run: after manual file operations)
- when `lore extract --help` is called, the system must explain that `file_path` is a local PDF/EBOOK and the output is CSL-JSON metadata (or an error if extraction fails)
- all argument `help=` text must use consistent terminology: "reference" for epistemic objects, "citekey" for identifiers, "library" for committed records, "staging" for evaluation layer, "uid" for unique identifier

## tasks

- [ ] task-01: improve root parser and group descriptions in `loretools/cli/__init__.py` (blocks: none)
  - Update root `ArgumentParser` description to explain loretools as reference management for AI agents
  - Update each group description in `_DESCRIPTIONS` to define its role in the workflow
  - Example: `"refs"`: "Manage references in the production library. A reference is a claim structure (existence assertion, retrieval promise, authority type, epistemological framework). Add, retrieve, filter, or modify committed references by citekey."
  - One commit

- [ ] task-02: improve `refs` subcommand and argument help in `loretools/cli/refs.py` (blocks: none)
  - Add `help=` to each `add_parser()` call: `add`, `get`, `update`, `rename`, `delete`, `list`, `filter`
  - Add `help=` to each argument: `json` (CSL-JSON structure, required fields), `citekey` (human-readable identifier), `uid` (unique record ID for lookups), `--author`, `--year`, `--type`, `--has-file`, `--staging`, `--page`
  - Define CSL-JSON briefly in `add` help
  - Explain what `--staging` filter means (include unstaged records under evaluation)
  - One commit

- [ ] task-03: improve `files` subcommand and argument help in `loretools/cli/files.py` (blocks: none)
  - Add `help=` to each `add_parser()` call: `attach`, `detach`, `reindex`, `get`, `move`, `list`
  - Add `help=` to each argument: `citekey`, `path`, `dest_name`, `--page`
  - Explain the difference between `attach` (link a file) and `reindex` (audit and re-index the file archive)
  - Explain `dest_name` as the new filename in the archive (for rename/organization)
  - One commit

- [ ] task-04: improve `staging` subcommand and argument help in `loretools/cli/staging.py` (blocks: none)
  - Add `help=` to each `add_parser()` call: `stage`, `list-staged`, `delete-staged`, `merge`
  - Add `help=` to each argument: `json`, `citekey`, `file`, `--omit`, `--allow-semantic`, `--page`
  - Explain staging as the evaluation layer separate from the committed library
  - Explain merge workflow: validates schema, detects duplicates, archives files, assigns citekeys
  - Explain `--omit` as comma-separated citekeys to exclude from merge
  - Explain `--allow-semantic` as allowing merge of references whose duplicate check used fuzzy title/author matching (uid_confidence="semantic") rather than a stable identifier; requires manual review before enabling
  - One commit

- [ ] task-05: improve `extract` subcommand and argument help in `loretools/cli/extract.py` (blocks: none)
  - Add `help=` to `add_parser()` for `extract`: explain it parses a local PDF/EBOOK and returns CSL-JSON metadata
  - Add `help=` to `file_path` argument: explain it must be a filesystem path to a PDF or EBOOK file
  - Mention that extraction uses pdfplumber by default; vision-based extraction (fallback) requires loretools-llm plugin
  - One commit

- [ ] task-06: integration test that help text renders correctly for all commands (blocks: task-01 through task-05)
  - Create or update tests in `tests/unit/cli/` that call `parser --help` for each group and subcommand and verify no crashes
  - Verify that `help=` strings appear in `--help` output for sampled commands (`lore refs add --help`, `lore staging merge --help`, `lore files attach --help`)
  - One commit

## plugin compatibility

Future plugins will register CLI commands via Python entry points (`importlib.metadata.entry_points(group="loretools.cli")`). The core will discover them and call their `register(sub: argparse.ArgumentParser) -> None` function — the same signature every current CLI module exposes.

**Constraint:** do not alter the `register(sub)` signature in any CLI module during this implementation. It is the stable plugin contract. All help text must be written inside `register()` — no module-level helpers that plugins would need to replicate.

## ADR required?

No. This is purely descriptive documentation — no architectural or design decisions.

## risks

1. **Help text length.** If descriptions are too verbose, `--help` output becomes unreadable. Mitigation: keep each command help to 1–2 sentences, each argument help to 1 sentence. Use examples sparingly.

2. **Terminology consistency.** If help text uses "record", "object", "item", and "reference" interchangeably, agents get confused. Mitigation: enforce "reference" throughout for epistemic objects, "citekey" for IDs, "library" for committed store, "staging" for evaluation layer.

3. **Plugin reference clarity.** Vision-based extraction (fallback path in `extract`) requires the loretools-llm plugin; the CLI cannot detect plugin presence from help text. Mitigation: note this in the `extract` group description. `--allow-semantic` is core functionality, not plugin-dependent — it gates fuzzy-matched UIDs and requires no plugin.

4. **Outdated help text.** If product.md or the public API changes, help text will drift. Mitigation: this is accepted; help text is documentation and can be updated in follow-on tasks.

5. **No validation of help text quality.** Unlike code, help text cannot be linted for accuracy or consistency. Mitigation: reviewer reads all help text during review; any unclear or inconsistent text is flagged and revised before merge.
