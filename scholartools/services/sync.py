import json
import mimetypes
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from scholartools.adapters import conflicts_store, s3_sync
from scholartools.adapters.peer_directory import load_peer_directory
from scholartools.config import CONFIG_PATH
from scholartools.models import (
    ChangeLogEntry,
    ConflictRecord,
    FileRecord,
    LibraryCtx,
    PrefetchResult,
    PullResult,
    PushResult,
    Result,
)
from scholartools.services import hlc as hlc_service
from scholartools.services import peers as peers_service
from scholartools.services.blobs import (
    blob_cache_path,
    compute_sha256_streaming,
    ensure_blob_cache_dir,
)


def _sync_state_path(data_dir: Path) -> Path:
    return data_dir / "sync_state.json"


def _load_sync_state(data_dir: Path) -> dict:
    path = _sync_state_path(data_dir)
    if not path.exists():
        return {"fence_push_hlc": "", "fence_pull_hlc": ""}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_sync_state(data_dir: Path, state: dict) -> None:
    path = _sync_state_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def _load_privkey(ctx: LibraryCtx) -> bytes | None:
    key_path = CONFIG_PATH.parent / "keys" / ctx.peer_id / f"{ctx.device_id}.key"
    return key_path.read_bytes() if key_path.exists() else None


def _sign_entry(entry_dict: dict, privkey: bytes) -> str:
    payload = peers_service._canonical(entry_dict)
    return peers_service._sign(payload, privkey)


def _hlc_to_datetime(hlc_str: str) -> datetime | None:
    try:
        iso_part = hlc_str[:23]
        dt = datetime.strptime(iso_part, "%Y-%m-%dT%H:%M:%S.%f")
        return dt.replace(tzinfo=timezone.utc)
    except (ValueError, IndexError):
        return None


def _within_60s(hlc_a: str, hlc_b: str) -> bool:
    dt_a = _hlc_to_datetime(hlc_a)
    dt_b = _hlc_to_datetime(hlc_b)
    if dt_a is None or dt_b is None:
        return False
    return abs((dt_a - dt_b).total_seconds()) <= 60


def _change_log_entries(
    data_dir: Path, fence: str
) -> list[tuple[Path, ChangeLogEntry]]:
    change_log_dir = data_dir / "change_log"
    if not change_log_dir.exists():
        return []
    results = []
    for f in sorted(change_log_dir.iterdir()):
        if not f.is_file() or not f.suffix == ".json":
            continue
        try:
            entry = ChangeLogEntry.model_validate_json(f.read_text(encoding="utf-8"))
            if entry.timestamp_hlc > fence:
                results.append((f, entry))
        except (ValueError, OSError):
            continue
    return results


def _write_change_log_entry(data_dir: Path, entry: ChangeLogEntry) -> None:
    log_dir = data_dir / "change_log"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{entry.timestamp_hlc}.json").write_text(
        entry.model_dump_json(), encoding="utf-8"
    )


async def push(ctx: LibraryCtx) -> PushResult:
    if not ctx.data_dir:
        return PushResult(errors=["data_dir not configured"])
    if not hasattr(ctx, "sync_config") or ctx.sync_config is None:
        return PushResult(errors=["sync not configured"])

    data_dir = Path(ctx.data_dir)
    privkey = _load_privkey(ctx)
    if privkey is None:
        return PushResult(errors=["local device keypair not found"])

    state = _load_sync_state(data_dir)
    fence = state.get("fence_push_hlc", "")
    entries = _change_log_entries(data_dir, fence)

    pushed = 0
    errors = []
    new_fence = fence

    for _, entry in entries:
        entry_dict = json.loads(entry.model_dump_json())
        entry_dict.pop("signature", None)
        entry_dict["signature"] = _sign_entry(entry_dict, privkey)
        remote_key = f"changes/{ctx.peer_id}/{entry.timestamp_hlc}.json"
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".json", delete=False, mode="w", encoding="utf-8"
            ) as tmp:
                json.dump(entry_dict, tmp, ensure_ascii=False)
                tmp_path = Path(tmp.name)
            s3_sync.upload(ctx.sync_config, tmp_path, remote_key)
            tmp_path.unlink(missing_ok=True)
            pushed += 1
            if entry.timestamp_hlc > new_fence:
                new_fence = entry.timestamp_hlc
        except Exception as exc:
            errors.append(f"{remote_key}: {exc}")
            tmp_path = Path(tmp.name) if "tmp_path" in dir() else None
            if tmp_path:
                tmp_path.unlink(missing_ok=True)

    state["fence_push_hlc"] = new_fence
    _save_sync_state(data_dir, state)
    return PushResult(entries_pushed=pushed, errors=errors)


async def pull(ctx: LibraryCtx) -> PullResult:
    if not ctx.data_dir:
        return PullResult(errors=["data_dir not configured"])
    if not hasattr(ctx, "sync_config") or ctx.sync_config is None:
        return PullResult(errors=["sync not configured"])
    if not ctx.peers_dir:
        return PullResult(errors=["peers_dir not configured"])

    data_dir = Path(ctx.data_dir)
    peers_dir = Path(ctx.peers_dir)
    state = _load_sync_state(data_dir)
    fence = state.get("fence_pull_hlc", "")

    try:
        all_keys = s3_sync.list_keys(ctx.sync_config, "changes/")
    except Exception as exc:
        return PullResult(errors=[f"list_keys failed: {exc}"])

    remote_keys = [k for k in all_keys if k > f"changes/{fence}"] if fence else all_keys
    peer_map = load_peer_directory(peers_dir)

    applied = 0
    rejected = 0
    conflicted = 0
    errors = []
    entries: list[ChangeLogEntry] = []

    for key in remote_keys:
        parts = key.split("/")
        if len(parts) >= 2 and parts[1] == ctx.peer_id:
            continue
        try:
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            s3_sync.download(ctx.sync_config, key, tmp_path)
            entry_dict = json.loads(tmp_path.read_text(encoding="utf-8"))
            tmp_path.unlink(missing_ok=True)
        except Exception as exc:
            errors.append(f"{key}: download failed: {exc}")
            continue

        verify_result = peers_service.verify_entry(entry_dict, peer_map)
        if not verify_result.verified:
            peer_id = entry_dict.get("peer_id", "unknown")
            device_id = entry_dict.get("device_id", "unknown")
            hlc_ts = entry_dict.get(
                "timestamp_hlc", datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            )
            rejected_dir = data_dir / "rejected"
            rejected_dir.mkdir(parents=True, exist_ok=True)
            fname = f"{hlc_ts}-{peer_id}-{device_id}.json"
            (rejected_dir / fname).write_text(
                json.dumps(entry_dict, ensure_ascii=False), encoding="utf-8"
            )
            rejected += 1
            continue

        try:
            entries.append(ChangeLogEntry.model_validate(entry_dict))
        except ValueError as exc:
            errors.append(f"{key}: invalid entry: {exc}")
            continue

    entries.sort(key=lambda e: e.timestamp_hlc)

    local_records: dict[str, dict] = {}
    try:
        raw = await ctx.read_all()
        for rec in raw:
            local_records[rec.get("id", "")] = rec
    except Exception as exc:
        errors.append(f"read_all failed: {exc}")

    updated_records: dict[str, dict] = dict(local_records)
    new_fence = fence

    for entry in entries:
        citekey = entry.citekey

        if entry.op == "delete_reference":
            existing = updated_records.get(citekey)
            if existing:
                ft = existing.get("_field_timestamps", {})
                any_local_newer = any(
                    local_ts > entry.timestamp_hlc for local_ts in ft.values()
                )
                if any_local_newer:
                    conflict = ConflictRecord(
                        uid=entry.uid,
                        field="__delete__",
                        local_value=existing,
                        local_timestamp_hlc=max(ft.values()) if ft else "",
                        remote_value=None,
                        remote_timestamp_hlc=entry.timestamp_hlc,
                        remote_peer_id=entry.peer_id,
                    )
                    conflicts_store.write_conflict(data_dir, conflict)
                    conflicted += 1
                else:
                    del updated_records[citekey]
                    applied += 1
            else:
                applied += 1
        elif entry.op in ("add_reference", "update_reference", "restore_reference"):
            existing = updated_records.get(citekey, {})
            ft = existing.get("_field_timestamps", {})
            incoming_data = entry.data
            merged = dict(existing)
            field_timestamps = dict(ft)

            conflict_written = False
            for field, value in incoming_data.items():
                local_ts = ft.get(field, "")
                remote_ts = entry.timestamp_hlc

                if local_ts and local_ts >= remote_ts:
                    if local_ts > remote_ts and _within_60s(local_ts, remote_ts):
                        if not conflict_written:
                            conflict = ConflictRecord(
                                uid=entry.uid,
                                field=field,
                                local_value=existing.get(field),
                                local_timestamp_hlc=local_ts,
                                remote_value=value,
                                remote_timestamp_hlc=remote_ts,
                                remote_peer_id=entry.peer_id,
                            )
                            conflicts_store.write_conflict(data_dir, conflict)
                            conflicted += 1
                            conflict_written = True
                    continue
                else:
                    merged[field] = value
                    field_timestamps[field] = remote_ts

            if not merged.get("id"):
                merged["id"] = citekey
            merged["_field_timestamps"] = field_timestamps
            updated_records[citekey] = merged
            if not conflict_written:
                applied += 1
        elif entry.op == "link_file":
            existing = updated_records.get(citekey, {})
            ft = existing.get("_field_timestamps", {})
            local_ts = ft.get("blob_ref", "")
            remote_ts = entry.timestamp_hlc
            if not local_ts or remote_ts > local_ts:
                merged = dict(existing)
                merged["blob_ref"] = entry.blob_ref
                field_timestamps = dict(ft)
                field_timestamps["blob_ref"] = remote_ts
                if not merged.get("id"):
                    merged["id"] = citekey
                merged["_field_timestamps"] = field_timestamps
                updated_records[citekey] = merged
            applied += 1
        elif entry.op == "unlink_file":
            existing = updated_records.get(citekey, {})
            ft = existing.get("_field_timestamps", {})
            local_ts = ft.get("blob_ref", "")
            remote_ts = entry.timestamp_hlc
            if not local_ts or remote_ts > local_ts:
                merged = dict(existing)
                merged["blob_ref"] = None
                field_timestamps = dict(ft)
                field_timestamps["blob_ref"] = remote_ts
                if not merged.get("id"):
                    merged["id"] = citekey
                merged["_field_timestamps"] = field_timestamps
                updated_records[citekey] = merged
            applied += 1

        if entry.timestamp_hlc > new_fence:
            new_fence = entry.timestamp_hlc

    try:
        await ctx.write_all(list(updated_records.values()))
    except Exception as exc:
        errors.append(f"write_all failed: {exc}")

    state["fence_pull_hlc"] = new_fence
    _save_sync_state(data_dir, state)
    return PullResult(
        applied_count=applied,
        rejected_count=rejected,
        conflicted_count=conflicted,
        errors=errors,
    )


async def create_snapshot(ctx: LibraryCtx) -> None:
    if not ctx.data_dir:
        return
    if not hasattr(ctx, "sync_config") or ctx.sync_config is None:
        return

    data_dir = Path(ctx.data_dir)
    records = await ctx.read_all()

    fence_hlc = ""
    change_log_dir = data_dir / "change_log"
    if change_log_dir.exists():
        for f in sorted(change_log_dir.iterdir()):
            if not f.is_file() or not f.suffix == ".json":
                continue
            try:
                entry = json.loads(f.read_text(encoding="utf-8"))
                ts = entry.get("timestamp_hlc", "")
                if ts > fence_hlc:
                    fence_hlc = ts
            except (ValueError, OSError):
                continue

    iso_timestamp = (
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    )
    snapshot = {"fence_hlc": fence_hlc, "library": records}
    remote_key = f"snapshots/{iso_timestamp}.json"

    with tempfile.NamedTemporaryFile(
        suffix=".json", delete=False, mode="w", encoding="utf-8"
    ) as tmp:
        json.dump(snapshot, tmp, ensure_ascii=False)
        tmp_path = Path(tmp.name)

    try:
        s3_sync.upload(ctx.sync_config, tmp_path, remote_key)
    finally:
        tmp_path.unlink(missing_ok=True)


def _detect_mime(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"


def _copy_to_files_dir(ctx: LibraryCtx, citekey: str, src: Path) -> FileRecord:
    files_dir = Path(ctx.files_dir)
    files_dir.mkdir(parents=True, exist_ok=True)
    dest = files_dir / f"{citekey}{src.suffix}"
    shutil.copy2(src, dest)
    return FileRecord(
        path=str(dest),
        mime_type=_detect_mime(str(dest)),
        size_bytes=dest.stat().st_size,
        added_at=datetime.now(timezone.utc).isoformat(),
    )


async def attach_file(ctx: LibraryCtx, citekey: str, path: str) -> Result:
    src = Path(path).resolve()
    if not src.exists():
        return Result(ok=False, error=f"file not found: {path}")

    records = await ctx.read_all()
    record = next((r for r in records if r.get("id") == citekey), None)
    if record is None:
        return Result(ok=False, error=f"not found: {citekey}")

    files_dir = Path(ctx.files_dir)
    if src.is_relative_to(files_dir):
        dest = src
    else:
        files_dir.mkdir(parents=True, exist_ok=True)
        dest = files_dir / f"{citekey}{src.suffix}"
        try:
            shutil.copy2(src, dest)
        except OSError as exc:
            return Result(ok=False, error=f"file copy failed: {exc}")

    file_record = FileRecord(
        path=dest.name,
        mime_type=_detect_mime(str(dest)),
        size_bytes=dest.stat().st_size,
        added_at=datetime.now(timezone.utc).isoformat(),
    )
    record["_file"] = file_record.model_dump()
    await ctx.write_all(records)
    return Result(ok=True)


async def detach_file(ctx: LibraryCtx, citekey: str) -> Result:
    records = await ctx.read_all()
    record = next((r for r in records if r.get("id") == citekey), None)
    if record is None:
        return Result(ok=False, error=f"not found: {citekey}")

    if record.get("blob_ref"):
        return Result(ok=False, error="file is synced — call unsync_file first")

    if not record.get("_file"):
        return Result(ok=False, error="no file attached")

    file_path = Path(ctx.files_dir) / record["_file"]["path"]
    try:
        file_path.unlink()
    except FileNotFoundError:
        pass

    record.pop("_file")
    await ctx.write_all(records)
    return Result(ok=True)


def _fetch_blob_ext(ctx: LibraryCtx, sha256: str) -> str:
    meta_key = f"blobs/{sha256}.meta"
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        s3_sync.download(ctx.sync_config, meta_key, tmp_path)
        meta = json.loads(tmp_path.read_text(encoding="utf-8"))
        return Path(meta.get("filename", "")).suffix
    except Exception:
        return ""
    finally:
        tmp_path.unlink(missing_ok=True)


async def get_file(ctx: LibraryCtx, citekey: str) -> Path | None:
    if not ctx.data_dir:
        return None

    records = await ctx.read_all()
    record = next((r for r in records if r.get("id") == citekey), None)
    if record is None:
        return None

    blob_ref = record.get("blob_ref")

    if ctx.sync_config is not None and blob_ref:
        sha256 = blob_ref.removeprefix("sha256:")
        data_dir = Path(ctx.data_dir)
        ensure_blob_cache_dir(data_dir)

        ext = _fetch_blob_ext(ctx, sha256)
        cache_path = blob_cache_path(data_dir, sha256, ext)

        legacy_path = blob_cache_path(data_dir, sha256)
        if legacy_path != cache_path and legacy_path.exists():
            legacy_path.unlink(missing_ok=True)

        if cache_path.exists():
            cached_sha256 = compute_sha256_streaming(cache_path)
            if cached_sha256 == sha256:
                return cache_path
            cache_path.unlink(missing_ok=True)

        try:
            s3_sync.download(ctx.sync_config, f"blobs/{sha256}", cache_path)
        except Exception:
            return None

        downloaded_sha256 = compute_sha256_streaming(cache_path)
        if downloaded_sha256 != sha256:
            cache_path.unlink(missing_ok=True)
            return None

        return cache_path

    file_rec = record.get("_file")
    if not file_rec:
        return None
    raw = file_rec["path"]
    p = Path(raw)
    if not p.is_absolute():
        p = Path(ctx.files_dir) / raw
    elif not p.exists():
        p = Path(ctx.files_dir) / p.name
    return p if p.exists() else None


async def unsync_file(ctx: LibraryCtx, citekey: str) -> Result:
    if not ctx.data_dir:
        return Result(ok=False, error="data_dir not configured")

    records = await ctx.read_all()
    record = next((r for r in records if r.get("id") == citekey), None)
    if record is None:
        return Result(ok=False, error=f"not found: {citekey}")

    if not record.get("blob_ref"):
        return Result(ok=False, error="file is not synced")

    data_dir = Path(ctx.data_dir)
    ts = hlc_service.now(ctx.peer_id)
    privkey = _load_privkey(ctx)

    entry_dict = {
        "op": "unlink_file",
        "uid": record.get("uid") or citekey,
        "uid_confidence": record.get("uid_confidence") or "",
        "citekey": citekey,
        "data": {},
        "blob_ref": None,
        "peer_id": ctx.peer_id,
        "device_id": ctx.device_id,
        "timestamp_hlc": ts,
        "signature": "",
    }
    if privkey is not None:
        entry_dict["signature"] = _sign_entry(entry_dict, privkey)

    entry = ChangeLogEntry.model_validate(entry_dict)
    _write_change_log_entry(data_dir, entry)

    record.pop("blob_ref")
    ft = dict(record.get("_field_timestamps", {}))
    ft["blob_ref"] = ts
    record["_field_timestamps"] = ft
    await ctx.write_all(records)

    return Result(ok=True)


async def prefetch_blobs(
    ctx: LibraryCtx, citekeys: list[str] | None = None
) -> PrefetchResult:
    if not ctx.data_dir:
        return PrefetchResult(
            fetched=0, already_cached=0, errors=["data_dir not configured"]
        )

    records = await ctx.read_all()
    if citekeys is not None:
        citekey_set = set(citekeys)
        records = [r for r in records if r.get("id") in citekey_set]

    data_dir = Path(ctx.data_dir)
    ensure_blob_cache_dir(data_dir)

    fetched = 0
    already_cached = 0
    errors = []

    for record in records:
        blob_ref = record.get("blob_ref")
        if not blob_ref:
            continue

        sha256 = blob_ref.removeprefix("sha256:")
        ext = _fetch_blob_ext(ctx, sha256)
        cache_path = blob_cache_path(data_dir, sha256, ext)

        legacy_path = blob_cache_path(data_dir, sha256)
        if legacy_path != cache_path and legacy_path.exists():
            legacy_path.unlink(missing_ok=True)

        if cache_path.exists():
            cached_sha256 = compute_sha256_streaming(cache_path)
            if cached_sha256 == sha256:
                already_cached += 1
                continue
            cache_path.unlink(missing_ok=True)

        if ctx.sync_config is None:
            errors.append(f"{record.get('id')}: sync not configured")
            continue

        try:
            s3_sync.download(ctx.sync_config, f"blobs/{sha256}", cache_path)
        except Exception as exc:
            errors.append(f"{record.get('id')}: download failed: {exc}")
            continue

        downloaded_sha256 = compute_sha256_streaming(cache_path)
        if downloaded_sha256 != sha256:
            cache_path.unlink(missing_ok=True)
            errors.append(f"{record.get('id')}: sha256 mismatch after download")
            continue

        fetched += 1

    return PrefetchResult(fetched=fetched, already_cached=already_cached, errors=errors)


async def sync_file(ctx: LibraryCtx, citekey: str) -> Result:
    records = await ctx.read_all()
    record = next((r for r in records if r.get("id") == citekey), None)
    if record is None:
        return Result(ok=False, error=f"not found: {citekey}")

    file_rec = record.get("_file")
    if not file_rec:
        return Result(ok=False, error="no file attached — call attach_file first")

    if ctx.sync_config is None:
        return Result(ok=False, error="sync not configured")

    file_path = Path(ctx.files_dir) / file_rec["path"]

    try:
        sha256 = compute_sha256_streaming(file_path)
    except OSError as exc:
        return Result(ok=False, error=f"hash failed: {exc}")

    blob_key = f"blobs/{sha256}"
    blob_ref = f"sha256:{sha256}"

    try:
        if not s3_sync.exists(ctx.sync_config, blob_key):
            s3_sync.upload(ctx.sync_config, file_path, blob_key)
    except Exception as exc:
        return Result(ok=False, error=f"blob upload failed: {exc}")

    ts = hlc_service.now(ctx.peer_id)
    meta = json.dumps(
        {
            "citekey": citekey,
            "filename": file_rec["path"],
            "uploaded_by": ctx.peer_id,
            "timestamp_hlc": ts,
        },
        ensure_ascii=False,
    ).encode()
    try:
        s3_sync.upload_bytes(ctx.sync_config, meta, f"{blob_key}.meta")
    except Exception as exc:
        return Result(ok=False, error=f"meta upload failed: {exc}")

    data_dir = Path(ctx.data_dir)
    privkey = _load_privkey(ctx)
    entry_dict = {
        "op": "link_file",
        "uid": record.get("uid") or citekey,
        "uid_confidence": record.get("uid_confidence") or "",
        "citekey": citekey,
        "data": {},
        "blob_ref": blob_ref,
        "peer_id": ctx.peer_id,
        "device_id": ctx.device_id,
        "timestamp_hlc": ts,
        "signature": "",
    }
    if privkey is not None:
        entry_dict["signature"] = _sign_entry(entry_dict, privkey)

    entry = ChangeLogEntry.model_validate(entry_dict)
    _write_change_log_entry(data_dir, entry)

    record["blob_ref"] = blob_ref
    ft = dict(record.get("_field_timestamps", {}))
    ft["blob_ref"] = ts
    record["_field_timestamps"] = ft
    await ctx.write_all(records)

    return Result(ok=True)
