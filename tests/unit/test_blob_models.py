from scholartools.models import ChangeLogEntry, PrefetchResult, Reference


def test_reference_blob_ref_default():
    ref = Reference(id="smith2024", type="article-journal")
    assert ref.blob_ref is None


def test_reference_blob_ref_set():
    ref = Reference(id="smith2024", type="article-journal", blob_ref="sha256:abc123")
    assert ref.blob_ref == "sha256:abc123"


def test_reference_blob_ref_roundtrip():
    ref = Reference(id="x", type="book", blob_ref="sha256:deadbeef")
    dumped = ref.model_dump(by_alias=True)
    restored = Reference.model_validate(dumped)
    assert restored.blob_ref == "sha256:deadbeef"


def test_reference_blob_ref_none_roundtrip():
    ref = Reference(id="x", type="book")
    dumped = ref.model_dump(by_alias=True)
    restored = Reference.model_validate(dumped)
    assert restored.blob_ref is None


def test_change_log_entry_link_file_op():
    e = ChangeLogEntry(
        op="link_file",
        uid="uid-1",
        uid_confidence="",
        citekey="smith2024",
        data={},
        blob_ref="sha256:abc",
        peer_id="peer-a",
        device_id="dev-1",
        timestamp_hlc="2026-01-01T00:00:00.000Z-0001-peer-a",
        signature="sig",
    )
    assert e.op == "link_file"
    assert e.blob_ref == "sha256:abc"


def test_change_log_entry_unlink_file_op():
    e = ChangeLogEntry(
        op="unlink_file",
        uid="uid-1",
        uid_confidence="",
        citekey="smith2024",
        data={},
        blob_ref=None,
        peer_id="peer-a",
        device_id="dev-1",
        timestamp_hlc="2026-01-01T00:00:00.000Z-0001-peer-a",
        signature="sig",
    )
    assert e.op == "unlink_file"
    assert e.blob_ref is None


def test_change_log_entry_blob_ref_roundtrip():
    e = ChangeLogEntry(
        op="link_file",
        uid="u",
        uid_confidence="",
        citekey="x",
        data={},
        blob_ref="sha256:ff00",
        peer_id="p",
        device_id="d",
        timestamp_hlc="ts",
        signature="s",
    )
    restored = ChangeLogEntry.model_validate_json(e.model_dump_json())
    assert restored.blob_ref == "sha256:ff00"


def test_change_log_entry_data_default():
    e = ChangeLogEntry(
        op="unlink_file",
        uid="u",
        uid_confidence="",
        citekey="x",
        blob_ref=None,
        peer_id="p",
        device_id="d",
        timestamp_hlc="ts",
        signature="s",
    )
    assert e.data == {}


def test_prefetch_result_fields():
    r = PrefetchResult(fetched=3, already_cached=1, errors=["err1"])
    assert r.fetched == 3
    assert r.already_cached == 1
    assert r.errors == ["err1"]


def test_prefetch_result_roundtrip():
    r = PrefetchResult(fetched=2, already_cached=5, errors=[])
    restored = PrefetchResult.model_validate_json(r.model_dump_json())
    assert restored == r


def test_prefetch_result_empty_errors():
    r = PrefetchResult(fetched=0, already_cached=0, errors=[])
    assert r.errors == []
