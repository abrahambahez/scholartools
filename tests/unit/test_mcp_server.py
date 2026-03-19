from unittest.mock import MagicMock, patch

import scholartools.mcp_server as mcp_server


def test_module_imports():
    assert mcp_server is not None


def test_main_is_callable():
    assert callable(mcp_server.main)


def test_mcp_instance_exists():
    assert mcp_server.mcp is not None


def test_discover_returns_dict():
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {"items": [], "total": 0}
    with patch(
        "scholartools.mcp_server.st.discover_references", return_value=mock_result
    ):
        result = mcp_server.discover("machine learning")
    assert isinstance(result, dict)


def test_fetch_returns_dict():
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {
        "reference": None,
        "source": None,
        "error": None,
    }
    with patch("scholartools.mcp_server.st.fetch_reference", return_value=mock_result):
        result = mcp_server.fetch("10.1234/test")
    assert isinstance(result, dict)


def test_ingest_file_path_traversal():
    result = mcp_server.ingest_file("/some/../path/file.pdf")
    assert result == {"error": "path traversal not allowed"}


def test_tool_descriptions_present():
    tools = {t.name: t for t in mcp_server.mcp._tool_manager.list_tools()}
    assert "discover" in tools
    assert "fetch" in tools
    assert "ingest_file" in tools
    assert tools["discover"].description
    assert tools["fetch"].description
    assert tools["ingest_file"].description
