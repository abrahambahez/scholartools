from mcp.server.fastmcp import FastMCP

import scholartools as st

mcp = FastMCP("scholartools")


@mcp.tool()
def discover(query: str, sources: list[str] | None = None, limit: int = 10) -> dict:
    """Use when you need to find new references on a topic or keyword.

    Returns candidates in staging — not committed to the library.
    Prefer `fetch` when you already have a specific identifier (DOI, arXiv ID, ISBN).
    """
    return st.discover_references(query, sources=sources, limit=limit).model_dump()


@mcp.tool()
def fetch(identifier: str) -> dict:
    """Use when you have a specific identifier (DOI, arXiv ID, ISBN, PubMed ID).

    Resolves a single record and auto-stages it.
    Prefer over `discover` when the exact identifier is known.
    """
    return st.fetch_reference(identifier).model_dump()


@mcp.tool()
def ingest_file(file_path: str) -> dict:
    """Use when a local PDF or EPUB file path is provided.

    Extracts metadata and auto-stages the result with the file attached.
    """
    if ".." in file_path:
        return {"error": "path traversal not allowed"}
    return st.extract_from_file(file_path).model_dump()


@mcp.tool()
def staging(
    action: str,
    page: int = 1,
    citekey: str | None = None,
    omit: list[str] | None = None,
    allow_semantic: bool = False,
) -> dict:
    """Use when reviewing, trimming, or promoting staged references.

    action='list' to see candidates, action='delete' to remove a citekey,
    action='merge' to promote staged refs to the committed library.
    """
    if action == "list":
        return st.list_staged(page=page).model_dump()
    elif action == "delete":
        if not citekey:
            return {"error": "citekey required for delete"}
        return st.delete_staged(citekey).model_dump()
    elif action == "merge":
        return st.merge(omit=omit, allow_semantic=allow_semantic).model_dump()
    else:
        return {"error": f"unknown action: {action}"}


@mcp.tool()
def library(
    action: str,
    query: str | None = None,
    author: str | None = None,
    year: int | None = None,
    ref_type: str | None = None,
    has_file: bool | None = None,
    citekey: str | None = None,
    page: int = 1,
) -> dict:
    """Use when querying the committed library. Read-only.

    Use manage_reference for writes. action='list', action='filter'
    (query/author/year/ref_type/has_file), action='get' with citekey.
    """
    if action == "list":
        return st.list_references(page=page).model_dump()
    elif action == "filter":
        return st.filter_references(
            query=query,
            author=author,
            year=year,
            ref_type=ref_type,
            has_file=has_file,
            page=page,
        ).model_dump()
    elif action == "get":
        if not citekey:
            return {"error": "citekey required for get"}
        return st.get_reference(citekey).model_dump()
    else:
        return {"error": f"unknown action: {action}"}


@mcp.tool()
def manage_reference(
    action: str,
    ref: dict | None = None,
    citekey: str | None = None,
    fields: dict | None = None,
    old_key: str | None = None,
    new_key: str | None = None,
) -> dict:
    """Use when mutating committed library records. Separate from library (read-only).

    action='add' with ref dict, action='update' with citekey and fields dict,
    action='delete' with citekey, action='rename' with old_key and new_key.
    """
    if action == "add":
        if ref is None:
            return {"error": "ref required for add"}
        return st.add_reference(ref).model_dump()
    elif action == "update":
        if not citekey:
            return {"error": "citekey required for update"}
        return st.update_reference(citekey, fields or {}).model_dump()
    elif action == "delete":
        if not citekey:
            return {"error": "citekey required for delete"}
        return st.delete_reference(citekey).model_dump()
    elif action == "rename":
        if not old_key or not new_key:
            return {"error": "old_key and new_key required for rename"}
        return st.rename_reference(old_key, new_key).model_dump()
    else:
        return {"error": f"unknown action: {action}"}


@mcp.tool()
def files(
    action: str,
    citekey: str | None = None,
    file_path: str | None = None,
    dest_name: str | None = None,
    page: int = 1,
) -> dict:
    """Use when attaching, detaching, moving, or listing PDF files for library records.

    action='link' with citekey/file_path, action='unlink' with citekey,
    action='move' with citekey/dest_name, action='list' to see all archived files.
    """
    if file_path and ".." in file_path:
        return {"error": "path traversal not allowed"}
    if action == "link":
        if not citekey or not file_path:
            return {"error": "citekey and file_path required for link"}
        return st.link_file(citekey, file_path).model_dump()
    elif action == "unlink":
        if not citekey:
            return {"error": "citekey required for unlink"}
        return st.unlink_file(citekey).model_dump()
    elif action == "move":
        if not citekey or not dest_name:
            return {"error": "citekey and dest_name required for move"}
        return st.move_file(citekey, dest_name).model_dump()
    elif action == "list":
        return st.list_files(page=page).model_dump()
    else:
        return {"error": f"unknown action: {action}"}


def main():
    mcp.run()
