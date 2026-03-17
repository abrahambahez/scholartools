import asyncio
import os

from scholartools.adapters.local import (
    make_filestore,
    make_staging_storage,
    make_storage,
)
from scholartools.adapters.sync_composite import make_sync_storage
from scholartools.apis.anthropic_extract import make_llm_extractor
from scholartools.apis.arxiv import make_arxiv
from scholartools.apis.crossref import make_crossref
from scholartools.apis.doaj import make_doaj
from scholartools.apis.google_books import make_google_books
from scholartools.apis.openalex import make_openalex
from scholartools.apis.semantic_scholar import make_semantic_scholar
from scholartools.config import load_settings
from scholartools.models import (
    AddResult,
    ChangeLogEntry,
    ConflictRecord,
    DeleteResult,
    DeleteStagedResult,
    ExtractResult,
    FetchResult,
    FilesListResult,
    GetResult,
    LibraryCtx,
    ListResult,
    ListStagedResult,
    MergeResult,
    MoveResult,
    PeerAddDeviceResult,
    PeerIdentity,
    PeerInitResult,
    PeerRegisterResult,
    PeerRevokeDeviceResult,
    PeerRevokeResult,
    PrefetchResult,
    PullResult,
    PushResult,
    Reference,
    RenameResult,
    Result,
    SearchResult,
    StageResult,
    UpdateResult,
)
from scholartools.models import (
    DeviceIdentity as DeviceIdentity,
)
from scholartools.models import (
    FileRow as FileRow,
)
from scholartools.models import (
    LinkResult as LinkResult,
)
from scholartools.models import (
    PeerRecord as PeerRecord,
)
from scholartools.models import (
    PeerSettings as PeerSettings,
)
from scholartools.models import (
    ReferenceRow as ReferenceRow,
)
from scholartools.models import (
    SyncConfig as SyncConfig,
)
from scholartools.models import (
    UnlinkResult as UnlinkResult,
)
from scholartools.models import (
    VerifyEntryResult as VerifyEntryResult,
)
from scholartools.services import extract, fetch, files, search, store
from scholartools.services import merge as merge_service
from scholartools.services import peers as peers_service
from scholartools.services import staging as staging_service
from scholartools.services import sync as sync_service

_ctx: LibraryCtx | None = None


def _build_ctx() -> LibraryCtx:
    s = load_settings()
    if s.sync:
        read_all, write_all = make_sync_storage(
            str(s.local.library_file),
            str(s.local.library_dir),
            s.peer.peer_id if s.peer else "",
            s.peer.device_id if s.peer else "",
        )
    else:
        read_all, write_all = make_storage(str(s.local.library_file))
    copy_file, delete_file, rename_file, list_file_paths = make_filestore(
        str(s.local.files_dir)
    )
    staging_read_all, staging_write_all = make_staging_storage(
        str(s.local.staging_file), str(s.local.staging_dir)
    )
    staging_copy_file, staging_delete_file, _, _ = make_filestore(
        str(s.local.staging_dir)
    )

    gbooks_api_key = os.environ.get("GBOOKS_API_KEY")
    ss_api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")

    email = s.apis.email
    source_map = {
        "crossref": lambda cfg: make_crossref(email=email),
        "semantic_scholar": lambda cfg: make_semantic_scholar(api_key=ss_api_key),
        "arxiv": lambda cfg: make_arxiv(),
        "openalex": lambda cfg: make_openalex(email=email),
        "doaj": lambda cfg: make_doaj(),
        "google_books": lambda cfg: (
            make_google_books(api_key=gbooks_api_key) if gbooks_api_key else None
        ),
    }

    api_sources = []
    for cfg in s.apis.sources:
        if not cfg.enabled or cfg.name not in source_map:
            continue
        result = source_map[cfg.name](cfg)
        if result is None:
            continue
        search_fn, fetch_fn = result
        api_sources.append({"name": cfg.name, "search": search_fn, "fetch": fetch_fn})

    llm_extract = (
        make_llm_extractor(anthropic_api_key, s.llm.model)
        if anthropic_api_key
        else None
    )

    return LibraryCtx(
        read_all=read_all,
        write_all=write_all,
        copy_file=copy_file,
        delete_file=delete_file,
        rename_file=rename_file,
        list_file_paths=list_file_paths,
        files_dir=str(s.local.files_dir),
        staging_read_all=staging_read_all,
        staging_write_all=staging_write_all,
        staging_copy_file=staging_copy_file,
        staging_delete_file=staging_delete_file,
        staging_dir=str(s.local.staging_dir),
        api_sources=api_sources,
        llm_extract=llm_extract,
        citekey_settings=s.citekey,
        peers_dir=str(s.local.peers_dir),
        data_dir=str(s.local.library_dir),
        peer_id=s.peer.peer_id if s.peer else "",
        device_id=s.peer.device_id if s.peer else "",
        sync_config=s.sync,
    )


def _get_ctx() -> LibraryCtx:
    global _ctx
    if _ctx is None:
        _ctx = _build_ctx()
    return _ctx


def _run(coro):
    return asyncio.run(coro)


def reset() -> None:
    """Fuerza recarga de config y contexto
    (útil en tests o tras cambiar .scholartools/config.json)."""
    global _ctx
    from scholartools.config import reset_settings

    reset_settings()
    _ctx = None


# --- public API ---


def add_reference(ref: dict) -> AddResult:
    return _run(store.add_reference(ref, _get_ctx()))


def get_reference(citekey: str | None = None, uid: str | None = None) -> GetResult:
    return _run(store.get_reference(_get_ctx(), citekey=citekey, uid=uid))


def update_reference(citekey: str, fields: dict) -> UpdateResult:
    return _run(store.update_reference(citekey, fields, _get_ctx()))


def rename_reference(old_key: str, new_key: str) -> RenameResult:
    return _run(store.rename_reference(old_key, new_key, _get_ctx()))


def delete_reference(citekey: str) -> DeleteResult:
    return _run(store.delete_reference(citekey, _get_ctx()))


def list_references(page: int = 1) -> ListResult:
    return _run(store.list_references(_get_ctx(), page))


def filter_references(
    query: str | None = None,
    author: str | None = None,
    year: int | None = None,
    ref_type: str | None = None,
    has_file: bool | None = None,
    staging: bool = False,
    page: int = 1,
) -> ListResult:
    return _run(
        store.filter_references(
            _get_ctx(),
            query=query,
            author=author,
            year=year,
            ref_type=ref_type,
            has_file=has_file,
            staging=staging,
            page=page,
        )
    )


def discover_references(
    query: str, sources: list[str] | None = None, limit: int = 10
) -> SearchResult:
    return _run(
        search.discover_references(query, _get_ctx(), sources=sources, limit=limit)
    )


def fetch_reference(identifier: str) -> FetchResult:
    return _run(fetch.fetch_reference(identifier, _get_ctx()))


def extract_from_file(file_path: str) -> ExtractResult:
    return _run(extract.extract_from_file(file_path, _get_ctx()))


def link_file(citekey: str, file_path: str) -> Result:
    return _run(sync_service.link_file(_get_ctx(), citekey, file_path))


def unlink_file(citekey: str) -> Result:
    return _run(sync_service.unlink_file(_get_ctx(), citekey))


def get_file(citekey: str):
    return _run(sync_service.get_file(_get_ctx(), citekey))


def prefetch_blobs(citekeys: list[str] | None = None) -> PrefetchResult:
    return _run(sync_service.prefetch_blobs(_get_ctx(), citekeys))


def move_file(citekey: str, dest_name: str) -> MoveResult:
    return _run(files.move_file(citekey, dest_name, _get_ctx()))


def list_files(page: int = 1) -> FilesListResult:
    return _run(files.list_files(_get_ctx(), page))


def stage_reference(ref: dict, file_path: str | None = None) -> StageResult:
    return _run(
        staging_service.stage_reference(
            Reference.model_validate(ref), file_path, _get_ctx()
        )
    )


def list_staged(page: int = 1) -> ListStagedResult:
    return _run(staging_service.list_staged(_get_ctx(), page))


def delete_staged(citekey: str) -> DeleteStagedResult:
    return _run(staging_service.delete_staged(citekey, _get_ctx()))


def merge(omit: list[str] | None = None, allow_semantic: bool = False) -> MergeResult:
    return _run(merge_service.merge(omit, _get_ctx(), allow_semantic=allow_semantic))


def peer_init(peer_id: str, device_id: str) -> PeerInitResult:
    return _run(peers_service.peer_init(peer_id, device_id, _get_ctx()))


def peer_register(identity: PeerIdentity) -> PeerRegisterResult:
    return _run(peers_service.peer_register(identity, _get_ctx()))


def peer_add_device(peer_id: str, device_identity: PeerIdentity) -> PeerAddDeviceResult:
    return _run(peers_service.peer_add_device(peer_id, device_identity, _get_ctx()))


def peer_revoke_device(peer_id: str, device_id: str) -> PeerRevokeDeviceResult:
    return _run(peers_service.peer_revoke_device(peer_id, device_id, _get_ctx()))


def peer_revoke(peer_id: str) -> PeerRevokeResult:
    return _run(peers_service.peer_revoke(peer_id, _get_ctx()))


def peer_register_self() -> Result:
    return _run(peers_service.peer_register_self(_get_ctx()))


def push() -> PushResult:
    return _run(sync_service.push(_get_ctx()))


def pull() -> PullResult:
    return _run(sync_service.pull(_get_ctx()))


def create_snapshot() -> None:
    return _run(sync_service.create_snapshot(_get_ctx()))


def list_conflicts() -> list[ConflictRecord]:
    from pathlib import Path

    from scholartools.adapters.conflicts_store import read_conflicts

    ctx = _get_ctx()
    if not ctx.data_dir:
        return []
    return read_conflicts(Path(ctx.data_dir))


def resolve_conflict(uid: str, field: str, winning_value) -> Result:
    import json
    import tempfile
    from pathlib import Path

    from scholartools.adapters import conflicts_store, s3_sync
    from scholartools.config import CONFIG_PATH
    from scholartools.services import peers as _peers

    ctx = _get_ctx()
    if not ctx.data_dir:
        return Result(ok=False, error="data_dir not configured")
    if not ctx.sync_config:
        return Result(ok=False, error="sync not configured")

    from scholartools.services.hlc import now as hlc_now

    ts = hlc_now(ctx.peer_id)

    key_path = CONFIG_PATH.parent / "keys" / ctx.peer_id / f"{ctx.device_id}.key"
    if not key_path.exists():
        return Result(ok=False, error="local device keypair not found")
    privkey = key_path.read_bytes()

    entry_dict = {
        "op": "update_reference",
        "uid": uid,
        "uid_confidence": "",
        "citekey": uid,
        "data": {field: winning_value},
        "peer_id": ctx.peer_id,
        "device_id": ctx.device_id,
        "timestamp_hlc": ts,
    }
    payload = _peers._canonical(entry_dict)
    entry_dict["signature"] = _peers._sign(payload, privkey)

    remote_key = f"changes/{ctx.peer_id}/{ts}.json"
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            json.dump(entry_dict, tmp, ensure_ascii=False)
            tmp_path = Path(tmp.name)
        s3_sync.upload(ctx.sync_config, tmp_path, remote_key)
        tmp_path.unlink(missing_ok=True)
    except Exception as exc:
        return Result(ok=False, error=str(exc))

    conflicts_store.delete_conflict(Path(ctx.data_dir), uid, field)
    return Result(ok=True)


def restore_reference(citekey: str) -> Result:
    from pathlib import Path

    from scholartools.services.hlc import now as hlc_now

    ctx = _get_ctx()
    if not ctx.data_dir:
        return Result(ok=False, error="data_dir not configured")

    ts = hlc_now(ctx.peer_id)
    entry = ChangeLogEntry(
        op="restore_reference",
        uid="",
        uid_confidence="",
        citekey=citekey,
        data={},
        peer_id=ctx.peer_id,
        device_id=ctx.device_id,
        timestamp_hlc=ts,
        signature="",
    )
    log_dir = Path(ctx.data_dir) / "change_log"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{ts}.json").write_text(entry.model_dump_json(), encoding="utf-8")
    return Result(ok=True)
