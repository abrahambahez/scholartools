import pytest

from scholartools.adapters.local import (
    make_filestore,
    make_staging_storage,
    make_storage,
)
from scholartools.models import LibraryCtx, Reference
from scholartools.services.merge import merge
from scholartools.services.staging import list_staged, stage_reference


def make_ctx(tmp_path):
    library_file = tmp_path / "library.json"
    files_dir = tmp_path / "files"
    staging_file = tmp_path / "staging.json"
    staging_dir = tmp_path / "staging"

    read_all, write_all = make_storage(str(library_file))
    copy_file, delete_file, rename_file, list_file_paths = make_filestore(
        str(files_dir)
    )
    staging_read_all, staging_write_all = make_staging_storage(
        str(staging_file), str(staging_dir)
    )
    staging_copy_file, staging_delete_file, _, _ = make_filestore(str(staging_dir))

    return LibraryCtx(
        read_all=read_all,
        write_all=write_all,
        copy_file=copy_file,
        delete_file=delete_file,
        rename_file=rename_file,
        list_file_paths=list_file_paths,
        files_dir=str(files_dir),
        staging_read_all=staging_read_all,
        staging_write_all=staging_write_all,
        staging_copy_file=staging_copy_file,
        staging_delete_file=staging_delete_file,
        staging_dir=str(staging_dir),
        api_sources=[],
    )


def valid_ref(**kwargs) -> Reference:
    defaults = dict(
        id="",
        type="article-journal",
        title="A Valid Integration Title",
        author=[{"family": "Smith"}],
        issued={"date-parts": [[2024]]},
    )
    defaults.update(kwargs)
    return Reference.model_validate(defaults)


@pytest.mark.integration
async def test_full_workflow_stage_list_merge_verify(tmp_path):
    ctx = make_ctx(tmp_path)
    ref = valid_ref()

    stage_result = await stage_reference(ref, None, ctx)
    assert stage_result.error is None
    citekey = stage_result.citekey

    list_result = await list_staged(ctx)
    assert list_result.total == 1
    assert list_result.references[0].citekey == citekey

    merge_result = await merge(None, ctx, allow_semantic=True)
    assert citekey in merge_result.promoted
    assert merge_result.errors == {}

    library_records = await ctx.read_all()
    assert any(r["id"] == citekey for r in library_records)

    list_after = await list_staged(ctx)
    assert list_after.total == 0


@pytest.mark.integration
async def test_duplicate_detection_stays_in_staging(tmp_path):
    ctx = make_ctx(tmp_path)

    existing = valid_ref(title="A Valid Integration Title")
    stage_existing = await stage_reference(existing, None, ctx)
    assert stage_existing.error is None
    existing_key = stage_existing.citekey
    await merge(None, ctx, allow_semantic=True)

    dup = valid_ref(title="A Valid Integration Title")
    stage_result = await stage_reference(dup, None, ctx)
    assert stage_result.error is None
    dup_key = stage_result.citekey

    merge_result = await merge(None, ctx, allow_semantic=True)
    assert dup_key in merge_result.errors
    assert existing_key in merge_result.errors[dup_key]

    staged_after = await list_staged(ctx)
    assert any(r.citekey == dup_key for r in staged_after.references)


@pytest.mark.integration
async def test_skip_list_one_promoted_one_skipped(tmp_path):
    ctx = make_ctx(tmp_path)

    ref_a = valid_ref(title="First Unique Integration Title")
    ref_b = valid_ref(title="Second Unique Integration Title")

    stage_a = await stage_reference(ref_a, None, ctx)
    stage_b = await stage_reference(ref_b, None, ctx)
    key_a = stage_a.citekey
    key_b = stage_b.citekey

    merge_result = await merge([key_b], ctx, allow_semantic=True)

    assert key_a in merge_result.promoted
    assert key_b in merge_result.skipped

    library_records = await ctx.read_all()
    assert any(r["id"] == key_a for r in library_records)
    assert not any(r["id"] == key_b for r in library_records)

    staged_after = await list_staged(ctx)
    assert any(r.citekey == key_b for r in staged_after.references)


@pytest.mark.integration
async def test_file_archival_on_merge(tmp_path):
    ctx = make_ctx(tmp_path)

    src_file = tmp_path / "paper.pdf"
    src_file.write_bytes(b"%PDF-1.4 fake content")

    ref = valid_ref(title="File Archival Integration Title")
    stage_result = await stage_reference(ref, src_file, ctx)
    assert stage_result.error is None
    citekey = stage_result.citekey

    staging_dir = tmp_path / "staging"
    staged_file = staging_dir / src_file.name
    assert staged_file.exists()

    merge_result = await merge(None, ctx, allow_semantic=True)
    assert citekey in merge_result.promoted

    files_dir = tmp_path / "files"
    archived_file = files_dir / f"{citekey}.pdf"
    assert archived_file.exists()

    assert not staged_file.exists()
