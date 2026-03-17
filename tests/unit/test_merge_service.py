from scholartools.models import LibraryCtx
from scholartools.services.merge import merge


def make_ctx(staged: list[dict] | None = None, library: list[dict] | None = None):
    staged_store = list(staged or [])
    lib_store = list(library or [])
    lib_writes: list[list] = []
    staging_writes: list[list] = []
    copied_files: list[tuple[str, str]] = []
    deleted_files: list[str] = []

    async def read_all():
        return list(lib_store)

    async def write_all(records):
        lib_store.clear()
        lib_store.extend(records)
        lib_writes.append(list(records))

    async def staging_read_all():
        return list(staged_store)

    async def staging_write_all(records):
        staged_store.clear()
        staged_store.extend(records)
        staging_writes.append(list(records))

    async def copy_file(src, dest):
        copied_files.append((src, dest))

    async def staging_delete_file(path):
        deleted_files.append(path)

    async def noop(*_):
        pass

    ctx = LibraryCtx(
        read_all=read_all,
        write_all=write_all,
        copy_file=copy_file,
        delete_file=noop,
        rename_file=noop,
        list_file_paths=lambda _: [],
        files_dir="/data/files",
        staging_read_all=staging_read_all,
        staging_write_all=staging_write_all,
        staging_copy_file=noop,
        staging_delete_file=staging_delete_file,
        staging_dir="/tmp/staging",
        api_sources=[],
    )
    return (
        ctx,
        staged_store,
        lib_store,
        lib_writes,
        staging_writes,
        copied_files,
        deleted_files,
    )


def valid_record(citekey="smith2020") -> dict:
    return {
        "id": citekey,
        "type": "article-journal",
        "title": "A Unique Title For Testing",
        "author": [{"family": "Smith"}],
        "issued": {"date-parts": [[2020]]},
        "added_at": "2025-01-01T00:00:00+00:00",
    }


# --- full merge workflow ---


async def test_merge_promotes_valid_record():
    staged = [valid_record("smith2020")]
    ctx, staged_store, lib_store, _, _, _, _ = make_ctx(staged=staged)

    result = await merge(None, ctx)

    assert result.promoted == ["smith2020"]
    assert result.errors == {}
    assert result.skipped == []
    assert any(r["id"] == "smith2020" for r in lib_store)


async def test_merge_clears_promoted_from_staging():
    staged = [valid_record("smith2020")]
    ctx, staged_store, _, _, _, _, _ = make_ctx(staged=staged)

    await merge(None, ctx)

    assert staged_store == []


async def test_merge_preserves_unpromoted_in_staging():
    rec_bad = {
        "id": "ghost2020",
        "type": "article-journal",
        "added_at": "2025-01-01T00:00:00+00:00",
    }
    staged = [valid_record("smith2020"), rec_bad]
    ctx, staged_store, _, _, _, _, _ = make_ctx(staged=staged)

    result = await merge(None, ctx)

    assert "smith2020" in result.promoted
    assert "ghost2020" in result.errors
    assert any(r["id"] == "ghost2020" for r in staged_store)


# --- error isolation ---


async def test_merge_error_does_not_block_other_records():
    staged = [
        valid_record("smith2020"),
        {
            "id": "broken2020",
            "type": "article-journal",
            "added_at": "2025-01-01T00:00:00+00:00",
        },
    ]
    ctx, _, lib_store, _, _, _, _ = make_ctx(staged=staged)

    result = await merge(None, ctx)

    assert "smith2020" in result.promoted
    assert "broken2020" in result.errors
    assert any(r["id"] == "smith2020" for r in lib_store)


async def test_merge_duplicate_goes_to_errors():
    existing = {
        **valid_record("smith2020"),
        "uid": "shared_uid_abcdef12",
        "uid_confidence": "authoritative",
    }
    staged = [
        {
            **valid_record("smith2020b"),
            "uid": "shared_uid_abcdef12",
            "uid_confidence": "authoritative",
        }
    ]

    ctx, _, _, _, _, _, _ = make_ctx(staged=staged, library=[existing])

    result = await merge(None, ctx)

    assert "smith2020b" in result.errors
    assert "smith2020" in result.errors["smith2020b"]


async def test_merge_rejects_semantic_uid_without_flag():
    rec = {
        **valid_record("smith2020"),
        "uid": "abc123def456abcd",
        "uid_confidence": "semantic",
    }
    ctx, _, _, _, _, _, _ = make_ctx(staged=[rec])
    result = await merge(None, ctx)
    assert "smith2020" in result.errors
    assert "allow_semantic" in result.errors["smith2020"]


async def test_merge_allows_semantic_uid_with_flag():
    rec = {
        **valid_record("smith2020"),
        "uid": "abc123def456abcd",
        "uid_confidence": "semantic",
    }
    ctx, _, _, _, _, _, _ = make_ctx(staged=[rec])
    result = await merge(None, ctx, allow_semantic=True)
    assert "smith2020" in result.promoted


async def test_merge_missing_required_field_goes_to_errors():
    staged = [
        {
            "id": "notype2020",
            "type": "article-journal",
            "title": "Something",
            "issued": {"date-parts": [[2020]]},
            "added_at": "2025-01-01T00:00:00+00:00",
        }
    ]
    ctx, _, _, _, _, _, _ = make_ctx(staged=staged)

    result = await merge(None, ctx)

    assert "notype2020" in result.errors
    assert "author" in result.errors["notype2020"]


# --- skip list ---


async def test_merge_omit_adds_to_skipped():
    staged = [valid_record("smith2020")]
    ctx, staged_store, lib_store, _, _, _, _ = make_ctx(staged=staged)

    result = await merge(["smith2020"], ctx)

    assert result.skipped == ["smith2020"]
    assert result.promoted == []
    assert not any(r["id"] == "smith2020" for r in lib_store)


async def test_merge_omit_record_stays_in_staging():
    staged = [valid_record("smith2020")]
    ctx, staged_store, _, _, staging_writes, _, _ = make_ctx(staged=staged)

    await merge(["smith2020"], ctx)

    # nothing promoted so write_all not called; staging unchanged
    assert staging_writes == []
    assert any(r["id"] == "smith2020" for r in staged_store)


# --- atomic write ---


async def test_merge_library_written_once():
    staged = [valid_record("smith2020"), valid_record("jones2021")]
    staged[1]["title"] = "Another Totally Different Title"
    ctx, _, _, lib_writes, _, _, _ = make_ctx(staged=staged)

    result = await merge(None, ctx)

    assert len(result.promoted) == 2
    assert len(lib_writes) == 1


async def test_merge_empty_staging_does_not_write_library():
    ctx, _, _, lib_writes, staging_writes, _, _ = make_ctx(staged=[])

    await merge(None, ctx)

    assert lib_writes == []
    assert staging_writes == []


# --- file archival order ---


async def test_merge_schema_validated_before_file_archived():
    """A record with a file but missing required fields
    must NOT have its file copied."""
    file_rec = {
        "path": "/tmp/staging/bad.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 100,
        "added_at": "2025-01-01T00:00:00+00:00",
    }
    staged = [
        {
            "id": "bad2020",
            "type": "article-journal",
            "_file": file_rec,
            "added_at": "2025-01-01T00:00:00+00:00",
        }
    ]
    ctx, _, _, _, _, copied_files, _ = make_ctx(staged=staged)

    result = await merge(None, ctx)

    assert "bad2020" in result.errors
    assert copied_files == []


async def test_merge_archives_file_for_valid_record():
    file_rec = {
        "path": "/tmp/staging/smith2020.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 100,
        "added_at": "2025-01-01T00:00:00+00:00",
    }
    rec = {**valid_record("smith2020"), "_file": file_rec}
    ctx, _, _, _, _, copied_files, _ = make_ctx(staged=[rec])

    result = await merge(None, ctx)

    assert "smith2020" in result.promoted
    assert len(copied_files) == 1
    assert copied_files[0][0] == "/tmp/staging/smith2020.pdf"
    assert copied_files[0][1] == "/data/files/smith2020.pdf"


async def test_merge_renames_file_to_citekey():
    """File is always archived as citekey.ext regardless of original filename."""
    file_rec = {
        "path": "/tmp/staging/original-name.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 100,
        "added_at": "2025-01-01T00:00:00+00:00",
    }
    rec = {**valid_record("smith2020"), "_file": file_rec}
    ctx, _, lib_store, _, _, copied_files, _ = make_ctx(staged=[rec])

    result = await merge(None, ctx)

    assert "smith2020" in result.promoted
    assert copied_files[0][1] == "/data/files/smith2020.pdf"
    promoted = next(r for r in lib_store if r["id"] == "smith2020")
    assert promoted["_file"]["path"] == "/data/files/smith2020.pdf"


# --- staging cleanup after promotion ---


async def test_merge_deletes_staging_file_after_promotion():
    file_rec = {
        "path": "/tmp/staging/smith2020.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 100,
        "added_at": "2025-01-01T00:00:00+00:00",
    }
    rec = {**valid_record("smith2020"), "_file": file_rec}
    ctx, _, _, _, _, _, deleted_files = make_ctx(staged=[rec])

    await merge(None, ctx)

    assert "/tmp/staging/smith2020.pdf" in deleted_files


async def test_merge_does_not_delete_file_for_error_record():
    file_rec = {
        "path": "/tmp/staging/bad.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 100,
        "added_at": "2025-01-01T00:00:00+00:00",
    }
    staged = [
        {
            "id": "bad2020",
            "type": "article-journal",
            "_file": file_rec,
            "added_at": "2025-01-01T00:00:00+00:00",
        }
    ]
    ctx, _, _, _, _, _, deleted_files = make_ctx(staged=staged)

    await merge(None, ctx)

    assert deleted_files == []


# --- BibTeX field normalization ---


async def test_merge_normalizes_journal_to_container_title():
    rec = {
        "id": "norm2020",
        "type": "article-journal",
        "title": "Normalized Journal Title",
        "author": [{"family": "Norm"}],
        "issued": {"date-parts": [[2020]]},
        "journal": "Nature",
        "added_at": "2025-01-01T00:00:00+00:00",
    }
    ctx, _, lib_store, _, _, _, _ = make_ctx(staged=[rec])

    result = await merge(None, ctx)

    assert "norm2020" in result.promoted
    promoted = next(r for r in lib_store if r["id"] == "norm2020")
    assert promoted.get("container-title") == "Nature"
    assert "journal" not in promoted
