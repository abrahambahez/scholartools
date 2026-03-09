from unittest.mock import AsyncMock

import httpx

from scholartools.models import ApiSource, LibraryCtx
from scholartools.services.search import search_references


def make_source(
    name: str, records: list[dict] | None = None, error: bool = False
) -> ApiSource:
    async def search_fn(query, limit):
        if error:
            raise httpx.ConnectError("api down")
        return (records or [])[:limit]

    return {"name": name, "search": search_fn, "fetch": AsyncMock(return_value=None)}


def make_ctx(*sources: ApiSource) -> LibraryCtx:
    async def noop(*_):
        pass

    return LibraryCtx(
        read_all=AsyncMock(return_value=[]),
        write_all=noop,
        copy_file=noop,
        delete_file=noop,
        rename_file=noop,
        list_file_paths=AsyncMock(return_value=[]),
        files_dir="data/files",
        api_sources=list(sources),
    )


async def test_search_no_sources_returns_empty():
    ctx = make_ctx()
    result = await search_references("query", ctx)
    assert result.total_found == 0
    assert result.references == []


async def test_search_single_source():
    records = [
        {"title": "Paper A", "DOI": "10.1/a"},
        {"title": "Paper B", "DOI": "10.1/b"},
    ]
    ctx = make_ctx(make_source("crossref", records))
    result = await search_references("infrastructure", ctx, limit=2)
    assert result.total_found == 2
    assert result.errors == []
    assert "crossref" in result.sources_queried


async def test_search_deduplicates_by_doi():
    records = [{"title": "Paper A", "DOI": "10.1/dup"}]
    ctx = make_ctx(
        make_source("crossref", records), make_source("semantic_scholar", records)
    )
    result = await search_references("query", ctx, limit=10)
    dois = [r.DOI for r in result.references if r.DOI]
    assert len(dois) == len(set(dois))


async def test_search_source_filter():
    ctx = make_ctx(
        make_source("crossref", [{"title": "CR"}]),
        make_source("arxiv", [{"title": "AX"}]),
    )
    result = await search_references("query", ctx, sources=["crossref"])
    assert "arxiv" not in result.sources_queried
    assert result.total_found >= 1


async def test_search_failed_source_non_fatal():
    ctx = make_ctx(
        make_source("crossref", [{"title": "OK", "DOI": "10.1/ok"}]),
        make_source("arxiv", error=True),
    )
    result = await search_references("query", ctx, limit=10)
    assert any("arxiv" in e for e in result.errors)
    assert result.total_found >= 1  # crossref still returned


async def test_search_respects_limit():
    records = [{"title": f"Paper {i}", "DOI": f"10.1/{i}"} for i in range(20)]
    ctx = make_ctx(make_source("crossref", records))
    result = await search_references("query", ctx, limit=5)
    assert len(result.references) <= 5


async def test_search_assigns_temp_id_when_missing():
    ctx = make_ctx(make_source("crossref", [{"title": "No ID"}]))
    result = await search_references("query", ctx)
    assert all(r.id for r in result.references)
