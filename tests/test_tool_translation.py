#!/usr/bin/env python3
"""
Executor-Level Regression Tests for the Argument-Translation Layer

Each test pins a verified defect from the 2026-08-04 review of
tool_executor.py's hand-maintained CLI translation: misplaced top-level
flags, schema/CLI value mismatches, lost schema defaults, exit-code
conventions misreported as failures, and the SnippetManager delete
confirmation hang.
"""

import os
import pytest

from ChatSystem.tools import tool_executor as tool_executor_module
from ChatSystem.tools.tool_executor import ToolExecutor
from ChatSystem.tools.tool_result import ToolStatus


class TestTranslationRegressions:
    """Regression tests for tool_executor argument translation"""

    @pytest.fixture
    def executor(self):
        """Create a ToolExecutor instance"""
        return ToolExecutor()

    def test_import_optimizer_no_color_precedes_subcommand(self, executor, tmp_path):
        """2a: --no-color is a top-level flag; placing it after the subcommand exits 2"""
        test_file = tmp_path / "unused.py"
        test_file.write_text("import os\nprint('hi')\n")

        result = executor.execute("optimize_python_imports", {
            "command": "unused",
            "path": str(test_file)
        })

        assert result.status == ToolStatus.SUCCESS
        assert "unrecognized arguments" not in (result.stderr or "")
        assert "os" in result.stdout  # the unused import is reported

    def test_snippet_manager_list_no_color_precedes_subcommand(self, executor, tmp_path, monkeypatch):
        """2a: SnippetManager also registers --no-color on the top-level parser"""
        monkeypatch.setenv("HOME", str(tmp_path))

        result = executor.execute("manage_code_snippets", {"action": "list"})

        assert result.status == ToolStatus.SUCCESS
        assert "unrecognized arguments" not in (result.stderr or "")

    def test_file_diff_side_by_side_format_translated(self, executor, tmp_path):
        """2b: schema advertises 'side-by-side'; FileDiff's --mode wants 'side_by_side'"""
        file1 = tmp_path / "f1.txt"
        file2 = tmp_path / "f2.txt"
        file1.write_text("same\n")
        file2.write_text("same\n")

        result = executor.execute("compare_files", {
            "file1": str(file1),
            "file2": str(file2),
            "format": "side-by-side"
        })

        assert result.status == ToolStatus.SUCCESS
        assert "invalid choice" not in (result.stderr or "")

    def test_duplicate_finder_recursive_defaults_true(self, executor, tmp_path):
        """2c: schema declares recursive default true; omitting it must still recurse"""
        (tmp_path / "sub").mkdir()
        (tmp_path / "a.txt").write_text("same-bytes\n")
        (tmp_path / "sub" / "b.txt").write_text("same-bytes\n")

        result = executor.execute("find_duplicate_files", {"path": str(tmp_path)})

        assert result.status == ToolStatus.SUCCESS
        # The duplicate lives in a subdirectory - only a recursive scan finds it
        assert "Found 1 set(s) of duplicates" in result.stdout

    def test_extract_todos_found_is_success(self, executor, tmp_path):
        """2d: exit code 1 means TODOs found (CI convention), not tool failure"""
        test_file = tmp_path / "todo.py"
        test_file.write_text("# TODO: implement this\n")

        result = executor.execute("extract_todos", {
            "path": str(test_file),
            "recursive": False
        })

        assert result.status == ToolStatus.SUCCESS
        assert result.exit_code == 1
        assert "TODO" in result.stdout

    def test_compare_files_differing_is_success(self, executor, tmp_path):
        """2d: exit code 1 means files differ (CI convention), not tool failure"""
        file1 = tmp_path / "f1.txt"
        file2 = tmp_path / "f2.txt"
        file1.write_text("one\n")
        file2.write_text("two\n")

        result = executor.execute("compare_files", {
            "file1": str(file1),
            "file2": str(file2)
        })

        assert result.status == ToolStatus.SUCCESS
        assert result.exit_code == 1

    def test_snippet_show_passes_id_not_title(self, executor, tmp_path, monkeypatch):
        """2e: show addresses snippets by ID; the executor must pass args['id']"""
        monkeypatch.setenv("HOME", str(tmp_path))

        result = executor.execute("manage_code_snippets", {
            "action": "show",
            "id": "xyz123"
        })

        # The snippet doesn't exist, but the ID must reach the CLI intact
        assert "xyz123" in ((result.stdout or "") + (result.stderr or ""))

    def test_snippet_delete_is_manual_and_spawns_nothing(self, executor, monkeypatch):
        """2f: delete needs interactive confirmation - MANUAL_REQUIRED, no subprocess"""
        def _no_subprocess(*args, **kwargs):
            raise AssertionError("delete must not spawn a subprocess")
        monkeypatch.setattr(tool_executor_module.subprocess, "run", _no_subprocess)

        result = executor.execute("manage_code_snippets", {
            "action": "delete",
            "id": "abc123"
        })

        assert result.status == ToolStatus.MANUAL_REQUIRED
        assert result.has_side_effects is True
        payload = result.structured_payload or {}
        assert payload.get("snippet_id") == "abc123"
        assert "python tools/SnippetManager/snippet_manager.py delete abc123" in payload.get("command", "")

    def test_compare_with_is_sandboxed_path_key(self):
        """2g: compare_with is a path-typed arg and must be sandbox-checked"""
        assert "compare_with" in ToolExecutor._PATH_ARG_KEYS

    def test_code_whisper_skips_dangling_symlink(self, executor, tmp_path):
        """2h: one broken symlink must not abort the whole directory scan"""
        good = tmp_path / "good.py"
        good.write_text("def hello():\n    return 1\n")
        os.symlink(tmp_path / "missing.py", tmp_path / "dangling.py")

        result = executor.execute("analyze_python_code", {"path": str(tmp_path)})

        assert result.status == ToolStatus.SUCCESS
        assert "hello" in result.stdout  # the valid file was analyzed
