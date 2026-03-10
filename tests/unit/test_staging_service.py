from datetime import datetime, timezone

from scholartools.models import LibraryCtx, Reference
from scholartools.services.staging import delete_staged, list_staged, stage_reference


def make_ctx(initial: list[dict] | None = None):
    store = list(initial or [])
    copied_files: list[tuple[str, str]] = []
    deleted_files: list[str] = []

    async def staging_read_all():
        return list(store)

    async def staging_write_all(records):
        store.clear()
        store.extend(records)

    async def staging_copy_file(src, dest):
        copied_files.append((src, dest))

    async def staging_delete_file(path):
        deleted_files.append(path)

    async def noop(*_):
        pass

    ctx = LibraryCtx(
        read_all=staging_read_all,
        write_all=staging_write_all,
        copy_file=noop,
        delete_file=noop,
        rename_file=noop,
        list_file_paths=lambda _: [],
        files_dir="data/files",
        staging_read_all=staging_read_all,
        staging_write_all=staging_write_all,
        staging_copy_file=staging_copy_file,
        staging_delete_file=staging_delete_file,
        staging_dir="/tmp/staging",
        api_sources=[],
    )
    return ctx, store, copied_files, deleted_files


def make_ref(**kwargs) -> Reference:
    defaults = {"id": "", "type": "book"}
    defaults.update(kwargs)
    return Reference(**defaults)


# --- stage_reference ---


async def test_stage_assigns_citekey():
    ctx, store, _, _ = make_ctx()
    ref = Reference(
        id="",
        type="article-journal",
        author=[{"family": "Jones"}],
        issued={"date-parts": [[2021]]},
    )
    result = await stage_reference(ref, None, ctx)
    assert result.error is None
    assert result.citekey == "jones2021"
    assert store[0]["id"] == "jones2021"


async def test_stage_sets_added_at():
    ctx, store, _, _ = make_ctx()
    ref = Reference(id="", type="book")
    before = datetime.now(timezone.utc)
    result = await stage_reference(ref, None, ctx)
    after = datetime.now(timezone.utc)

    assert result.error is None
    added_at = datetime.fromisoformat(store[0]["added_at"])
    assert before <= added_at <= after


async def test_stage_resolves_collision():
    ctx, store, _, _ = make_ctx(
        [{"id": "jones2021", "type": "book", "added_at": "2021-01-01T00:00:00+00:00"}]
    )
    ref = Reference(
        id="",
        type="article-journal",
        author=[{"family": "Jones"}],
        issued={"date-parts": [[2021]]},
    )
    result = await stage_reference(ref, None, ctx)
    assert result.citekey == "jones2021a"


async def test_stage_copies_file_when_provided(tmp_path):
    ctx, store, copied, _ = make_ctx()
    src = tmp_path / "paper.pdf"
    src.write_text("content")

    ref = Reference(id="", type="book")
    await stage_reference(ref, src, ctx)

    assert len(copied) == 1
    assert copied[0][0] == str(src.resolve())
    assert copied[0][1] == f"/tmp/staging/{src.name}"


async def test_stage_no_file_copy_when_path_none():
    ctx, _, copied, _ = make_ctx()
    ref = Reference(id="", type="book")
    await stage_reference(ref, None, ctx)
    assert copied == []


async def test_stage_never_raises_on_error():
    async def failing_read():
        raise RuntimeError("storage down")

    async def noop(*_):
        pass

    ctx = LibraryCtx(
        read_all=failing_read,
        write_all=noop,
        copy_file=noop,
        delete_file=noop,
        rename_file=noop,
        list_file_paths=lambda _: [],
        files_dir="data/files",
        staging_read_all=failing_read,
        staging_write_all=noop,
        staging_copy_file=noop,
        staging_delete_file=noop,
        staging_dir="/tmp/staging",
        api_sources=[],
    )
    ref = Reference(id="", type="book")
    result = await stage_reference(ref, None, ctx)
    assert result.error is not None
    assert result.citekey is None


# --- list_staged ---


async def test_list_staged_returns_all():
    records = [
        {"id": "a", "type": "book", "added_at": "2025-01-02T00:00:00+00:00"},
        {"id": "b", "type": "book", "added_at": "2025-01-01T00:00:00+00:00"},
    ]
    ctx, _, _, _ = make_ctx(records)
    result = await list_staged(ctx)
    assert result.total == 2
    assert {r.citekey for r in result.references} == {"a", "b"}


async def test_list_staged_sorted_by_citekey():
    records = [
        {"id": "zebra2024", "type": "book", "added_at": "2025-06-01T00:00:00+00:00"},
        {"id": "alpha2024", "type": "book", "added_at": "2024-01-01T00:00:00+00:00"},
    ]
    ctx, _, _, _ = make_ctx(records)
    result = await list_staged(ctx)
    assert result.references[0].citekey == "alpha2024"
    assert result.references[1].citekey == "zebra2024"


async def test_list_staged_has_warnings_for_missing_fields():
    ctx, _, _, _ = make_ctx([{"id": "x", "type": "book"}])
    result = await list_staged(ctx)
    assert result.references[0].has_warnings is True


async def test_list_staged_empty():
    ctx, _, _, _ = make_ctx()
    result = await list_staged(ctx)
    assert result.total == 0
    assert result.references == []


# --- delete_staged ---


async def test_delete_staged_removes_record():
    ctx, store, _, _ = make_ctx(
        [
            {"id": "x", "type": "book", "added_at": "2025-01-01T00:00:00+00:00"},
            {"id": "y", "type": "book", "added_at": "2025-01-01T00:00:00+00:00"},
        ]
    )
    result = await delete_staged("x", ctx)
    assert result.deleted is True
    assert result.error is None
    assert len(store) == 1
    assert store[0]["id"] == "y"


async def test_delete_staged_not_found():
    ctx, _, _, _ = make_ctx()
    result = await delete_staged("ghost", ctx)
    assert result.deleted is False
    assert "not found" in result.error


async def test_delete_staged_deletes_associated_file():
    records = [
        {
            "id": "x",
            "type": "book",
            "added_at": "2025-01-01T00:00:00+00:00",
            "_file": {
                "path": "/tmp/staging/x.pdf",
                "mime_type": "application/pdf",
                "size_bytes": 100,
                "added_at": "2025-01-01T00:00:00+00:00",
            },
        }
    ]
    ctx, _, _, deleted = make_ctx(records)
    result = await delete_staged("x", ctx)
    assert result.deleted is True
    assert "/tmp/staging/x.pdf" in deleted


async def test_delete_staged_no_file_no_delete_call():
    ctx, _, _, deleted = make_ctx(
        [{"id": "x", "type": "book", "added_at": "2025-01-01T00:00:00+00:00"}]
    )
    await delete_staged("x", ctx)
    assert deleted == []


async def test_delete_staged_never_raises():
    async def failing_read():
        raise RuntimeError("storage down")

    async def noop(*_):
        pass

    ctx = LibraryCtx(
        read_all=failing_read,
        write_all=noop,
        copy_file=noop,
        delete_file=noop,
        rename_file=noop,
        list_file_paths=lambda _: [],
        files_dir="data/files",
        staging_read_all=failing_read,
        staging_write_all=noop,
        staging_copy_file=noop,
        staging_delete_file=noop,
        staging_dir="/tmp/staging",
        api_sources=[],
    )
    result = await delete_staged("x", ctx)
    assert result.deleted is False
    assert result.error is not None
