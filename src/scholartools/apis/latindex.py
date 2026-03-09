import httpx

from scholartools.ports import FetchFn, SearchFn

_BASE = "https://api.latindex.org/api"  # placeholder — Latindex API is restricted


def make_latindex(api_key: str | None = None) -> tuple[SearchFn, FetchFn]:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    async def search(query: str, limit: int) -> list[dict]:
        if not api_key:
            return []
        async with httpx.AsyncClient(headers=headers, timeout=10) as client:
            r = await client.get(
                f"{_BASE}/search",
                params={"q": query, "limit": limit},
            )
            r.raise_for_status()
            return [_normalize(item) for item in r.json().get("results", [])]

    async def fetch(identifier: str) -> dict | None:
        if not api_key:
            return None
        async with httpx.AsyncClient(headers=headers, timeout=10) as client:
            r = await client.get(f"{_BASE}/record/{identifier}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return _normalize(r.json())

    return search, fetch


def _normalize(item: dict) -> dict:
    out: dict = {"type": "article-journal"}
    if title := item.get("title"):
        out["title"] = title
    if issn := item.get("issn"):
        out["ISSN"] = issn
    if journal := item.get("journal"):
        out["container-title"] = journal
    if year := item.get("year"):
        out["issued"] = {"date-parts": [[int(year)]]}
    if authors := item.get("authors", []):
        out["author"] = [{"literal": a} if isinstance(a, str) else a for a in authors]
    return out
