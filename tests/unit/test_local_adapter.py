from scholartools.adapters.local import make_filestore, make_storage

# --- storage ---


async def test_read_all_returns_empty_when_no_file(tmp_path):
    read_all, _ = make_storage(str(tmp_path / "lib.json"))
    assert await read_all() == []


async def test_write_all_creates_file_and_reads_back(tmp_path):
    lib = tmp_path / "lib.json"
    read_all, write_all = make_storage(str(lib))
    records = [{"id": "smith2020", "type": "article-journal"}]
    await write_all(records)
    assert lib.exists()
    assert await read_all() == records


async def test_write_all_creates_parent_dirs(tmp_path):
    lib = tmp_path / "nested" / "deep" / "lib.json"
    _, write_all = make_storage(str(lib))
    await write_all([])
    assert lib.exists()


async def test_write_all_is_atomic(tmp_path):
    lib = tmp_path / "lib.json"
    read_all, write_all = make_storage(str(lib))
    await write_all([{"id": "a", "type": "book"}])
    await write_all([{"id": "b", "type": "book"}])
    # no .tmp.json left behind
    assert not (tmp_path / "lib.tmp.json").exists()
    assert await read_all() == [{"id": "b", "type": "book"}]


async def test_write_all_preserves_unicode(tmp_path):
    lib = tmp_path / "lib.json"
    _, write_all = make_storage(str(lib))
    read_all, _ = make_storage(str(lib))
    records = [{"id": "x", "title": "Infraestructura en América Latina"}]
    await write_all(records)
    result = await read_all()
    assert result[0]["title"] == "Infraestructura en América Latina"


# --- filestore ---


async def test_copy_file(tmp_path):
    src = tmp_path / "source.pdf"
    src.write_bytes(b"pdf content")
    dest = tmp_path / "files" / "dest.pdf"
    copy_file, _, _, _ = make_filestore(str(tmp_path / "files"))
    await copy_file(str(src), str(dest))
    assert dest.exists()
    assert dest.read_bytes() == b"pdf content"
    assert src.exists()  # original untouched


async def test_copy_file_creates_dest_dirs(tmp_path):
    src = tmp_path / "source.pdf"
    src.write_bytes(b"data")
    dest = tmp_path / "files" / "nested" / "dest.pdf"
    copy_file, _, _, _ = make_filestore(str(tmp_path / "files"))
    await copy_file(str(src), str(dest))
    assert dest.exists()


async def test_delete_file(tmp_path):
    f = tmp_path / "file.pdf"
    f.write_bytes(b"data")
    _, delete_file, _, _ = make_filestore(str(tmp_path))
    await delete_file(str(f))
    assert not f.exists()


async def test_delete_file_missing_ok(tmp_path):
    _, delete_file, _, _ = make_filestore(str(tmp_path))
    await delete_file(str(tmp_path / "nonexistent.pdf"))  # must not raise


async def test_rename_file(tmp_path):
    old = tmp_path / "old.pdf"
    old.write_bytes(b"data")
    new = tmp_path / "new.pdf"
    _, _, rename_file, _ = make_filestore(str(tmp_path))
    await rename_file(str(old), str(new))
    assert new.exists()
    assert not old.exists()


async def test_list_file_paths_empty_dir(tmp_path):
    _, _, _, list_file_paths = make_filestore(str(tmp_path))
    files_dir = tmp_path / "files"
    assert await list_file_paths(str(files_dir)) == []


async def test_list_file_paths(tmp_path):
    files_dir = tmp_path / "files"
    files_dir.mkdir()
    (files_dir / "a.pdf").write_bytes(b"a")
    (files_dir / "b.pdf").write_bytes(b"b")
    _, _, _, list_file_paths = make_filestore(str(files_dir))
    paths = await list_file_paths(str(files_dir))
    assert len(paths) == 2
    assert all(p.endswith(".pdf") for p in paths)
