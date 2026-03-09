import re
import xml.etree.ElementTree as ET

import httpx

from scholartools.ports import FetchFn, SearchFn

_BASE = "https://export.arxiv.org/api"
_NS = {"atom": "http://www.w3.org/2005/Atom"}
_ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5}(?:v\d+)?)")


def make_arxiv() -> tuple[SearchFn, FetchFn]:
    async def search(query: str, limit: int) -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{_BASE}/query",
                params={"search_query": f"all:{query}", "max_results": limit},
            )
            r.raise_for_status()
            return _parse_feed(r.text)

    async def fetch(identifier: str) -> dict | None:
        arxiv_id = _extract_id(identifier)
        if not arxiv_id:
            return None
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{_BASE}/query", params={"id_list": arxiv_id})
            r.raise_for_status()
            results = _parse_feed(r.text)
            return results[0] if results else None

    return search, fetch


def _parse_feed(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    return [_normalize(e) for e in root.findall("atom:entry", _NS)]


def _normalize(entry) -> dict:
    def text(tag):
        el = entry.find(tag, _NS)
        return el.text.strip() if el is not None and el.text else None

    out: dict = {"type": "article-journal"}
    if title := text("atom:title"):
        out["title"] = title.replace("\n", " ")
    if authors := entry.findall("atom:author", _NS):
        out["author"] = [
            {"literal": a.find("atom:name", _NS).text}
            for a in authors
            if a.find("atom:name", _NS) is not None
        ]
    if published := text("atom:published"):
        year = int(published[:4])
        out["issued"] = {"date-parts": [[year]]}
    if link := entry.find("atom:id", _NS):
        url = link.text.strip() if link.text else ""
        out["URL"] = url
        m = _ARXIV_ID_RE.search(url)
        if m:
            out["DOI"] = f"10.48550/arXiv.{m.group(1)}"
    return out


def _extract_id(identifier: str) -> str | None:
    m = _ARXIV_ID_RE.search(identifier)
    return m.group(1) if m else None
