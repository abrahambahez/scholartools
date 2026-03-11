import hashlib
import json
import unicodedata
from typing import Literal

from scholartools.models import Reference


def _normalize_text(text: str) -> str:
    nfc = unicodedata.normalize("NFC", text)
    lowered = nfc.lower()
    stripped = "".join(
        c for c in lowered if unicodedata.category(c)[0] not in ("P", "S")
    )
    return " ".join(stripped.split())


def _normalize_isbn(isbn: str) -> str:
    cleaned = isbn.replace("-", "").replace(" ", "")
    if len(cleaned) != 10:
        return cleaned
    base = "978" + cleaned[:9]
    total = sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(base))
    check = (10 - (total % 10)) % 10
    return base + str(check)


def compute_uid(ref: Reference) -> tuple[str, Literal["authoritative", "semantic"]]:
    extra = ref.model_extra or {}

    if ref.DOI:
        key = f"doi:{ref.DOI.lower().strip()}"
        return hashlib.sha256(key.encode()).hexdigest()[:16], "authoritative"

    arxiv = extra.get("arXiv-ID") or extra.get("arxiv")
    if arxiv:
        key = f"arxiv:{str(arxiv).strip()}"
        return hashlib.sha256(key.encode()).hexdigest()[:16], "authoritative"

    _CONTAINER_TYPES = {
        "chapter",
        "entry-encyclopedia",
        "entry-dictionary",
        "paper-conference",
    }
    isbn = extra.get("ISBN")
    if isbn and ref.type not in _CONTAINER_TYPES:
        raw = isbn if isinstance(isbn, str) else isbn[0]
        key = f"isbn:{_normalize_isbn(raw)}"
        return hashlib.sha256(key.encode()).hexdigest()[:16], "authoritative"

    canonical: dict = {}
    if ref.title:
        canonical["title"] = _normalize_text(ref.title)
    if ref.issued and ref.issued.date_parts and ref.issued.date_parts[0]:
        canonical["year"] = ref.issued.date_parts[0][0]
    if ref.author and ref.author[0].family:
        canonical["first_author"] = _normalize_text(ref.author[0].family)
    canonical["type"] = ref.type

    key = json.dumps(canonical, sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()[:16], "semantic"
