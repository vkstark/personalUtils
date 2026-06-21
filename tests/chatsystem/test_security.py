#!/usr/bin/env python3
"""
Security hardening tests for ToolExecutor: path sandboxing, SSRF URL filtering,
and the fixed (previously-broken) EnvManager parse action.

All hermetic — path/URL checks happen before any subprocess for the blocked
cases; the env-parse case runs the real EnvManager on a temp file.
"""

import pytest

from ChatSystem.tools.tool_executor import ToolExecutor
from ChatSystem.tools.tool_result import ToolStatus


class TestPathSandbox:
    def test_path_outside_root_is_rejected(self, tmp_path):
        ex = ToolExecutor(sandbox_root=str(tmp_path))
        result = ex.execute("analyze_python_code", {"path": "/etc/hosts"})
        assert result.status == ToolStatus.ERROR
        assert result.error_type == "SecurityError"

    def test_path_inside_root_is_not_blocked(self, tmp_path):
        target = tmp_path / "ok.py"
        target.write_text("def f():\n    return 1\n")
        ex = ToolExecutor(sandbox_root=str(tmp_path))
        result = ex.execute("analyze_python_code", {"path": str(target)})
        assert result.error_type != "SecurityError"

    def test_no_sandbox_allows_any_path(self, tmp_path):
        target = tmp_path / "anywhere.py"
        target.write_text("x = 1\n")
        ex = ToolExecutor()  # sandbox_root=None -> no path checks
        result = ex.execute("analyze_python_code", {"path": str(target)})
        assert result.error_type != "SecurityError"

    def test_compare_files_second_path_checked(self, tmp_path):
        inside = tmp_path / "a.txt"
        inside.write_text("a")
        ex = ToolExecutor(sandbox_root=str(tmp_path))
        result = ex.execute("compare_files", {"file1": str(inside), "file2": "/etc/hosts"})
        assert result.status == ToolStatus.ERROR
        assert result.error_type == "SecurityError"


class TestSSRF:
    def test_non_http_scheme_rejected(self):
        result = ToolExecutor().execute(
            "test_api_endpoint", {"url": "file:///etc/passwd", "method": "GET"}
        )
        assert result.status == ToolStatus.ERROR
        assert result.error_type == "SecurityError"

    def test_loopback_rejected(self):
        result = ToolExecutor().execute(
            "test_api_endpoint", {"url": "http://127.0.0.1/", "method": "GET"}
        )
        assert result.status == ToolStatus.ERROR
        assert result.error_type == "SecurityError"

    def test_cloud_metadata_link_local_rejected(self):
        result = ToolExecutor().execute(
            "test_api_endpoint",
            {"url": "http://169.254.169.254/latest/meta-data/", "method": "GET"},
        )
        assert result.status == ToolStatus.ERROR
        assert result.error_type == "SecurityError"

    def test_private_rfc1918_rejected(self):
        result = ToolExecutor().execute(
            "test_api_endpoint", {"url": "http://10.0.0.5/admin", "method": "GET"}
        )
        assert result.status == ToolStatus.ERROR
        assert result.error_type == "SecurityError"


class TestEnvParseFixed:
    def test_env_parse_returns_success(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY1=value1\nKEY2=value2\n")
        result = ToolExecutor().execute(
            "manage_env_files", {"action": "parse", "file_path": str(env_file)}
        )
        assert result.status == ToolStatus.SUCCESS

    def test_env_parse_hides_secret_values(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=supersecretvalue\n")
        result = ToolExecutor().execute(
            "manage_env_files", {"action": "parse", "file_path": str(env_file)}
        )
        # --hide-values keeps the actual secret out of stdout (and history)
        assert "supersecretvalue" not in (result.stdout or "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
