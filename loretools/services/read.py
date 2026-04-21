import asyncio
from pathlib import Path

import pymupdf
import pymupdf4llm

from loretools.models import LibraryCtx, ReadBatchResult, ReadResult

_PDF_SUFFIXES = {".pdf"}
_MARKITDOWN_SUFFIXES = {".epub", ".docx", ".doc", ".html", ".htm", ".pptx"}
_QUALITY_THRESHOLD = 0.4
_CHARS_PER_PAGE_DIVISOR = 500
_EMPTY_HEADER_THRESHOLD = 10


def _check_quality(text: str, page_count: int) -> float:
    chars_per_page = len(text) / max(page_count, 1)
    density_score = min(chars_per_page / _CHARS_PER_PAGE_DIVISOR, 1.0)

    lines = text.splitlines()
    headers = [
        i for i, ln in enumerate(lines) if ln.startswith("# ") or ln.startswith("## ")
    ]
    empty_header_ratio = 0.0
    if len(headers) >= _EMPTY_HEADER_THRESHOLD:
        empty_count = sum(
            1
            for i in headers
            if not any(lines[j].strip() for j in range(i + 1, min(i + 3, len(lines))))
        )
        empty_header_ratio = empty_count / len(headers)

    return density_score * (1.0 - empty_header_ratio * 0.5)


async def _convert_with_markitdown(file_path: str) -> tuple[str, str]:
    try:
        from markitdown import MarkItDown

        md = MarkItDown().convert(file_path).text_content
        return md, ""
    except Exception as e:
        return "", str(e)


async def _convert_with_pymupdf4llm(
    file_path: str, page_count: int
) -> tuple[str, float]:
    try:
        md = pymupdf4llm.to_markdown(file_path)
    except Exception:
        return "", 0.0
    score = _check_quality(md, page_count)
    if score < _QUALITY_THRESHOLD:
        return "", 0.0
    return md, score


async def _convert_with_pymupdf(file_path: str) -> tuple[str, int]:
    try:
        with pymupdf.open(file_path) as doc:
            page_count = doc.page_count
            pages = [
                f"---\n[page {i}]\n\n{doc[i].get_text()}"
                for i in range(page_count)
            ]
        return "\n\n".join(pages), page_count
    except Exception:
        return "", 0


async def read_reference(
    citekey: str, ctx: LibraryCtx, force: bool = False
) -> ReadResult:
    sources_read_dir = Path(ctx.sources_read_dir)
    sources_raw_dir = Path(ctx.sources_raw_dir)

    if not force:
        for ext in ("md", "txt"):
            cached = sources_read_dir / f"{citekey}.source.{ext}"
            if cached.exists():
                return ReadResult(
                    citekey=citekey,
                    output_path=str(cached),
                    format=ext,
                    method=None,
                    quality_score=None,
                    page_count=None,
                )

    records = await ctx.read_all()
    record = next((r for r in records if r.get("id") == citekey), None)
    if record is None:
        return ReadResult(citekey=citekey, error=f"not found: {citekey}")

    file_rec = record.get("_file")
    if not file_rec:
        return ReadResult(citekey=citekey, error="no file linked")

    raw_path = file_rec["path"]
    file_path = Path(raw_path) if Path(raw_path).is_absolute() else sources_raw_dir / raw_path
    if not file_path.exists():
        return ReadResult(citekey=citekey, error=f"file not found: {file_path}")

    suffix = file_path.suffix.lower()

    if suffix in _MARKITDOWN_SUFFIXES:
        md, err = await _convert_with_markitdown(str(file_path))
        if err:
            return ReadResult(citekey=citekey, error=f"markitdown conversion failed: {err}")
        sources_read_dir.mkdir(parents=True, exist_ok=True)
        out = sources_read_dir / f"{citekey}.source.md"
        out.write_text(md, encoding="utf-8")
        return ReadResult(
            citekey=citekey,
            output_path=str(out),
            format="md",
            method="markitdown",
            quality_score=_check_quality(md, 1),
            page_count=None,
        )

    if suffix not in _PDF_SUFFIXES:
        return ReadResult(citekey=citekey, error=f"unsupported format: {suffix}")

    try:
        with pymupdf.open(str(file_path)) as doc:
            page_count = doc.page_count
    except Exception:
        return ReadResult(citekey=citekey, error=f"cannot open file: {file_path}")

    md, score = await _convert_with_pymupdf4llm(str(file_path), page_count)

    if md:
        sources_read_dir.mkdir(parents=True, exist_ok=True)
        out = sources_read_dir / f"{citekey}.source.md"
        out.write_text(md, encoding="utf-8")
        return ReadResult(
            citekey=citekey,
            output_path=str(out),
            format="md",
            method="pymupdf4llm",
            quality_score=score,
            page_count=page_count,
        )

    text, page_count = await _convert_with_pymupdf(str(file_path))
    if not text:
        return ReadResult(citekey=citekey, error="extraction produced no content")

    txt_score = _check_quality(text, page_count)
    sources_read_dir.mkdir(parents=True, exist_ok=True)
    out = sources_read_dir / f"{citekey}.source.txt"
    out.write_text(text, encoding="utf-8")
    return ReadResult(
        citekey=citekey,
        output_path=str(out),
        format="txt",
        method="pymupdf",
        quality_score=txt_score,
        page_count=page_count,
    )


async def read_references(
    citekeys: list[str], ctx: LibraryCtx, force: bool = False
) -> ReadBatchResult:
    results = await asyncio.gather(
        *[read_reference(ck, ctx, force=force) for ck in citekeys],
        return_exceptions=False,
    )
    failed = sum(1 for r in results if r.error is not None)
    return ReadBatchResult(
        results=list(results),
        total_read=len(results) - failed,
        total_failed=failed,
    )
