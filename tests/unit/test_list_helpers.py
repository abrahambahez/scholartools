from scholartools.models import Author
from scholartools.services.list_helpers import (
    format_authors,
    paginate,
    to_reference_row,
)

# --- format_authors ---


def test_format_authors_none():
    assert format_authors(None) is None


def test_format_authors_empty():
    assert format_authors([]) is None


def test_format_authors_single():
    assert format_authors([Author(family="Smith", given="John")]) == "Smith, John"


def test_format_authors_family_only():
    assert format_authors([Author(family="Smith")]) == "Smith"


def test_format_authors_literal():
    assert format_authors([Author(literal="UNESCO")]) == "UNESCO"


def test_format_authors_multiple():
    authors = [Author(family="A"), Author(family="B"), Author(family="C")]
    assert format_authors(authors) == "A; B; C"


def test_format_authors_exactly_five():
    authors = [Author(family=str(i)) for i in range(5)]
    result = format_authors(authors)
    assert "et al." not in result
    assert result.count(";") == 4


def test_format_authors_six_adds_et_al():
    authors = [Author(family=str(i)) for i in range(6)]
    result = format_authors(authors)
    assert result.endswith("; et al.")
    assert result.count(";") == 5


# --- paginate ---


def test_paginate_empty():
    items, page, pages = paginate([], 1)
    assert items == []
    assert page == 1
    assert pages == 1


def test_paginate_first_page():
    items = list(range(25))
    result, page, pages = paginate(items, 1)
    assert result == list(range(10))
    assert page == 1
    assert pages == 3


def test_paginate_last_page_partial():
    items = list(range(25))
    result, page, pages = paginate(items, 3)
    assert result == list(range(20, 25))
    assert page == 3


def test_paginate_out_of_range_clamps_to_last():
    items = list(range(5))
    result, page, pages = paginate(items, 99)
    assert result == list(range(5))
    assert page == 1
    assert pages == 1


def test_paginate_exact_multiple():
    items = list(range(20))
    result, page, pages = paginate(items, 2)
    assert result == list(range(10, 20))
    assert pages == 2


# --- to_reference_row ---


def test_to_reference_row_basic():
    record = {
        "id": "smith2024",
        "type": "article-journal",
        "title": "A Study",
        "author": [{"family": "Smith", "given": "John"}],
        "issued": {"date-parts": [[2024]]},
    }
    row = to_reference_row(record)
    assert row.citekey == "smith2024"
    assert row.title == "A Study"
    assert row.authors == "Smith, John"
    assert row.year == 2024
    assert row.has_warnings is False


def test_to_reference_row_missing_fields_sets_has_warnings():
    record = {"id": "x", "type": "book"}
    row = to_reference_row(record)
    assert row.has_warnings is True


def test_to_reference_row_has_file():
    record = {
        "id": "x",
        "type": "book",
        "_file": {
            "path": "/lib/x.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 100,
            "added_at": "2024-01-01T00:00:00+00:00",
        },
    }
    row = to_reference_row(record)
    assert row.has_file is True


def test_to_reference_row_doi_from_extra():
    record = {"id": "x", "type": "book", "doi": "10.1234/test"}
    row = to_reference_row(record)
    assert row.doi == "10.1234/test"
