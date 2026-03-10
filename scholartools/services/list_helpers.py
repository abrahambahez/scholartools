import math

from scholartools.models import Author, Reference, ReferenceRow

_REQUIRED = ("id", "type", "title", "author", "issued")
_PAGE_SIZE = 10


def format_authors(authors: list[Author] | None) -> str | None:
    if not authors:
        return None
    parts = []
    for a in authors[:5]:
        if a.family and a.given:
            parts.append(f"{a.family}, {a.given}")
        elif a.family:
            parts.append(a.family)
        elif a.literal:
            parts.append(a.literal)
    if not parts:
        return None
    result = "; ".join(parts)
    if len(authors) > 5:
        result += "; et al."
    return result


def paginate(items: list, page: int) -> tuple[list, int, int]:
    total = len(items)
    pages = max(1, math.ceil(total / _PAGE_SIZE))
    page = max(1, min(page, pages))
    start = (page - 1) * _PAGE_SIZE
    return items[start : start + _PAGE_SIZE], page, pages


def to_reference_row(record: dict) -> ReferenceRow:
    ref = Reference.model_validate(record)
    has_warnings = any(not record.get(f) for f in _REQUIRED)

    year = None
    if ref.issued and ref.issued.date_parts:
        parts = ref.issued.date_parts
        if parts and parts[0]:
            year = parts[0][0]

    doi = ref.DOI or (ref.model_extra or {}).get("doi")

    return ReferenceRow(
        citekey=ref.id,
        title=ref.title,
        authors=format_authors(ref.author),
        year=year,
        doi=doi,
        has_file=ref.file_record is not None,
        has_warnings=has_warnings,
    )
