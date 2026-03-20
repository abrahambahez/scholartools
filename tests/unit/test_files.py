from pathlib import Path

from scholartools.models import LibraryCtx
from scholartools.services.files import (
    _resolve_file_path,
    link_file,
    list_files,
    move_file,
    unlink_file,
)


def make_ctx(tmp_path, initial=None):
    store = list(initial or [])
    files_dir = tmp_path / "files"
    files_dir.mkdir(exist_ok=True)

    async def read_all():
        return list(store)

    async def write_all(records):
        store.clear()
        store.extend(records)

    async def copy_file(src, dest):
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_bytes(Path(src).read_bytes())

    async def delete_file(path):
        Path(path).unlink(missing_ok=True)

    async def rename_file(old, new):
        Path(old).rename(new)

    async def list_file_paths(dir_path):
        return []

    return (
        LibraryCtx(
            read_all=read_all,
            write_all=write_all,
            copy_file=copy_file,
            delete_file=delete_file,
            rename_file=rename_file,
            list_file_paths=list_file_paths,
            files_dir=str(files_dir),
            api_sources=[],
        ),
        store,
        files_dir,
    )


async def test_link_file(tmp_path):
    src = tmp_path / "paper.pdf"
    src.write_bytes(b"pdf data")
    ctx, store, files_dir = make_ctx(tmp_path, [{"id": "smith2020", "type": "book"}])

    result = await link_file("smith2020", str(src), ctx)

    assert result.error is None
    assert result.citekey == "smith2020"
    assert result.file_record.path == str(src.resolve())  # absolute path stored
    assert result.file_record.mime_type == "application/pdf"
    assert result.file_record.size_bytes == len(b"pdf data")
    assert src.exists()  # not copied — original stays in place
    assert store[0]["_file"]["path"] == str(src.resolve())


async def test_link_file_not_found_citekey(tmp_path):
    src = tmp_path / "paper.pdf"
    src.write_bytes(b"data")
    ctx, _, _ = make_ctx(tmp_path)
    result = await link_file("missing", str(src), ctx)
    assert result.error is not None


async def test_link_file_missing_source(tmp_path):
    ctx, _, _ = make_ctx(tmp_path, [{"id": "x", "type": "book"}])
    result = await link_file("x", str(tmp_path / "ghost.pdf"), ctx)
    assert result.error is not None
    assert "not found" in result.error


async def test_unlink_file(tmp_path):
    ctx, store, files_dir = make_ctx(
        tmp_path,
        [
            {
                "id": "x",
                "type": "book",
                "_file": {
                    "path": "x.pdf",
                    "mime_type": "application/pdf",
                    "size_bytes": 10,
                    "added_at": "2026-01-01T00:00:00Z",
                },
            }
        ],
    )
    (files_dir / "x.pdf").write_bytes(b"data")

    result = await unlink_file("x", ctx)

    assert result.unlinked is True
    assert "_file" not in store[0]
    # file not deleted — only the record is removed


async def test_unlink_no_file_linked(tmp_path):
    ctx, _, _ = make_ctx(tmp_path, [{"id": "x", "type": "book"}])
    result = await unlink_file("x", ctx)
    assert result.unlinked is False
    assert result.error is not None


async def test_unlink_citekey_not_found(tmp_path):
    ctx, _, _ = make_ctx(tmp_path)
    result = await unlink_file("missing", ctx)
    assert result.unlinked is False


async def test_move_file(tmp_path):
    ctx, store, files_dir = make_ctx(
        tmp_path,
        [
            {
                "id": "x",
                "type": "book",
                "_file": {
                    "path": "x.pdf",
                    "mime_type": "application/pdf",
                    "size_bytes": 5,
                    "added_at": "2026-01-01T00:00:00Z",
                },
            }
        ],
    )
    (files_dir / "x.pdf").write_bytes(b"hello")

    result = await move_file("x", "x_renamed.pdf", ctx)

    assert result.error is None
    assert store[0]["_file"]["path"] == "x_renamed.pdf"
    assert result.new_path.endswith("x_renamed.pdf")


async def test_list_files_empty(tmp_path):
    ctx, _, _ = make_ctx(tmp_path, [{"id": "x", "type": "book"}])
    result = await list_files(ctx)
    assert result.total == 0
    assert result.files == []


async def test_list_files(tmp_path):
    ctx, _, _ = make_ctx(
        tmp_path,
        [
            {
                "id": "a",
                "type": "book",
                "_file": {
                    "path": "a.pdf",
                    "mime_type": "application/pdf",
                    "size_bytes": 1,
                    "added_at": "2026-01-01T00:00:00Z",
                },
            },
            {"id": "b", "type": "book"},
            {
                "id": "c",
                "type": "book",
                "_file": {
                    "path": "c.epub",
                    "mime_type": "application/epub+zip",
                    "size_bytes": 2,
                    "added_at": "2026-01-01T00:00:00Z",
                },
            },
        ],
    )
    result = await list_files(ctx)
    assert result.total == 2
    citekeys = {f.citekey for f in result.files}
    assert citekeys == {"a", "c"}


def test_resolve_file_path_relative(tmp_path):
    ctx, _, files_dir = make_ctx(tmp_path)
    resolved = _resolve_file_path(ctx, "paper.pdf")
    assert resolved == files_dir / "paper.pdf"


def test_resolve_file_path_absolute_exists(tmp_path):
    ctx, _, files_dir = make_ctx(tmp_path)
    existing = tmp_path / "other" / "paper.pdf"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"data")
    resolved = _resolve_file_path(ctx, str(existing))
    assert resolved == existing


def test_resolve_file_path_absolute_missing_falls_back(tmp_path):
    ctx, _, files_dir = make_ctx(tmp_path)
    legacy = Path("/old/library/files/paper.pdf")
    resolved = _resolve_file_path(ctx, str(legacy))
    assert resolved == files_dir / "paper.pdf"
