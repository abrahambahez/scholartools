from unittest.mock import MagicMock, patch

import pytest

import scholartools.mcp_server as mcp_server


def _mock_result(**fields):
    m = MagicMock()
    m.model_dump.return_value = fields
    return m


@pytest.mark.integration
class TestMcpToolsIntegration:
    def test_discover_tool(self):
        with patch(
            "scholartools.mcp_server.st.discover_references",
            return_value=_mock_result(items=[], total=0),
        ):
            result = mcp_server.discover(
                "neural networks", sources=["semantic_scholar"], limit=5
            )
        assert isinstance(result, dict)

    def test_fetch_tool(self):
        with patch(
            "scholartools.mcp_server.st.fetch_reference",
            return_value=_mock_result(reference=None, source=None, error=None),
        ):
            result = mcp_server.fetch("10.1234/test.doi")
        assert isinstance(result, dict)

    def test_ingest_file_tool(self):
        with patch(
            "scholartools.mcp_server.st.extract_from_file",
            return_value=_mock_result(
                reference=None, method_used="pdf", confidence=0.9, error=None
            ),
        ):
            result = mcp_server.ingest_file("/tmp/paper.pdf")
        assert isinstance(result, dict)

    def test_staging_list_tool(self):
        with patch(
            "scholartools.mcp_server.st.list_staged",
            return_value=_mock_result(references=[], total=0),
        ):
            result = mcp_server.staging("list", page=1)
        assert isinstance(result, dict)

    def test_staging_delete_tool(self):
        with patch(
            "scholartools.mcp_server.st.delete_staged",
            return_value=_mock_result(citekey="smith2020", error=None),
        ):
            result = mcp_server.staging("delete", citekey="smith2020")
        assert isinstance(result, dict)

    def test_staging_merge_tool(self):
        with patch(
            "scholartools.mcp_server.st.merge",
            return_value=_mock_result(promoted=["smith2020"], skipped=[], errors={}),
        ):
            result = mcp_server.staging(
                "merge", omit=["jones2019"], allow_semantic=True
            )
        assert isinstance(result, dict)

    def test_library_list_tool(self):
        with patch(
            "scholartools.mcp_server.st.list_references",
            return_value=_mock_result(items=[], total=0),
        ):
            result = mcp_server.library("list", page=1)
        assert isinstance(result, dict)

    def test_library_filter_tool(self):
        with patch(
            "scholartools.mcp_server.st.filter_references",
            return_value=_mock_result(items=[], total=0),
        ):
            result = mcp_server.library(
                "filter",
                query="deep learning",
                author="LeCun",
                year=2015,
                ref_type="article",
                has_file=True,
                page=1,
            )
        assert isinstance(result, dict)

    def test_library_get_tool(self):
        with patch(
            "scholartools.mcp_server.st.get_reference",
            return_value=_mock_result(reference=None, error=None),
        ):
            result = mcp_server.library("get", citekey="lecun2015")
        assert isinstance(result, dict)

    def test_manage_reference_add_tool(self):
        with patch(
            "scholartools.mcp_server.st.add_reference",
            return_value=_mock_result(citekey="smith2020", error=None),
        ):
            result = mcp_server.manage_reference(
                "add",
                ref={"title": "Test Paper", "type": "article-journal"},
            )
        assert isinstance(result, dict)

    def test_manage_reference_update_tool(self):
        with patch(
            "scholartools.mcp_server.st.update_reference",
            return_value=_mock_result(citekey="smith2020", error=None),
        ):
            result = mcp_server.manage_reference(
                "update", citekey="smith2020", fields={"title": "Updated"}
            )
        assert isinstance(result, dict)

    def test_manage_reference_delete_tool(self):
        with patch(
            "scholartools.mcp_server.st.delete_reference",
            return_value=_mock_result(citekey="smith2020", error=None),
        ):
            result = mcp_server.manage_reference("delete", citekey="smith2020")
        assert isinstance(result, dict)

    def test_manage_reference_rename_tool(self):
        with patch(
            "scholartools.mcp_server.st.rename_reference",
            return_value=_mock_result(
                old_key="smith2020", new_key="smith2020a", error=None
            ),
        ):
            result = mcp_server.manage_reference(
                "rename", old_key="smith2020", new_key="smith2020a"
            )
        assert isinstance(result, dict)

    def test_files_link_tool(self):
        with patch(
            "scholartools.mcp_server.st.link_file",
            return_value=_mock_result(citekey="smith2020", error=None),
        ):
            result = mcp_server.files(
                "link", citekey="smith2020", file_path="/tmp/paper.pdf"
            )
        assert isinstance(result, dict)

    def test_files_unlink_tool(self):
        with patch(
            "scholartools.mcp_server.st.unlink_file",
            return_value=_mock_result(citekey="smith2020", error=None),
        ):
            result = mcp_server.files("unlink", citekey="smith2020")
        assert isinstance(result, dict)

    def test_files_move_tool(self):
        with patch(
            "scholartools.mcp_server.st.move_file",
            return_value=_mock_result(
                citekey="smith2020", dest="smith2020.pdf", error=None
            ),
        ):
            result = mcp_server.files(
                "move", citekey="smith2020", dest_name="smith2020.pdf"
            )
        assert isinstance(result, dict)

    def test_files_list_tool(self):
        with patch(
            "scholartools.mcp_server.st.list_files",
            return_value=_mock_result(items=[], total=0),
        ):
            result = mcp_server.files("list", page=1)
        assert isinstance(result, dict)


def test_mcp_module_importable_cleanly():
    import scholartools.mcp_server as m

    assert m.mcp is not None
    assert callable(m.main)
