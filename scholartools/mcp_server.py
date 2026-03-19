from mcp.server.fastmcp import FastMCP

import scholartools as st

mcp = FastMCP("scholartools")


@mcp.tool()
def discover(query: str, sources: list[str] | None = None, limit: int = 10) -> dict:
    """Use when you need to find new references on a topic or keyword. Returns candidates in staging — not committed to the library. Prefer `fetch` when you already have a specific identifier (DOI, arXiv ID, ISBN)."""
    return st.discover_references(query, sources=sources, limit=limit).model_dump()


@mcp.tool()
def fetch(identifier: str) -> dict:
    """Use when you have a specific identifier (DOI, arXiv ID, ISBN, PubMed ID). Resolves a single record and auto-stages it. Prefer over `discover` when the exact identifier is known."""
    return st.fetch_reference(identifier).model_dump()


@mcp.tool()
def ingest_file(file_path: str) -> dict:
    """Use when a local PDF or EPUB file path is provided. Extracts metadata and auto-stages the result with the file attached."""
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
    """Use when reviewing, trimming, or promoting staged references. Call with action='list' to see candidates, action='delete' to remove a specific citekey, or action='merge' to promote staged refs to the committed library."""
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


def main():
    mcp.run()
