"""Generación de citekeys con convención de la bóveda.

Configuración en CitekeySettings (config.json > citekey).
Defaults: {author[2]}{year}, separator="_", etal="_etal",
disambiguation_suffix="letters"
"""

import re
import unicodedata
import uuid

from scholartools.models import CitekeySettings

_STOP_WORDS = frozenset(
    {"a", "an", "the", "de", "el", "la", "les", "los", "das", "der", "die"}
)
_TOKEN_RE = re.compile(r"\{author\[(\d+)\]\}|\{year\}")
_DEFAULT = CitekeySettings()


def generate(ref: dict, settings: CitekeySettings = _DEFAULT) -> str:
    parts = []
    pos = 0
    for m in _TOKEN_RE.finditer(settings.pattern):
        if m.start() > pos:
            parts.append(settings.pattern[pos : m.start()])
        pos = m.end()
        if m.group(1) is not None:
            part = _eval_author(ref, int(m.group(1)), settings.separator, settings.etal)
        else:
            part = _issued_year(ref)
        if part is None:
            return f"ref{uuid.uuid4().hex[:6]}"
        parts.append(part)
    parts.append(settings.pattern[pos:])
    key = "".join(parts)
    return key if key else f"ref{uuid.uuid4().hex[:6]}"


def resolve_collision(
    key: str,
    existing: set[str],
    settings: CitekeySettings = _DEFAULT,
    ref: dict | None = None,
) -> str:
    if key not in existing:
        return key
    if settings.disambiguation_suffix != "letters" and ref is not None:
        n = int(settings.disambiguation_suffix[-1])
        words = _title_words(ref, n)
        if words:
            candidate = f"{key}{words}"
            if candidate not in existing:
                return candidate
    return _letter_collision(key, existing)


def _eval_author(ref: dict, max_n: int, separator: str, etal: str) -> str | None:
    authors = ref.get("author") or []
    names = [n for n in (_normalize(_family(a)) for a in authors) if n]
    if not names:
        return None
    if len(names) <= max_n:
        return separator.join(names)
    return f"{names[0]}{etal}"


def _title_words(ref: dict, n: int) -> str:
    title = ref.get("title") or ""
    words = [w for w in re.split(r"\W+", title.lower()) if w and w not in _STOP_WORDS]
    return "".join(_normalize(w) or w for w in words[:n])


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


def _letter_collision(key: str, existing: set[str]) -> str:
    for suffix in _letter_suffixes():
        candidate = f"{key}{suffix}"
        if candidate not in existing:
            return candidate
    return f"{key}{uuid.uuid4().hex[:4]}"


def _letter_suffixes():
    for c in "abcdefghijklmnopqrstuvwxyz":
        yield c
    for c in "abcdefghijklmnopqrstuvwxyz":
        yield f"a{c}"
