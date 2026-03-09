"""Adapter Google Books para resolución de ISBN a CSL-JSON."""

import httpx

from scholartools.ports import FetchFn, SearchFn

_BASE = "https://www.googleapis.com/books/v1/volumes"


def make_google_books(api_key: str | None = None) -> tuple[SearchFn, FetchFn]:
    async def search(query: str, limit: int) -> list[dict]:
        return []

    async def fetch(identifier: str) -> dict | None:
        isbn = _clean_isbn(identifier)
        if not isbn:
            return None
        params: dict = {"q": f"isbn:{isbn}"}
        if api_key:
            params["key"] = api_key
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(_BASE, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError:
            return None
        items = data.get("items", [])
        if not items:
            return None
        return _normalize(items[0]["volumeInfo"])

    return search, fetch


def _clean_isbn(identifier: str) -> str | None:
    cleaned = (
        identifier.upper()
        .replace("ISBN:", "")
        .replace("ISBN", "")
        .replace("-", "")
        .replace(" ", "")
        .strip()
    )
    if len(cleaned) in (10, 13) and cleaned.rstrip("X").isdigit():
        return cleaned
    return None


def _normalize(info: dict) -> dict:
    out: dict = {"type": "book"}

    title = info.get("title", "")
    if subtitle := info.get("subtitle"):
        title = f"{title}: {subtitle}"
    if title:
        out["title"] = title

    if authors := info.get("authors", []):
        out["author"] = [_split_name(a) for a in authors]

    if date := info.get("publishedDate", ""):
        try:
            out["issued"] = {"date-parts": [[int(date[:4])]]}
        except ValueError:
            pass

    if publisher := info.get("publisher"):
        out["publisher"] = publisher

    for ident in info.get("industryIdentifiers", []):
        if ident.get("type") in ("ISBN_13", "ISBN_10"):
            out["ISBN"] = ident["identifier"]
            break

    if pages := info.get("pageCount"):
        out["number-of-pages"] = pages

    if language := info.get("language"):
        out["language"] = language

    return out


def _split_name(name: str) -> dict:
    parts = name.rsplit(" ", 1)
    if len(parts) == 2:
        return {"given": parts[0], "family": parts[1]}
    return {"family": name}
