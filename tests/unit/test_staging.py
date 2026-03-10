from datetime import datetime, timezone

from scholartools.adapters.local import make_staging_storage
from scholartools.models import (
    DeleteStagedResult,
    ListStagedResult,
    MergeResult,
    Reference,
    StageResult,
)

# --- staging storage ---


async def test_staging_read_returns_empty_before_any_write(tmp_path):
    read_all, _ = make_staging_storage(
        str(tmp_path / "staging.json"), str(tmp_path / "staging")
    )
    assert await read_all() == []


async def test_staging_write_creates_staging_json_and_dir(tmp_path):
    staging_json = tmp_path / "staging.json"
    staging_dir = tmp_path / "staging"
    read_all, write_all = make_staging_storage(str(staging_json), str(staging_dir))

    await write_all([{"id": "jones2021", "type": "book"}])

    assert staging_json.exists()
    assert staging_dir.exists()


async def test_staging_write_reads_back(tmp_path):
    read_all, write_all = make_staging_storage(
        str(tmp_path / "staging.json"), str(tmp_path / "staging")
    )
    records = [{"id": "jones2021", "type": "book"}]
    await write_all(records)
    assert await read_all() == records


async def test_staging_write_is_atomic(tmp_path):
    staging_json = tmp_path / "staging.json"
    read_all, write_all = make_staging_storage(
        str(staging_json), str(tmp_path / "staging")
    )
    await write_all([{"id": "a", "type": "book"}])
    await write_all([{"id": "b", "type": "book"}])
    assert not (tmp_path / "staging.tmp.json").exists()
    assert await read_all() == [{"id": "b", "type": "book"}]


async def test_staging_isolated_from_library(tmp_path):
    lib_json = tmp_path / "library.json"
    staging_json = tmp_path / "staging.json"

    from scholartools.adapters.local import make_storage

    lib_read, lib_write = make_storage(str(lib_json))
    stage_read, stage_write = make_staging_storage(
        str(staging_json), str(tmp_path / "staging")
    )

    await lib_write([{"id": "lib_ref", "type": "book"}])
    await stage_write([{"id": "stage_ref", "type": "article-journal"}])

    lib_records = await lib_read()
    stage_records = await stage_read()

    assert lib_records == [{"id": "lib_ref", "type": "book"}]
    assert stage_records == [{"id": "stage_ref", "type": "article-journal"}]


async def test_staging_creates_parent_dirs(tmp_path):
    nested = tmp_path / "nested" / "deep"
    staging_json = nested / "staging.json"
    _, write_all = make_staging_storage(str(staging_json), str(nested / "staging"))
    await write_all([])
    assert staging_json.exists()


# --- staging result models ---


def test_stage_result_success():
    result = StageResult(citekey="jones2021")
    assert result.citekey == "jones2021"
    assert result.error is None


def test_stage_result_failure():
    result = StageResult(error="invalid reference")
    assert result.citekey is None
    assert result.error == "invalid reference"


def test_list_staged_result():
    from scholartools.models import ReferenceRow

    rows = [ReferenceRow(citekey="a"), ReferenceRow(citekey="b")]
    result = ListStagedResult(references=rows, total=2)
    assert result.total == 2
    assert len(result.references) == 2


def test_delete_staged_result_success():
    result = DeleteStagedResult(deleted=True)
    assert result.deleted is True
    assert result.error is None


def test_delete_staged_result_failure():
    result = DeleteStagedResult(deleted=False, error="not found")
    assert result.deleted is False
    assert result.error == "not found"


def test_merge_result_all_promoted():
    result = MergeResult(promoted=["a", "b"], errors={}, skipped=[])
    assert result.promoted == ["a", "b"]
    assert result.errors == {}
    assert result.skipped == []


def test_merge_result_with_errors_and_skipped():
    result = MergeResult(
        promoted=["a"],
        errors={"b": "duplicate: smith2020"},
        skipped=["c"],
    )
    assert result.promoted == ["a"]
    assert result.errors["b"] == "duplicate: smith2020"
    assert result.skipped == ["c"]


def test_reference_added_at_optional():
    ref = Reference(id="x", type="book")
    assert ref.added_at is None


def test_reference_added_at_accepts_datetime():
    now = datetime.now(tz=timezone.utc)
    ref = Reference(id="x", type="book", added_at=now)
    assert ref.added_at == now


def test_reference_added_at_roundtrips_json():
    now = datetime(2026, 3, 9, 12, 0, 0, tzinfo=timezone.utc)
    ref = Reference(id="x", type="book", added_at=now)
    data = ref.model_dump()
    restored = Reference(**data)
    assert restored.added_at == now
