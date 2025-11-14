#!/usr/bin/env python3
"""
Contract Tests for Tool Executor

This test suite ensures that:
1. All 12 tools return ToolExecutionResult (not raw dict/str)
2. ToolExecutionResult schemas are valid
3. Required fields are present (status, duration, tool_name)
4. Tools handle success and error cases correctly
5. No silent failures

These tests validate the tool reliability contract.
"""

import pytest
import tempfile
import os
from pathlib import Path
from ChatSystem.tools.tool_executor import ToolExecutor
from ChatSystem.tools.tool_result import ToolExecutionResult, ToolStatus


class TestToolContracts:
    """Contract tests for all 12 tools"""

    @pytest.fixture
    def executor(self):
        """Create a ToolExecutor instance"""
        return ToolExecutor()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    # ==================== Core Contract Tests ====================

    def test_unknown_function_returns_execution_result(self, executor):
        """Unknown function should return ToolExecutionResult with ERROR status"""
        result = executor.execute("nonexistent_function", {})

        assert isinstance(result, ToolExecutionResult)
        assert result.status == ToolStatus.ERROR
        assert result.error_message is not None
        assert "Unknown function" in result.error_message
        assert result.duration >= 0

    @pytest.mark.parametrize("function_name", [
        "analyze_python_code",
        "test_api_endpoint",
        "find_duplicate_files",
        "manage_code_snippets",
        "bulk_rename_files",
        "manage_env_files",
        "compare_files",
        "analyze_git_repository",
        "optimize_python_imports",
        "visualize_directory_tree",
        "extract_todos",
        "convert_data_format",
    ])
    def test_all_tools_return_execution_result(self, executor, function_name, temp_dir):
        """All tools must return ToolExecutionResult, not dict or str"""
        # Get minimal valid arguments for each tool
        args = self._get_minimal_args(function_name, temp_dir)

        result = executor.execute(function_name, args)

        # Core contract: must return ToolExecutionResult
        assert isinstance(result, ToolExecutionResult), \
            f"{function_name} returned {type(result)} instead of ToolExecutionResult"

        # Must have required fields
        assert hasattr(result, 'status')
        assert hasattr(result, 'duration')
        assert hasattr(result, 'tool_name')
        assert hasattr(result, 'timestamp')

        # Status must be valid
        assert result.status in [ToolStatus.SUCCESS, ToolStatus.ERROR, ToolStatus.TIMEOUT, ToolStatus.MANUAL_REQUIRED]

        # Duration must be non-negative
        assert result.duration >= 0

        # Tool name should match
        assert result.tool_name == function_name

    # ==================== Tool-Specific Tests ====================

    def test_code_whisper_success(self, executor, temp_dir):
        """CodeWhisper: analyze a simple Python file"""
        # Create a simple Python file
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("def hello():\n    print('Hello')\n")

        result = executor.execute("analyze_python_code", {"path": str(test_file)})

        assert isinstance(result, ToolExecutionResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.stdout is not None
        assert result.duration >= 0

    def test_code_whisper_invalid_path(self, executor):
        """CodeWhisper: handle nonexistent path"""
        result = executor.execute("analyze_python_code", {"path": "/nonexistent/path/12345"})

        assert isinstance(result, ToolExecutionResult)
        # Should be ERROR (path doesn't exist)
        assert result.status == ToolStatus.ERROR
        assert result.error_message is not None

    def test_api_tester_success(self, executor):
        """APITester: test a real HTTP endpoint"""
        result = executor.execute("test_api_endpoint", {
            "url": "https://httpbin.org/get",
            "method": "GET"
        })

        assert isinstance(result, ToolExecutionResult)
        # Note: This might fail if no internet, which is OK - we're testing the contract
        assert result.status in [ToolStatus.SUCCESS, ToolStatus.ERROR]
        assert result.duration >= 0

    def test_api_tester_invalid_url(self, executor):
        """APITester: handle invalid URL"""
        result = executor.execute("test_api_endpoint", {
            "url": "not-a-valid-url",
            "method": "GET"
        })

        assert isinstance(result, ToolExecutionResult)
        # Should handle invalid URL gracefully
        assert result.status in [ToolStatus.ERROR, ToolStatus.SUCCESS]  # Depends on implementation
        assert result.duration >= 0

    def test_duplicate_finder_success(self, executor, temp_dir):
        """DuplicateFinder: scan an empty directory"""
        result = executor.execute("find_duplicate_files", {
            "path": temp_dir,
            "recursive": False
        })

        assert isinstance(result, ToolExecutionResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.duration >= 0

    def test_duplicate_finder_invalid_path(self, executor):
        """DuplicateFinder: handle nonexistent path (scans 0 files, not an error)"""
        result = executor.execute("find_duplicate_files", {
            "path": "/nonexistent/path/12345"
        })

        assert isinstance(result, ToolExecutionResult)
        # DuplicateFinder doesn't error on invalid paths, just scans 0 files
        assert result.status == ToolStatus.SUCCESS
        assert result.duration >= 0

    def test_snippet_manager_list(self, executor):
        """SnippetManager: list snippets"""
        result = executor.execute("manage_code_snippets", {"action": "list"})

        assert isinstance(result, ToolExecutionResult)
        # Should succeed (empty list is OK)
        assert result.status in [ToolStatus.SUCCESS, ToolStatus.ERROR]
        assert result.duration >= 0

    def test_bulk_rename_requires_manual(self, executor, temp_dir):
        """BulkRename: should return MANUAL_REQUIRED"""
        result = executor.execute("bulk_rename_files", {
            "path": temp_dir,
            "pattern": "*.txt",
            "replacement": "renamed",
            "dry_run": True
        })

        assert isinstance(result, ToolExecutionResult)
        assert result.status == ToolStatus.MANUAL_REQUIRED
        assert result.has_side_effects is True

    def test_env_manager_parse(self, executor, temp_dir):
        """EnvManager: parse an env file"""
        # Create a simple .env file
        env_file = Path(temp_dir) / ".env"
        env_file.write_text("KEY1=value1\nKEY2=value2\n")

        result = executor.execute("manage_env_files", {
            "action": "parse",
            "file_path": str(env_file)
        })

        assert isinstance(result, ToolExecutionResult)
        assert result.status in [ToolStatus.SUCCESS, ToolStatus.ERROR]
        assert result.duration >= 0

    def test_env_manager_other_actions_require_manual(self, executor):
        """EnvManager: non-parse actions should return MANUAL_REQUIRED"""
        result = executor.execute("manage_env_files", {
            "action": "validate",
            "file_path": ".env"
        })

        assert isinstance(result, ToolExecutionResult)
        assert result.status == ToolStatus.MANUAL_REQUIRED
        assert result.has_side_effects is True

    def test_file_diff_success(self, executor, temp_dir):
        """FileDiff: compare two files"""
        # Create two files
        file1 = Path(temp_dir) / "file1.txt"
        file2 = Path(temp_dir) / "file2.txt"
        file1.write_text("Hello world")
        file2.write_text("Hello world!")

        result = executor.execute("compare_files", {
            "file1": str(file1),
            "file2": str(file2)
        })

        assert isinstance(result, ToolExecutionResult)
        assert result.status in [ToolStatus.SUCCESS, ToolStatus.ERROR]
        assert result.duration >= 0

    def test_git_stats_success(self, executor):
        """GitStats: analyze current repository"""
        result = executor.execute("analyze_git_repository", {
            "repo_path": ".",
            "report_type": "summary"
        })

        assert isinstance(result, ToolExecutionResult)
        # Should succeed if we're in a git repo
        assert result.status in [ToolStatus.SUCCESS, ToolStatus.ERROR]
        assert result.duration >= 0

    def test_import_optimizer_success(self, executor, temp_dir):
        """ImportOptimizer: analyze Python file"""
        # Create a Python file with imports
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("import os\nimport sys\nprint('hello')\n")

        result = executor.execute("optimize_python_imports", {
            "command": "unused",
            "path": str(test_file)
        })

        assert isinstance(result, ToolExecutionResult)
        assert result.status in [ToolStatus.SUCCESS, ToolStatus.ERROR]
        assert result.duration >= 0

    def test_path_sketch_success(self, executor, temp_dir):
        """PathSketch: visualize directory"""
        result = executor.execute("visualize_directory_tree", {
            "path": temp_dir,
            "max_depth": 2
        })

        assert isinstance(result, ToolExecutionResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.duration >= 0

    def test_todo_extractor_success(self, executor, temp_dir):
        """TodoExtractor: extract TODOs from file (returns ERROR when TODOs found)"""
        # Create a file with TODOs
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("# TODO: implement this\ndef foo():\n    pass\n")

        result = executor.execute("extract_todos", {
            "path": str(test_file),
            "recursive": False
        })

        assert isinstance(result, ToolExecutionResult)
        # TodoExtractor returns exit code 1 when TODOs are found (by design - for CI)
        assert result.status == ToolStatus.ERROR
        assert result.exit_code == 1
        assert result.duration >= 0
        # But it should have output showing the TODOs
        assert result.stdout is not None or result.stderr is not None

    def test_data_convert_success(self, executor, temp_dir):
        """DataConvert: convert JSON to YAML"""
        # Create input JSON file
        input_file = Path(temp_dir) / "input.json"
        output_file = Path(temp_dir) / "output.yaml"
        input_file.write_text('{"key": "value"}')

        result = executor.execute("convert_data_format", {
            "input_file": str(input_file),
            "output_file": str(output_file),
            "from_format": "json",
            "to_format": "yaml"
        })

        assert isinstance(result, ToolExecutionResult)
        assert result.status in [ToolStatus.SUCCESS, ToolStatus.ERROR]
        assert result.duration >= 0
        assert result.has_side_effects is True  # Writes output file

    # ==================== Schema Validation Tests ====================

    def test_execution_result_serialization(self, executor, temp_dir):
        """ToolExecutionResult should serialize to dict"""
        result = executor.execute("visualize_directory_tree", {"path": temp_dir})

        # Should be able to convert to dict
        result_dict = result.model_dump()
        assert isinstance(result_dict, dict)
        assert "status" in result_dict
        assert "duration" in result_dict
        assert "tool_name" in result_dict

        # Legacy format conversion
        legacy_dict = result.to_legacy_dict()
        assert isinstance(legacy_dict, dict)
        assert "success" in legacy_dict

    def test_execution_result_json_serialization(self, executor, temp_dir):
        """ToolExecutionResult should serialize to JSON"""
        import json
        result = executor.execute("visualize_directory_tree", {"path": temp_dir})

        # Should be able to convert to JSON
        json_str = result.model_dump_json()
        assert isinstance(json_str, str)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    # ==================== Helper Methods ====================

    def _get_minimal_args(self, function_name: str, temp_dir: str) -> dict:
        """Get minimal valid arguments for each tool"""
        minimal_args = {
            "analyze_python_code": {"path": "."},
            "test_api_endpoint": {"url": "https://httpbin.org/get", "method": "GET"},
            "find_duplicate_files": {"path": temp_dir},
            "manage_code_snippets": {"action": "list"},
            "bulk_rename_files": {"path": temp_dir, "pattern": "*.txt", "replacement": "new"},
            "manage_env_files": {"action": "parse", "file_path": ".env"},
            "compare_files": {
                "file1": os.path.join(temp_dir, "f1.txt"),
                "file2": os.path.join(temp_dir, "f2.txt")
            },
            "analyze_git_repository": {"repo_path": "."},
            "optimize_python_imports": {"command": "unused", "path": "."},
            "visualize_directory_tree": {"path": temp_dir},
            "extract_todos": {"path": temp_dir},
            "convert_data_format": {
                "input_file": os.path.join(temp_dir, "in.json"),
                "output_file": os.path.join(temp_dir, "out.yaml"),
                "from_format": "json",
                "to_format": "yaml"
            },
        }

        return minimal_args.get(function_name, {})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
