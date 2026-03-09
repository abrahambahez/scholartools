import httpx

from scholartools.ports import FetchFn, SearchFn

_BASE = "https://api.semanticscholar.org/graph/v1"
_FIELDS = "title,authors,year,externalIds,venue,url,publicationTypes"


def make_semantic_scholar(api_key: str | None = None) -> tuple[SearchFn, FetchFn]:
    headers = {"x-api-key": api_key} if api_key else {}

    async def search(query: str, limit: int) -> list[dict]:
        async with httpx.AsyncClient(headers=headers, timeout=10) as client:
            r = await client.get(
                f"{_BASE}/paper/search",
                params={"query": query, "limit": limit, "fields": _FIELDS},
            )
            r.raise_for_status()
            return [_normalize(p) for p in r.json().get("data", [])]

    async def fetch(identifier: str) -> dict | None:
        async with httpx.AsyncClient(headers=headers, timeout=10) as client:
            r = await client.get(
                f"{_BASE}/paper/{identifier}", params={"fields": _FIELDS}
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return _normalize(r.json())

    return search, fetch


def _normalize(item: dict) -> dict:
    out: dict = {"type": "article-journal"}
    if title := item.get("title"):
        out["title"] = title
    if authors := item.get("authors"):
        out["author"] = [_split_name(a.get("name", "")) for a in authors]
    if year := item.get("year"):
        out["issued"] = {"date-parts": [[year]]}
    if doi := (item.get("externalIds") or {}).get("DOI"):
        out["DOI"] = doi
    if venue := item.get("venue"):
        out["container-title"] = venue
    if url := item.get("url"):
        out["URL"] = url
    return out


def _split_name(name: str) -> dict:
    parts = name.rsplit(" ", 1)
    if len(parts) == 2:
        return {"given": parts[0], "family": parts[1]}
    return {"family": name}
