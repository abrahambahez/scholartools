import httpx

from scholartools.ports import FetchFn, SearchFn

_BASE = "https://api.crossref.org"


def make_crossref(email: str | None = None) -> tuple[SearchFn, FetchFn]:
    headers = {"User-Agent": f"scholartools/0.1 (mailto:{email})"} if email else {}

    async def search(query: str, limit: int) -> list[dict]:
        async with httpx.AsyncClient(headers=headers, timeout=10) as client:
            r = await client.get(
                f"{_BASE}/works",
                params={
                    "query": query,
                    "rows": limit,
                    "select": "DOI,title,author,issued,container-title,type,URL",
                },
            )
            r.raise_for_status()
            return [_normalize(item) for item in r.json()["message"]["items"]]

    async def fetch(identifier: str) -> dict | None:
        async with httpx.AsyncClient(headers=headers, timeout=10) as client:
            r = await client.get(f"{_BASE}/works/{identifier}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return _normalize(r.json()["message"])

    return search, fetch


def _normalize(item: dict) -> dict:
    out: dict = {"type": _csl_type(item.get("type", ""))}
    if doi := item.get("DOI"):
        out["DOI"] = doi
    if titles := item.get("title"):
        out["title"] = titles[0] if titles else None
    if authors := item.get("author"):
        out["author"] = [
            {"family": a.get("family"), "given": a.get("given")} for a in authors
        ]
    if issued := item.get("issued", {}).get("date-parts"):
        out["issued"] = {"date-parts": issued}
    if journal := item.get("container-title"):
        out["container-title"] = journal[0] if journal else None
    if url := item.get("URL"):
        out["URL"] = url
    return out


def _csl_type(raw: str) -> str:
    mapping = {
        "journal-article": "article-journal",
        "book": "book",
        "book-chapter": "chapter",
        "proceedings-article": "paper-conference",
        "dissertation": "thesis",
    }
    return mapping.get(raw, "article-journal")
