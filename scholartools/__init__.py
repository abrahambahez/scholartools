import asyncio
import os

from scholartools.adapters.local import make_filestore, make_storage
from scholartools.apis.anthropic_extract import make_llm_extractor
from scholartools.apis.arxiv import make_arxiv
from scholartools.apis.crossref import make_crossref
from scholartools.apis.google_books import make_google_books
from scholartools.apis.latindex import make_latindex
from scholartools.apis.semantic_scholar import make_semantic_scholar
from scholartools.config import load_settings
from scholartools.models import (
    AddResult,
    DeleteResult,
    ExtractResult,
    FetchResult,
    FilesListResult,
    GetResult,
    LibraryCtx,
    LinkResult,
    ListResult,
    MoveResult,
    RenameResult,
    SearchResult,
    UnlinkResult,
    UpdateResult,
)
from scholartools.services import extract, fetch, files, search, store

_ctx: LibraryCtx | None = None


def _build_ctx() -> LibraryCtx:
    s = load_settings()
    read_all, write_all = make_storage(str(s.local.library_file))
    copy_file, delete_file, rename_file, list_file_paths = make_filestore(
        str(s.local.files_dir)
    )

    gbooks_api_key = os.environ.get("GBOOKS_API_KEY")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")

    source_map = {
        "crossref": lambda cfg: make_crossref(email=cfg.email),
        "semantic_scholar": lambda cfg: make_semantic_scholar(api_key=None),
        "arxiv": lambda cfg: make_arxiv(),
        "latindex": lambda cfg: make_latindex(api_key=None),
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
        api_sources=api_sources,
        llm_extract=llm_extract,
    )


def _get_ctx() -> LibraryCtx:
    global _ctx
    if _ctx is None:
        _ctx = _build_ctx()
    return _ctx


def _run(coro):
    return asyncio.run(coro)


def reset() -> None:
    """Fuerza recarga de config y contexto (útil en tests o tras cambiar .scholartools/config.json)."""
    global _ctx
    from scholartools.config import reset_settings

    reset_settings()
    _ctx = None


# --- public API ---


def add_reference(ref: dict) -> AddResult:
    return _run(store.add_reference(ref, _get_ctx()))


def get_reference(citekey: str) -> GetResult:
    return _run(store.get_reference(citekey, _get_ctx()))


def update_reference(citekey: str, fields: dict) -> UpdateResult:
    return _run(store.update_reference(citekey, fields, _get_ctx()))


def rename_reference(old_key: str, new_key: str) -> RenameResult:
    return _run(store.rename_reference(old_key, new_key, _get_ctx()))


def delete_reference(citekey: str) -> DeleteResult:
    return _run(store.delete_reference(citekey, _get_ctx()))


def list_references() -> ListResult:
    return _run(store.list_references(_get_ctx()))


def search_references(
    query: str, sources: list[str] | None = None, limit: int = 10
) -> SearchResult:
    return _run(
        search.search_references(query, _get_ctx(), sources=sources, limit=limit)
    )


def fetch_reference(identifier: str) -> FetchResult:
    return _run(fetch.fetch_reference(identifier, _get_ctx()))


def extract_from_file(file_path: str) -> ExtractResult:
    return _run(extract.extract_from_file(file_path, _get_ctx()))


def link_file(citekey: str, file_path: str) -> LinkResult:
    return _run(files.link_file(citekey, file_path, _get_ctx()))


def unlink_file(citekey: str) -> UnlinkResult:
    return _run(files.unlink_file(citekey, _get_ctx()))


def move_file(citekey: str, dest_name: str) -> MoveResult:
    return _run(files.move_file(citekey, dest_name, _get_ctx()))


def list_files() -> FilesListResult:
    return _run(files.list_files(_get_ctx()))
