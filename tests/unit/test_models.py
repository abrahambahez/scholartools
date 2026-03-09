import pytest
from pydantic import ValidationError

from scholartools.models import (
    AddResult,
    Author,
    DateField,
    ExtractResult,
    FileRecord,
    Reference,
    SearchResult,
)


def test_reference_minimal():
    ref = Reference(id="smith2020", type="article-journal")
    assert ref.id == "smith2020"
    assert ref.type == "article-journal"
    assert ref.title is None
    assert ref.warnings == []
    assert ref.file_record is None


def test_reference_requires_id():
    with pytest.raises(ValidationError):
        Reference(type="article-journal")


def test_reference_csl_json_passthrough():
    ref = Reference(id="x", type="book", publisher="MIT Press", edition="2nd")
    data = ref.model_dump(by_alias=True)
    assert data["publisher"] == "MIT Press"
    assert data["edition"] == "2nd"


def test_reference_file_alias():
    file_rec = FileRecord(
        path="smith2020.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        added_at="2026-03-07T00:00:00Z",
    )
    ref = Reference(id="smith2020", type="article-journal", _file=file_rec)
    data = ref.model_dump(by_alias=True)
    assert data["_file"]["path"] == "smith2020.pdf"
    assert ref.file_record.path == "smith2020.pdf"


def test_reference_warnings_alias():
    ref = Reference(id="x", type="book", _warnings=["missing title"])
    assert ref.warnings == ["missing title"]
    data = ref.model_dump(by_alias=True)
    assert data["_warnings"] == ["missing title"]


def test_author_institutional():
    author = Author(literal="World Health Organization")
    assert author.literal == "World Health Organization"
    assert author.family is None


def test_date_field_alias():
    date = DateField(**{"date-parts": [[2020, 3]]})
    assert date.date_parts == [[2020, 3]]
    data = date.model_dump(by_alias=True)
    assert data["date-parts"] == [[2020, 3]]


def test_search_result_defaults():
    result = SearchResult(
        references=[], sources_queried=["crossref"], total_found=0, errors=[]
    )
    assert result.total_found == 0
    assert result.errors == []


def test_extract_result_no_raise_on_error():
    result = ExtractResult(error="file not found")
    assert result.reference is None
    assert result.method_used is None
    assert result.confidence is None
    assert result.error == "file not found"


def test_add_result_success():
    result = AddResult(citekey="smith2020")
    assert result.citekey == "smith2020"
    assert result.error is None


def test_add_result_failure():
    result = AddResult(error="duplicate citekey")
    assert result.citekey is None
    assert result.error == "duplicate citekey"
