import re
import uuid

import httpx

from scholartools.models import FetchResult, LibraryCtx, Reference

_DOI_RE = re.compile(r"^10\.\d{4,}/")
_ARXIV_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
_ISSN_RE = re.compile(r"^\d{4}-\d{3}[\dX]$")
_ISBN_RE = re.compile(r"^(?:ISBN[:\s-]*)?[\dX\-]{10,17}$", re.IGNORECASE)


async def fetch_reference(identifier: str, ctx: LibraryCtx) -> FetchResult:
    identifier = identifier.strip()
    source_name, fetch_fn = _route(identifier, ctx)

    if fetch_fn is None:
        return FetchResult(error=f"no source available for identifier: {identifier}")

    try:
        raw = await fetch_fn(identifier)
    except (httpx.HTTPError, ValueError, KeyError) as e:
        return FetchResult(error=str(e), source=source_name)

    if raw is None:
        return FetchResult(error=f"not found: {identifier}", source=source_name)

    raw.setdefault("id", f"ref{uuid.uuid4().hex[:6]}")
    raw.setdefault("type", "article-journal")
    return FetchResult(reference=Reference.model_validate(raw), source=source_name)


def _route(identifier: str, ctx: LibraryCtx) -> tuple[str | None, object]:
    sources = {s["name"]: s for s in ctx.api_sources}

    if _DOI_RE.match(identifier):
        for name in ("crossref", "semantic_scholar"):
            if name in sources:
                return name, sources[name]["fetch"]

    if _ARXIV_RE.match(identifier):
        if "arxiv" in sources:
            return "arxiv", sources["arxiv"]["fetch"]

    if _ISSN_RE.match(identifier):
        if "latindex" in sources:
            return "latindex", sources["latindex"]["fetch"]
        if "crossref" in sources:
            return "crossref", sources["crossref"]["fetch"]

    if _is_isbn(identifier):
        if "google_books" in sources:
            return "google_books", sources["google_books"]["fetch"]

    if "crossref" in sources:
        return "crossref", sources["crossref"]["fetch"]

    return None, None


def _is_isbn(identifier: str) -> bool:
    cleaned = (
        identifier.upper()
        .replace("ISBN:", "")
        .replace("ISBN", "")
        .replace("-", "")
        .replace(" ", "")
        .strip()
    )
    return len(cleaned) in (10, 13) and cleaned.rstrip("X").isdigit()
