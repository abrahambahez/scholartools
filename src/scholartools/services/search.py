import asyncio
import uuid

import httpx

from scholartools.models import LibraryCtx, Reference, SearchResult


async def search_references(
    query: str, ctx: LibraryCtx, sources: list[str] | None = None, limit: int = 10
) -> SearchResult:
    active = (
        [s for s in ctx.api_sources if s["name"] in sources]
        if sources
        else ctx.api_sources
    )
    if not active:
        return SearchResult(references=[], sources_queried=[], total_found=0, errors=[])

    per_source = max(1, limit // len(active))
    tasks = [_fetch_source(s, query, per_source) for s in active]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    seen_dois: set[str] = set()
    references: list[Reference] = []
    errors: list[str] = []
    sources_queried: list[str] = []

    for source, (records, error) in zip(active, results):
        sources_queried.append(source["name"])
        if error:
            errors.append(f"{source['name']}: {error}")
            continue
        for raw in records:
            doi = raw.get("DOI")
            if doi and doi in seen_dois:
                continue
            if doi:
                seen_dois.add(doi)
            ref = _to_reference(raw)
            references.append(ref)
            if len(references) >= limit:
                break

    return SearchResult(
        references=references[:limit],
        sources_queried=sources_queried,
        total_found=len(references),
        errors=errors,
    )


async def _fetch_source(
    source: dict, query: str, limit: int
) -> tuple[list[dict], str | None]:
    try:
        records = await source["search"](query, limit)
        return records, None
    except (httpx.HTTPError, ValueError, KeyError) as e:
        return [], str(e)


def _to_reference(raw: dict) -> Reference:
    if "id" not in raw:
        raw = {**raw, "id": f"ref{uuid.uuid4().hex[:6]}"}
    if "type" not in raw:
        raw = {**raw, "type": "article-journal"}
    return Reference.model_validate(raw)
