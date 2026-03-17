from unittest.mock import patch

import pytest

from scholartools.cli import _build_parser
from scholartools.models import ExtractResult, FetchResult, SearchResult


def _run(argv):
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.func(args)


def test_discover_default_args():
    result = SearchResult(references=[], sources_queried=[], total_found=0, errors=[])
    with patch("scholartools.discover_references", return_value=result) as mock_fn:
        with pytest.raises(SystemExit) as exc_info:
            _run(["discover", "query"])
        assert exc_info.value.code == 0
        mock_fn.assert_called_once_with("query", sources=None, limit=10)


def test_discover_with_sources_and_limit():
    result = SearchResult(references=[], sources_queried=[], total_found=0, errors=[])
    with patch("scholartools.discover_references", return_value=result) as mock_fn:
        with pytest.raises(SystemExit) as exc_info:
            _run(["discover", "query", "--sources", "crossref,arxiv", "--limit", "5"])
        assert exc_info.value.code == 0
        mock_fn.assert_called_once_with("query", sources=["crossref", "arxiv"], limit=5)


def test_fetch_calls_fetch_reference():
    result = FetchResult(reference=None, source="crossref")
    with patch("scholartools.fetch_reference", return_value=result) as mock_fn:
        with pytest.raises(SystemExit) as exc_info:
            _run(["fetch", "doi:10.1234/test"])
        assert exc_info.value.code == 0
        mock_fn.assert_called_once_with("doi:10.1234/test")


def test_extract_calls_extract_from_file():
    result = ExtractResult(reference=None, method_used="pdfplumber", confidence=0.9)
    with patch("scholartools.extract_from_file", return_value=result) as mock_fn:
        with pytest.raises(SystemExit) as exc_info:
            _run(["extract", "/path/to/file.pdf"])
        assert exc_info.value.code == 0
        mock_fn.assert_called_once_with("/path/to/file.pdf")
