"""Generación de citekeys con convención de la bóveda.

Convenciones:
  1 autor:   autor2024
  2 autores: autor1_autor22024
  3+ autores: autor_etal2024
"""

import re
import unicodedata
import uuid


def generate(ref: dict) -> str:
    authors = ref.get("author", [])
    year = _issued_year(ref)

    if not authors or not year:
        return f"ref{uuid.uuid4().hex[:6]}"

    if len(authors) == 1:
        family = _normalize(_family(authors[0]))
        return f"{family}{year}" if family else f"ref{uuid.uuid4().hex[:6]}"

    if len(authors) == 2:
        f1 = _normalize(_family(authors[0]))
        f2 = _normalize(_family(authors[1]))
        if f1 and f2:
            return f"{f1}_{f2}{year}"

    f1 = _normalize(_family(authors[0]))
    return f"{f1}_etal{year}" if f1 else f"ref{uuid.uuid4().hex[:6]}"


def resolve_collision(key: str, existing: set[str]) -> str:
    if key not in existing:
        return key
    for suffix in _letter_suffixes():
        candidate = f"{key}{suffix}"
        if candidate not in existing:
            return candidate
    return f"{key}{uuid.uuid4().hex[:4]}"


def _family(author: dict) -> str | None:
    if family := author.get("family"):
        return family
    if literal := author.get("literal"):
        parts = literal.rsplit(" ", 1)
        return parts[-1] if parts else literal
    return None


def _normalize(name: str | None) -> str | None:
    if not name:
        return None
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", ascii_name.lower()) or None


def _issued_year(ref: dict) -> str | None:
    issued = ref.get("issued") or {}
    date_parts = issued.get("date-parts", [])
    if date_parts and date_parts[0]:
        return str(date_parts[0][0])
    return None


def _letter_suffixes():
    for c in "abcdefghijklmnopqrstuvwxyz":
        yield c
    for c in "abcdefghijklmnopqrstuvwxyz":
        yield f"a{c}"
