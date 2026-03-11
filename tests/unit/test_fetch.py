from unittest.mock import AsyncMock

from scholartools.models import LibraryCtx
from scholartools.services.fetch import fetch_reference


def make_ctx(crossref=None, arxiv=None, semantic_scholar=None) -> LibraryCtx:
    async def noop(*_):
        pass

    sources = []
    if crossref is not None:
        sources.append({"name": "crossref", "search": noop, "fetch": crossref})
    if semantic_scholar is not None:
        sources.append(
            {"name": "semantic_scholar", "search": noop, "fetch": semantic_scholar}
        )
    if arxiv is not None:
        sources.append({"name": "arxiv", "search": noop, "fetch": arxiv})

    return LibraryCtx(
        read_all=AsyncMock(return_value=[]),
        write_all=noop,
        copy_file=noop,
        delete_file=noop,
        rename_file=noop,
        list_file_paths=AsyncMock(return_value=[]),
        files_dir="data/files",
        api_sources=sources,
    )


async def test_fetch_doi_routes_to_crossref():
    mock = AsyncMock(return_value={"title": "Paper", "type": "article-journal"})
    ctx = make_ctx(crossref=mock)
    result = await fetch_reference("10.1234/test", ctx)
    assert result.error is None
    assert result.source == "crossref"
    mock.assert_called_once_with("10.1234/test")


async def test_fetch_arxiv_id_routes_to_arxiv():
    mock = AsyncMock(return_value={"title": "ArXiv Paper"})
    ctx = make_ctx(arxiv=mock)
    result = await fetch_reference("2301.00001", ctx)
    assert result.source == "arxiv"
    mock.assert_called_once()


async def test_fetch_issn_routes_to_crossref():
    mock = AsyncMock(return_value={"title": "Journal"})
    ctx = make_ctx(crossref=mock)
    result = await fetch_reference("1234-567X", ctx)
    assert result.source == "crossref"


async def test_fetch_not_found():
    ctx = make_ctx(crossref=AsyncMock(return_value=None))
    result = await fetch_reference("10.1/missing", ctx)
    assert result.reference is None
    assert "not found" in result.error


async def test_fetch_no_matching_source():
    ctx = make_ctx()
    result = await fetch_reference("10.1/doi", ctx)
    assert result.reference is None
    assert result.error is not None


async def test_fetch_api_error_returns_result_not_raises():
    import httpx

    ctx = make_ctx(crossref=AsyncMock(side_effect=httpx.ConnectError("timeout")))
    result = await fetch_reference("10.1/x", ctx)
    assert result.reference is None
    assert result.error is not None


async def test_fetch_assigns_id_and_type():
    ctx = make_ctx(crossref=AsyncMock(return_value={"title": "No ID or Type"}))
    result = await fetch_reference("10.1/x", ctx)
    assert result.reference.id.startswith("ref")
    assert result.reference.type == "article-journal"
