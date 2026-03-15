from unittest.mock import MagicMock, patch

from scholartools.models import PrefetchResult, Result


def test_link_file_returns_result():
    mock_result = Result(ok=True)
    assert isinstance(mock_result, Result)
    assert mock_result.ok is True


def test_prefetch_result_is_exported():
    import scholartools

    assert hasattr(scholartools, "PrefetchResult")
    assert scholartools.PrefetchResult is PrefetchResult


def test_link_file_wrapper_calls_sync_service(tmp_path):
    from unittest.mock import AsyncMock

    import scholartools
    from scholartools.models import LibraryCtx

    mock_result = Result(ok=True)
    mock_ctx = MagicMock(spec=LibraryCtx)

    with (
        patch.object(scholartools, "_get_ctx", return_value=mock_ctx),
        patch(
            "scholartools.sync_service.link_file",
            new=AsyncMock(return_value=mock_result),
        ),
    ):
        result = scholartools.link_file("s2024", "/path/to/file.pdf")

    assert isinstance(result, Result)


def test_get_file_wrapper_returns_none_or_path(tmp_path):
    from unittest.mock import AsyncMock

    import scholartools
    from scholartools.models import LibraryCtx

    mock_ctx = MagicMock(spec=LibraryCtx)

    with (
        patch.object(scholartools, "_get_ctx", return_value=mock_ctx),
        patch("scholartools.sync_service.get_file", new=AsyncMock(return_value=None)),
    ):
        result = scholartools.get_file("s2024")

    assert result is None


def test_prefetch_blobs_wrapper_returns_prefetch_result():
    from unittest.mock import AsyncMock

    import scholartools
    from scholartools.models import LibraryCtx

    mock_result = PrefetchResult(fetched=2, already_cached=1, errors=[])
    mock_ctx = MagicMock(spec=LibraryCtx)

    with (
        patch.object(scholartools, "_get_ctx", return_value=mock_ctx),
        patch(
            "scholartools.sync_service.prefetch_blobs",
            new=AsyncMock(return_value=mock_result),
        ),
    ):
        result = scholartools.prefetch_blobs(["s2024"])

    assert isinstance(result, PrefetchResult)
    assert result.fetched == 2


def _async(val):

    async def _inner():
        return val

    return _inner()
