#!/usr/bin/env python3
"""
Unit tests for ToolExecutionResult

Tests serialization, legacy conversion, and edge cases.
"""

import pytest
from datetime import datetime
from ChatSystem.tools.tool_result import ToolExecutionResult, ToolStatus


class TestToolExecutionResult:
    """Test ToolExecutionResult model"""

    def test_success_result(self):
        """Test successful result creation"""
        result = ToolExecutionResult(
            status=ToolStatus.SUCCESS,
            stdout="Output text",
            duration=0.5,
            tool_name="test_tool"
        )

        assert result.is_success() is True
        assert result.is_error() is False
        assert result.is_timeout() is False
        assert result.requires_manual_action() is False

    def test_error_result(self):
        """Test error result creation"""
        result = ToolExecutionResult(
            status=ToolStatus.ERROR,
            error_message="Something went wrong",
            error_type="ValueError",
            duration=0.1,
            tool_name="test_tool"
        )

        assert result.is_success() is False
        assert result.is_error() is True
        assert result.error_message == "Something went wrong"
        assert result.error_type == "ValueError"

    def test_timeout_result(self):
        """Test timeout result"""
        result = ToolExecutionResult(
            status=ToolStatus.TIMEOUT,
            duration=60.0,
            tool_name="test_tool",
            error_message="Command timed out"
        )

        assert result.is_timeout() is True
        assert result.duration == 60.0

    def test_manual_required_result(self):
        """Test manual_required result"""
        result = ToolExecutionResult(
            status=ToolStatus.MANUAL_REQUIRED,
            stdout="BulkRename requires interactive confirmation",
            structured_payload={
                "message": "Please use CLI directly",
                "path": "/some/path"
            },
            duration=0.01,
            tool_name="bulk_rename_files",
            has_side_effects=True
        )

        assert result.requires_manual_action() is True
        assert result.has_side_effects is True

    def test_legacy_dict_success(self):
        """Test legacy dict conversion for success"""
        result = ToolExecutionResult(
            status=ToolStatus.SUCCESS,
            stdout="Success output",
            duration=0.2,
            tool_name="test_tool"
        )

        legacy = result.to_legacy_dict()

        assert legacy["success"] is True
        assert "result" in legacy
        assert legacy["result"] == "Success output"

    def test_legacy_dict_error(self):
        """Test legacy dict conversion for error"""
        result = ToolExecutionResult(
            status=ToolStatus.ERROR,
            error_message="File not found",
            stderr="Error: /path does not exist",
            duration=0.1,
            tool_name="test_tool"
        )

        legacy = result.to_legacy_dict()

        assert legacy["success"] is False
        assert legacy["error"] == "File not found"

    def test_legacy_dict_manual_required_preserves_message(self):
        """
        P1 Bug Fix Test: Ensure MANUAL_REQUIRED preserves stdout message.

        This was the critical bug - manual tools were showing "Unknown error"
        instead of the actual instruction message.
        """
        result = ToolExecutionResult(
            status=ToolStatus.MANUAL_REQUIRED,
            stdout="BulkRename requires interactive confirmation. Please use the CLI directly.",
            structured_payload={
                "message": "Interactive confirmation needed",
                "path": "/some/path"
            },
            duration=0.01,
            tool_name="bulk_rename_files"
        )

        legacy = result.to_legacy_dict()

        # Should NOT be "Unknown error"
        assert legacy["success"] is False
        assert legacy["error"] == "BulkRename requires interactive confirmation. Please use the CLI directly."
        assert legacy["status"] == "manual_required"
        assert legacy["requires_manual_action"] is True

    def test_legacy_dict_manual_required_from_structured_payload(self):
        """Test MANUAL_REQUIRED fallback to structured_payload if no stdout"""
        result = ToolExecutionResult(
            status=ToolStatus.MANUAL_REQUIRED,
            structured_payload={
                "message": "Manual action needed"
            },
            duration=0.01,
            tool_name="test_tool"
        )

        legacy = result.to_legacy_dict()

        assert legacy["error"] == "Manual action needed"
        assert legacy["requires_manual_action"] is True

    def test_legacy_dict_manual_required_fallback(self):
        """Test MANUAL_REQUIRED with no stdout or structured_payload"""
        result = ToolExecutionResult(
            status=ToolStatus.MANUAL_REQUIRED,
            duration=0.01,
            tool_name="test_tool"
        )

        legacy = result.to_legacy_dict()

        assert legacy["error"] == "Manual intervention required"
        assert legacy["requires_manual_action"] is True

    def test_get_output_with_structured_payload(self):
        """Test get_output returns JSON when structured_payload exists"""
        import json

        payload = {"status": "ok", "count": 42}
        result = ToolExecutionResult(
            status=ToolStatus.SUCCESS,
            stdout="raw output",
            structured_payload=payload,
            duration=0.1,
            tool_name="test_tool"
        )

        output = result.get_output()
        parsed = json.loads(output)

        assert parsed == payload

    def test_get_output_without_structured_payload(self):
        """Test get_output returns stdout when no structured_payload"""
        result = ToolExecutionResult(
            status=ToolStatus.SUCCESS,
            stdout="plain text output",
            duration=0.1,
            tool_name="test_tool"
        )

        output = result.get_output()

        assert output == "plain text output"

    def test_get_summary(self):
        """Test get_summary produces correct format"""
        result = ToolExecutionResult(
            status=ToolStatus.SUCCESS,
            duration=0.523,
            tool_name="analyze_python_code"
        )

        summary = result.get_summary()

        assert summary == "analyze_python_code: SUCCESS (0.523s)"

    def test_serialization_to_dict(self):
        """Test model_dump() serialization"""
        result = ToolExecutionResult(
            status=ToolStatus.ERROR,
            stdout="output",
            stderr="error output",
            error_message="Test error",
            duration=0.5,
            tool_name="test_tool",
            exit_code=1
        )

        data = result.model_dump()

        assert data["status"] == "error"
        assert data["stdout"] == "output"
        assert data["stderr"] == "error output"
        assert data["error_message"] == "Test error"
        assert data["duration"] == 0.5
        assert data["tool_name"] == "test_tool"
        assert data["exit_code"] == 1

    def test_serialization_to_json(self):
        """Test model_dump_json() serialization"""
        import json

        result = ToolExecutionResult(
            status=ToolStatus.SUCCESS,
            duration=0.1,
            tool_name="test_tool"
        )

        json_str = result.model_dump_json()
        parsed = json.loads(json_str)

        assert isinstance(parsed, dict)
        assert parsed["status"] == "success"
        assert parsed["tool_name"] == "test_tool"

    def test_timestamp_is_set(self):
        """Test that timestamp is automatically set"""
        result = ToolExecutionResult(
            status=ToolStatus.SUCCESS,
            duration=0.1,
            tool_name="test_tool"
        )

        assert isinstance(result.timestamp, datetime)

    def test_structured_payload_json_parsing(self):
        """Test that structured_payload can hold JSON data"""
        payload = {
            "files": ["file1.py", "file2.py"],
            "total_lines": 100,
            "complexity": 5.2
        }

        result = ToolExecutionResult(
            status=ToolStatus.SUCCESS,
            structured_payload=payload,
            duration=0.1,
            tool_name="analyze_python_code"
        )

        assert result.structured_payload == payload
        assert result.structured_payload["total_lines"] == 100

    def test_has_side_effects_flag(self):
        """Test has_side_effects flag for tools that modify state"""
        result = ToolExecutionResult(
            status=ToolStatus.SUCCESS,
            duration=0.1,
            tool_name="convert_data_format",
            has_side_effects=True
        )

        assert result.has_side_effects is True

    def test_command_and_exit_code_tracking(self):
        """Test that command and exit_code are captured for debugging"""
        result = ToolExecutionResult(
            status=ToolStatus.ERROR,
            duration=0.1,
            tool_name="test_tool",
            command="python test.py --arg value",
            exit_code=2,
            error_message="Invalid argument"
        )

        assert result.command == "python test.py --arg value"
        assert result.exit_code == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
