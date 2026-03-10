from unittest.mock import AsyncMock

from scholartools.models import LibraryCtx
from scholartools.services.store import filter_references

_RECORDS = [
    {
        "id": "smith2020",
        "type": "article-journal",
        "title": "Climate Change and Society",
        "author": [{"family": "Smith", "given": "John"}],
        "issued": {"date-parts": [[2020]]},
        "_file": {
            "path": "smith2020.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 100,
            "added_at": "2024-01-01",
        },
    },
    {
        "id": "garcia2021",
        "type": "book",
        "title": "Urban Ecology",
        "author": [{"family": "García", "given": "Ana"}],
        "issued": {"date-parts": [[2021]]},
    },
    {
        "id": "jones_etal2021",
        "type": "article-journal",
        "title": "Social Change in Cities",
        "author": [
            {"family": "Jones", "given": "Bob"},
            {"family": "García", "given": "Luis"},
        ],
        "issued": {"date-parts": [[2021]]},
    },
    {
        "id": "anon2019",
        "type": "report",
        "title": None,
        "author": [{"literal": "Anonymous Group"}],
        "issued": {"date-parts": [[2019]]},
    },
]

_STAGED = [
    {
        "id": "staged2022",
        "type": "article-journal",
        "title": "Staged Climate Paper",
        "author": [{"family": "Rivera", "given": "M"}],
        "issued": {"date-parts": [[2022]]},
    },
]


def make_ctx(library=None, staging=None):
    lib = list(library if library is not None else _RECORDS)
    stg = list(staging if staging is not None else _STAGED)

    async def noop(*_):
        pass

    return LibraryCtx(
        read_all=AsyncMock(return_value=lib),
        write_all=noop,
        copy_file=noop,
        delete_file=noop,
        rename_file=noop,
        list_file_paths=AsyncMock(return_value=[]),
        files_dir="data/files",
        staging_read_all=AsyncMock(return_value=stg),
        staging_write_all=noop,
        staging_copy_file=noop,
        staging_delete_file=noop,
        staging_dir="data/staging",
        api_sources=[],
    )


async def test_no_args_returns_all():
    ctx = make_ctx()
    result = await filter_references(ctx)
    assert result.total == len(_RECORDS)


async def test_query_matches_title_substring():
    ctx = make_ctx()
    result = await filter_references(ctx, query="climate")
    assert result.total == 1
    assert result.references[0].citekey == "smith2020"


async def test_query_is_case_insensitive():
    ctx = make_ctx()
    result = await filter_references(ctx, query="CLIMATE")
    assert result.total == 1


async def test_query_no_match_returns_empty():
    ctx = make_ctx()
    result = await filter_references(ctx, query="zzznomatch")
    assert result.total == 0
    assert result.references == []


async def test_query_skips_none_title():
    ctx = make_ctx()
    result = await filter_references(ctx, query="anything")
    citekeys = [r.citekey for r in result.references]
    assert "anon2019" not in citekeys


async def test_author_matches_family():
    ctx = make_ctx()
    result = await filter_references(ctx, author="garcía")
    assert result.total == 2
    citekeys = {r.citekey for r in result.references}
    assert citekeys == {"garcia2021", "jones_etal2021"}


async def test_author_matches_literal():
    ctx = make_ctx()
    result = await filter_references(ctx, author="anonymous")
    assert result.total == 1
    assert result.references[0].citekey == "anon2019"


async def test_year_exact_match():
    ctx = make_ctx()
    result = await filter_references(ctx, year=2021)
    assert result.total == 2
    assert all(r.year == 2021 for r in result.references)


async def test_ref_type_exact():
    ctx = make_ctx()
    result = await filter_references(ctx, ref_type="book")
    assert result.total == 1
    assert result.references[0].citekey == "garcia2021"


async def test_has_file_true():
    ctx = make_ctx()
    result = await filter_references(ctx, has_file=True)
    assert result.total == 1
    assert result.references[0].citekey == "smith2020"


async def test_has_file_false():
    ctx = make_ctx()
    result = await filter_references(ctx, has_file=False)
    assert result.total == len(_RECORDS) - 1
    assert all(not r.has_file for r in result.references)


async def test_and_combination():
    ctx = make_ctx()
    result = await filter_references(ctx, author="garcía", year=2021, ref_type="book")
    assert result.total == 1
    assert result.references[0].citekey == "garcia2021"


async def test_and_combination_no_match():
    ctx = make_ctx()
    result = await filter_references(ctx, author="smith", year=2021)
    assert result.total == 0


async def test_staging_true_queries_staging_store():
    ctx = make_ctx()
    result = await filter_references(ctx, staging=True)
    assert result.total == len(_STAGED)
    assert result.references[0].citekey == "staged2022"


async def test_staging_false_queries_library():
    ctx = make_ctx()
    result = await filter_references(ctx, staging=False)
    assert result.total == len(_RECORDS)


async def test_staging_with_predicate():
    ctx = make_ctx()
    result = await filter_references(ctx, query="climate", staging=True)
    assert result.total == 1
    assert result.references[0].citekey == "staged2022"


async def test_pagination():
    records = [{"id": f"r{i:03}", "type": "article-journal"} for i in range(25)]
    ctx = make_ctx(library=records)
    p1 = await filter_references(ctx, page=1)
    p3 = await filter_references(ctx, page=3)
    assert p1.total == 25
    assert p1.pages == 3
    assert len(p1.references) == 10
    assert len(p3.references) == 5
