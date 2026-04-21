# spec: 030-markitdown-read-adapter — multi-format source extraction with markitdown

## findings

From the reading skills analysis (2026-04-20):

**The problem with the current `read` operation:** `read_reference()` (spec-029) calls `pymupdf.open()` unconditionally. Any non-PDF file attached to a reference (EPUB, DOCX, HTML clip) silently returns `error: "cannot open file"`. The reading skills promise "PDF or EPUB" as equivalent source types — that promise is currently broken.

**Why markitdown, not a native EPUB library:** markitdown (Microsoft, 113K stars, v0.1.5) is an LLM-pipeline-focused multi-format converter that handles EPUB, DOCX, HTML, PPTX, and more under a single dispatch API. The extensibility argument is the key one: as new source types appear (field notes in DOCX, web clips as HTML, syllabi in PPTX), adding support is an optional-dependency install rather than a new adapter per format.

**Why NOT replacing the PDF path:** The existing pymupdf4llm → pymupdf fallback was calibrated specifically against academic PDF behavior (OCR layer detection, chars-per-page heuristic, empty-header-ratio). markitdown's PDF backend (`pdfminer.six`) has different characteristics. The quality gate would need recalibration from scratch. There is no gain from replacing a proven path.

**Architecture:** `read_reference()` dispatches by file extension. PDFs take the existing path unchanged. Everything else goes to markitdown. The quality check function `_check_quality()` applies to all paths — markitdown output is scored the same way.

**`lore read` CLI command:** The Python `read_reference()` function has no CLI surface yet. Skills call the CLI, so a `lore read` command must be added as part of this spec.

**markitdown output format:** markitdown always returns Markdown. Output is saved as `{citekey}.source.md` regardless of input format (no `.txt` fallback needed — markitdown does not fail silently the way pymupdf4llm does on OCR PDFs). If markitdown raises, return an error result.

**Dependency scope:** Add `markitdown[epub]` now. Extend extras as more formats are tested. Do not add `markitdown[pdf]` — keep pymupdf as the PDF backend.

**Page count for non-PDF:** pymupdf gives `page_count` for PDFs. For non-PDF formats, `page_count` is `None` — markitdown does not expose page boundaries. Locators in non-PDF sources use chapter/section markers, not page numbers; this is acceptable and documented in the reading skills.

## objective

Add markitdown as an additive read adapter for non-PDF source files. Keep the PDF path (spec-029) entirely unchanged. Add `lore read` CLI command. Skills can now run `lore read <citekey>` on any attached source type and receive a readable text file.

## acceptance criteria (EARS format)

- when `read_reference(citekey, ctx)` is called on a reference with a linked PDF, the system must use the existing pymupdf4llm → pymupdf path unchanged; markitdown must not be called
- when `read_reference(citekey, ctx)` is called on a reference with a linked EPUB, DOCX, or HTML file, the system must use markitdown to convert it, write `{citekey}.source.md` to `sources/read/`, and return `ReadResult(format="md", method="markitdown")`
- when markitdown raises on conversion, the system must return `ReadResult(citekey, error="markitdown conversion failed: {msg}")` and never raise
- when `read_reference` is called on a non-PDF file that is already converted (output file exists), the system must return the cached result without re-converting unless `force=True`
- when `lore read <citekey>` is called, the CLI must invoke `read_reference(citekey)` and print the `ReadResult` as JSON to stdout
- when `lore read <citekey> --force` is called, the CLI must pass `force=True` to `read_reference`
- when `lore read <citekey>` is called and the result has a non-null `error`, the CLI must print the JSON result and exit with code 1
- when `ReadResult.method` is `"markitdown"`, `page_count` must be `None`; `format` must be `"md"`
- when the quality check is applied to markitdown output, the same `_check_quality` function must be used; `quality_score` is recorded in `ReadResult` but does not trigger a fallback (no fallback exists for non-PDF formats)

## tasks

- [ ] task-01: add `markitdown[epub]` dependency (blocks: none)
  - In `pyproject.toml`, add `"markitdown[epub]"` to `dependencies`
  - Run `uv sync` to verify resolution
  - tests: import `markitdown` in a unit test fixture — confirms install

- [ ] task-02: add `"markitdown"` as a valid `method` Literal in `ReadResult` (blocks: none)
  - In `loretools/models.py`, update `ReadResult.method` from `Literal["pymupdf4llm", "pymupdf"]` to `Literal["pymupdf4llm", "pymupdf", "markitdown"]`
  - tests: field validation accepts `"markitdown"`, rejects unknown strings

- [ ] task-03: implement `_convert_with_markitdown` (blocks: task-01, task-02)
  - In `loretools/services/read.py`:
    ```python
    async def _convert_with_markitdown(file_path: str) -> tuple[str, str]:
        # returns (markdown_text, error_msg_or_empty)
    ```
  - Import `markitdown` inside the function body (lazy import — keeps startup fast if markitdown is slow to import)
  - Call `MarkItDown().convert(file_path).text_content`; on any exception return `("", str(e))`
  - No quality gate fallback: return the text as-is, quality score is informational only
  - tests: EPUB fixture produces non-empty markdown; exception path returns empty string and error message

- [ ] task-04: update `read_reference` dispatch logic (blocks: task-03)
  - In `loretools/services/read.py`, before the pymupdf block, check the file extension:
    ```python
    _PDF_SUFFIXES = {".pdf"}
    _MARKITDOWN_SUFFIXES = {".epub", ".docx", ".doc", ".html", ".htm", ".pptx"}
    ```
  - If suffix not in `_PDF_SUFFIXES` and in `_MARKITDOWN_SUFFIXES`: call `_convert_with_markitdown`; write `.source.md`; return `ReadResult(method="markitdown", format="md", page_count=None, quality_score=_check_quality(md, 1))`
  - If suffix not in either set: return `ReadResult(citekey, error=f"unsupported format: {suffix}")`
  - PDF path: unchanged
  - tests: EPUB dispatch hits markitdown path; PDF dispatch hits pymupdf path; unknown extension returns error result

- [ ] task-05: add `lore read` CLI command (blocks: task-04)
  - Create `loretools/cli/read.py`:
    - `_read(args)`: calls `loretools.read_reference(args.citekey, force=args.force)`; prints JSON; exits 1 on error
    - `register(sub)`: adds `citekey` positional and `--force` flag
  - In `loretools/cli/__init__.py`: import and register `read` group alongside `refs`, `files`, etc.
  - Add `"read"` to `_GROUPS` and `_DESCRIPTIONS` with description: `"Convert an attached source file to agent-readable text. Output is cached in sources/read/ and reused on subsequent calls."`
  - tests: `lore read <citekey>` outputs valid JSON; `--force` re-converts; error result exits 1

- [ ] task-06: update reading skills reference documentation (blocks: task-05)
  - Both skills already reference `lore read <citekey>` — no changes needed if skills were updated in the wiki layer design session
  - Verify `skills/en/structural-reading/SKILL.md` and `skills/es/lectura-estructural/SKILL.md` reference `lore read` correctly

- [ ] task-07: update CHANGELOG (blocks: task-05)
  - Add entry under `[Unreleased]`:
    - `### Added`: markitdown EPUB/DOCX/HTML support in `read_reference`; `lore read` CLI command
    - `### Skills`: structural-reading and lectura-estructural updated to use `lore read` CLI

## ADR required?

No. This is an additive adapter change. The dispatch-by-extension pattern is straightforward and requires no architectural decision record.

## risks

- **markitdown EPUB quality on academic texts**: markitdown's EPUB output quality on complex academic texts (footnotes, scholarly apparatus) is untested. The quality score will surface this — if scores are consistently low, reconsider or add post-processing.
- **markitdown API stability**: v0.1.5 — Microsoft-backed but pre-1.0. Pin a minimum version in pyproject.toml (`markitdown[epub]>=0.1.5`). Watch for breaking changes on the `text_content` attribute.
- **Import time**: markitdown pulls in several optional backends. The lazy import in `_convert_with_markitdown` prevents this from slowing PDF-only workflows.
