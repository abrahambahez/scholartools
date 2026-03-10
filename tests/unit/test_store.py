from scholartools.models import LibraryCtx
from scholartools.services.store import (
    add_reference,
    delete_reference,
    get_reference,
    list_references,
    rename_reference,
    update_reference,
)


def make_ctx(initial: list[dict] | None = None):
    store = list(initial or [])

    async def read_all():
        return list(store)

    async def write_all(records):
        store.clear()
        store.extend(records)

    async def noop(*_):
        pass

    return LibraryCtx(
        read_all=read_all,
        write_all=write_all,
        copy_file=noop,
        delete_file=noop,
        rename_file=noop,
        list_file_paths=lambda _: [],
        files_dir="data/files",
        api_sources=[],
    ), store


async def test_add_generates_citekey():
    ctx, store = make_ctx()
    ref = {
        "type": "article-journal",
        "author": [{"family": "Smith"}],
        "issued": {"date-parts": [[2020]]},
    }
    result = await add_reference(ref, ctx)
    assert result.error is None
    assert result.citekey == "smith2020"
    assert store[0]["id"] == "smith2020"


async def test_add_uses_provided_id():
    ctx, store = make_ctx()
    result = await add_reference({"id": "mykey", "type": "book"}, ctx)
    assert result.citekey == "mykey"


async def test_add_rejects_duplicate():
    ctx, _ = make_ctx([{"id": "smith2020", "type": "book"}])
    result = await add_reference({"id": "smith2020", "type": "article-journal"}, ctx)
    assert result.error is not None
    assert "duplicate" in result.error


async def test_add_resolves_collision():
    ctx, _ = make_ctx([{"id": "smith2020", "type": "book"}])
    ref = {
        "type": "article-journal",
        "author": [{"family": "Smith"}],
        "issued": {"date-parts": [[2020]]},
    }
    result = await add_reference(ref, ctx)
    assert result.citekey == "smith2020a"


async def test_get_found():
    ctx, _ = make_ctx([{"id": "smith2020", "type": "book", "title": "A Book"}])
    result = await get_reference("smith2020", ctx)
    assert result.error is None
    assert result.reference.id == "smith2020"


async def test_get_not_found():
    ctx, _ = make_ctx()
    result = await get_reference("missing", ctx)
    assert result.reference is None
    assert "not found" in result.error


async def test_get_populates_warnings_on_partial():
    ctx, _ = make_ctx([{"id": "x", "type": "book"}])
    result = await get_reference("x", ctx)
    assert result.reference is not None
    assert any("title" in w for w in result.reference.warnings)


async def test_update_merges_fields():
    ctx, store = make_ctx([{"id": "x", "type": "book", "title": "Old"}])
    result = await update_reference("x", {"title": "New"}, ctx)
    assert result.error is None
    assert store[0]["title"] == "New"


async def test_update_rejects_id_change():
    ctx, _ = make_ctx([{"id": "x", "type": "book"}])
    result = await update_reference("x", {"id": "y"}, ctx)
    assert result.error is not None


async def test_update_not_found():
    ctx, _ = make_ctx()
    result = await update_reference("missing", {"title": "X"}, ctx)
    assert result.error is not None


async def test_delete_removes_record():
    ctx, store = make_ctx([{"id": "x", "type": "book"}, {"id": "y", "type": "book"}])
    result = await delete_reference("x", ctx)
    assert result.deleted is True
    assert len(store) == 1
    assert store[0]["id"] == "y"


async def test_delete_not_found():
    ctx, _ = make_ctx()
    result = await delete_reference("missing", ctx)
    assert result.deleted is False
    assert result.error is not None


async def test_list_returns_all():
    ctx, _ = make_ctx([{"id": "a", "type": "book"}, {"id": "b", "type": "book"}])
    result = await list_references(ctx)
    assert result.total == 2
    assert {r.citekey for r in result.references} == {"a", "b"}


async def test_list_empty():
    ctx, _ = make_ctx()
    result = await list_references(ctx)
    assert result.total == 0
    assert result.references == []


async def test_list_sorted_by_citekey():
    ctx, _ = make_ctx([{"id": "z", "type": "book"}, {"id": "a", "type": "book"}])
    result = await list_references(ctx)
    assert result.references[0].citekey == "a"
    assert result.references[1].citekey == "z"


async def test_list_pagination():
    records = [{"id": f"ref{i:02d}", "type": "book"} for i in range(25)]
    ctx, _ = make_ctx(records)
    p1 = await list_references(ctx, page=1)
    p3 = await list_references(ctx, page=3)
    assert p1.total == 25
    assert p1.pages == 3
    assert len(p1.references) == 10
    assert len(p3.references) == 5


async def test_list_page_out_of_range_returns_last_page():
    records = [{"id": f"ref{i:02d}", "type": "book"} for i in range(5)]
    ctx, _ = make_ctx(records)
    result = await list_references(ctx, page=99)
    assert len(result.references) == 5
    assert result.page == 1


async def test_rename_updates_id():
    ctx, store = make_ctx([{"id": "old2020", "type": "book", "title": "T"}])
    result = await rename_reference("old2020", "new2020", ctx)
    assert result.error is None
    assert result.old_key == "old2020"
    assert result.new_key == "new2020"
    assert store[0]["id"] == "new2020"


async def test_rename_updates_file_path():
    ctx, store = make_ctx(
        [
            {
                "id": "old2020",
                "type": "book",
                "_file": {
                    "path": "/vault/librero/old2020.pdf",
                    "mime_type": "application/pdf",
                    "size_bytes": 1,
                    "added_at": "2025-01-01T00:00:00+00:00",
                },
            }
        ]
    )
    await rename_reference("old2020", "new2020", ctx)
    assert store[0]["_file"]["path"] == "/vault/librero/new2020.pdf"


async def test_rename_not_found():
    ctx, _ = make_ctx()
    result = await rename_reference("ghost", "new2020", ctx)
    assert result.error is not None
    assert "not found" in result.error


async def test_rename_rejects_existing_key():
    ctx, _ = make_ctx([{"id": "a", "type": "book"}, {"id": "b", "type": "book"}])
    result = await rename_reference("a", "b", ctx)
    assert result.error is not None
    assert "already exists" in result.error
