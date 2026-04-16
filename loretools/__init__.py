import asyncio

from loretools.adapters.local import (
    make_filestore,
    make_staging_storage,
    make_storage,
)
from loretools.config import load_settings
from loretools.models import (
    AddResult,
    AttachResult,
    DeleteResult,
    DeleteStagedResult,
    DetachResult,
    ExtractResult,
    FilesListResult,
    GetFileResult,
    GetResult,
    LibraryCtx,
    ListResult,
    ListStagedResult,
    MergeResult,
    MoveResult,
    Reference,
    ReindexResult,
    RenameResult,
    StageResult,
    UpdateResult,
)
from loretools.models import (
    FileRow as FileRow,
)
from loretools.models import (
    ReferenceRow as ReferenceRow,
)
from loretools.services import extract, files, store
from loretools.services import merge as merge_service
from loretools.services import staging as staging_service

_ctx: LibraryCtx | None = None


def _build_ctx() -> LibraryCtx:
    s = load_settings()
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
        citekey_settings=s.citekey,
    )


def _get_ctx() -> LibraryCtx:
    global _ctx
    if _ctx is None:
        _ctx = _build_ctx()
    return _ctx


def _run(coro):
    return asyncio.run(coro)


def reset() -> None:
    global _ctx
    from loretools.config import reset_settings

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


def extract_from_file(file_path: str) -> ExtractResult:
    return _run(extract.extract_from_file(file_path, _get_ctx()))


def attach_file(citekey: str, path: str) -> AttachResult:
    return _run(files.attach_file(_get_ctx(), citekey, path))


def detach_file(citekey: str) -> DetachResult:
    return _run(files.detach_file(_get_ctx(), citekey))


def get_file(citekey: str) -> GetFileResult:
    path = _run(files.get_file(_get_ctx(), citekey))
    return GetFileResult(path=str(path) if path is not None else None)


def reindex_files() -> ReindexResult:
    return _run(files.reindex_files(_get_ctx()))


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
