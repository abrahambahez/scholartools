from unittest.mock import AsyncMock, patch

import pytest

from scholartools.models import LibraryCtx
from scholartools.services.extract import _confidence, extract_from_file


def make_ctx(llm_extract=None, files_dir="data/files"):
    async def noop(*_):
        pass

    return LibraryCtx(
        read_all=AsyncMock(return_value=[]),
        write_all=noop,
        copy_file=noop,
        delete_file=noop,
        rename_file=noop,
        list_file_paths=AsyncMock(return_value=[]),
        files_dir=files_dir,
        api_sources=[],
        llm_extract=llm_extract,
    )


# --- confidence ---


def test_confidence_zero():
    assert _confidence({}) == 0.0


def test_confidence_partial():
    assert _confidence({"title": "X"}) == pytest.approx(1 / 3)


def test_confidence_full():
    fields = {
        "title": "X",
        "author": [{"family": "Smith"}],
        "issued": {"date-parts": [[2020]]},
    }
    assert _confidence(fields) == 1.0


# --- file not found ---


async def test_extract_file_not_found(tmp_path):
    ctx = make_ctx()
    result = await extract_from_file(str(tmp_path / "ghost.pdf"), ctx)
    assert result.reference is None
    assert result.error is not None
    assert "not found" in result.error


# --- pdfplumber path ---


async def test_extract_uses_pdfplumber_when_confident(tmp_path):
    good_fields = {
        "title": "Infrastructure in the Global South",
        "author": [{"family": "García"}],
        "issued": {"date-parts": [[2023]]},
    }
    fake = tmp_path / "fake.pdf"
    fake.write_bytes(b"")
    with patch(
        "scholartools.services.extract._extract_with_pdfplumber",
        return_value=(good_fields, 1.0),
    ):
        ctx = make_ctx()
        result = await extract_from_file(str(fake), ctx)

    assert result.method_used == "pdfplumber"
    assert result.confidence == 1.0
    assert result.reference.title == "Infrastructure in the Global South"


# --- LLM fallback ---


async def test_extract_falls_back_to_llm_on_low_confidence(tmp_path):
    low_fields = {"DOI": "10.1234/x"}  # no title/author/issued → low confidence
    llm_fields = {
        "title": "LLM Title",
        "author": [{"family": "Smith", "given": "J."}],
        "issued": {"date-parts": [[2022]]},
    }
    llm_mock = AsyncMock(return_value=llm_fields)
    fake = tmp_path / "fake.pdf"
    fake.write_bytes(b"")

    with patch(
        "scholartools.services.extract._extract_with_pdfplumber",
        return_value=(low_fields, 1 / 3),
    ):
        ctx = make_ctx(llm_extract=llm_mock)
        result = await extract_from_file(str(fake), ctx)

    assert result.method_used == "llm"
    assert result.reference.title == "LLM Title"
    llm_mock.assert_called_once()


async def test_extract_no_llm_returns_partial_result(tmp_path):
    partial_fields = {"title": "Some Title", "DOI": "10.1/x"}
    fake = tmp_path / "fake.pdf"
    fake.write_bytes(b"")
    with patch(
        "scholartools.services.extract._extract_with_pdfplumber",
        return_value=(partial_fields, 1 / 3),
    ):
        ctx = make_ctx(llm_extract=None)
        result = await extract_from_file(str(fake), ctx)

    assert result.method_used == "pdfplumber"
    assert result.reference.title == "Some Title"


async def test_extract_llm_returns_none_gives_error(tmp_path):
    with patch(
        "scholartools.services.extract._extract_with_pdfplumber", return_value=({}, 0.0)
    ):
        ctx = make_ctx(llm_extract=AsyncMock(return_value=None))
        result = await extract_from_file(str(tmp_path / "fake.pdf"), ctx)

    assert result.reference is None
    assert result.error is not None


async def test_extract_no_llm_no_fields_gives_error(tmp_path):
    with patch(
        "scholartools.services.extract._extract_with_pdfplumber", return_value=({}, 0.0)
    ):
        ctx = make_ctx(llm_extract=None)
        result = await extract_from_file(str(tmp_path / "fake.pdf"), ctx)

    assert result.reference is None
    assert result.error is not None


# --- result never raises ---


async def test_extract_never_raises_on_corrupt_file(tmp_path):
    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"not a pdf")
    ctx = make_ctx()
    result = await extract_from_file(str(corrupt), ctx)
    assert result is not None  # never raises
