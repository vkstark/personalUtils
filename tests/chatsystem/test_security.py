#!/usr/bin/env python3
"""
Security hardening tests for ToolExecutor: path sandboxing, SSRF URL filtering,
and the fixed (previously-broken) EnvManager parse action.

All hermetic — path/URL checks happen before any subprocess for the blocked
cases; the env-parse case runs the real EnvManager on a temp file.
"""

import subprocess
import types

import pytest

from ChatSystem.tools import tool_executor as te
from ChatSystem.tools.tool_executor import ToolExecutor
from ChatSystem.tools.tool_result import ToolStatus


def _fake_getaddrinfo(ip):
    """Return a getaddrinfo replacement that always resolves to `ip`."""
    def _inner(host, *args, **kwargs):
        return [(2, 1, 6, "", (ip, 0))]
    return _inner


def _capturing_run(recorder, stdout="{}", returncode=0):
    """subprocess.run replacement that records the argv/env and returns a stub."""
    def _inner(cmd, *args, **kwargs):
        recorder["cmd"] = cmd
        recorder["env"] = kwargs.get("env")
        return types.SimpleNamespace(stdout=stdout, stderr="", returncode=returncode)
    return _inner


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

    def test_hostname_resolving_to_private_ip_rejected(self, monkeypatch):
        # DNS-rebinding shape: a benign-looking host that resolves to a private IP.
        monkeypatch.setattr(te.socket, "getaddrinfo", _fake_getaddrinfo("10.1.2.3"))
        err = ToolExecutor()._check_url("http://benign.example/")
        assert err is not None and "private" in err.lower()

    def test_hostname_resolving_to_public_ip_allowed(self, monkeypatch):
        monkeypatch.setattr(te.socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34"))
        assert ToolExecutor()._check_url("http://example.com/") is None

    def test_allow_list_permits_otherwise_checked_host(self, monkeypatch):
        # Even if it would resolve to a private IP, an allow-listed host passes.
        monkeypatch.setattr(te.socket, "getaddrinfo", _fake_getaddrinfo("10.0.0.9"))
        ex = ToolExecutor(allowed_url_hosts=["internal.example"])
        assert ex._check_url("http://internal.example/health") is None


class TestSecretFileGuard:
    def test_env_file_blocked_for_generic_tool(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=sk-secret\n")
        result = ToolExecutor(sandbox_root=str(tmp_path)).execute(
            "compare_files", {"file1": str(env_file), "file2": str(env_file)}
        )
        assert result.status == ToolStatus.ERROR
        assert "secret file" in (result.error_message or "")

    def test_pem_file_blocked(self, tmp_path):
        key = tmp_path / "server.pem"
        key.write_text("-----BEGIN PRIVATE KEY-----\n")
        result = ToolExecutor(sandbox_root=str(tmp_path)).execute(
            "extract_todos", {"path": str(key)}
        )
        assert result.status == ToolStatus.ERROR
        assert "secret file" in (result.error_message or "")

    def test_env_manager_may_read_env(self, tmp_path):
        # The one exception: manage_env_files reads .env on purpose (redacted).
        env_file = tmp_path / ".env"
        env_file.write_text("A=b\n")
        result = ToolExecutor(sandbox_root=str(tmp_path)).execute(
            "manage_env_files", {"action": "parse", "file_path": str(env_file)}
        )
        assert result.status == ToolStatus.SUCCESS

    def test_dash_leading_path_rejected(self, tmp_path):
        result = ToolExecutor(sandbox_root=str(tmp_path)).execute(
            "analyze_python_code", {"path": "--evil-flag"}
        )
        assert result.status == ToolStatus.ERROR
        assert result.error_type == "SecurityError"


class TestSandboxEdgeCases:
    def test_relative_traversal_escapes_root(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        ex = ToolExecutor(sandbox_root=str(sub))
        escape = str(sub / ".." / ".." / "etc" / "hosts")
        result = ex.execute("analyze_python_code", {"path": escape})
        assert result.status == ToolStatus.ERROR
        assert result.error_type == "SecurityError"

    def test_symlink_out_of_root_rejected(self, tmp_path):
        link = tmp_path / "link_to_etc"
        try:
            link.symlink_to("/etc")
        except (OSError, NotImplementedError):
            pytest.skip("symlinks unavailable")
        ex = ToolExecutor(sandbox_root=str(tmp_path))
        result = ex.execute("analyze_python_code", {"path": str(link / "hosts")})
        assert result.status == ToolStatus.ERROR
        assert result.error_type == "SecurityError"

    def test_malformed_path_is_rejected(self, tmp_path):
        ex = ToolExecutor(sandbox_root=str(tmp_path))
        result = ex.execute("analyze_python_code", {"path": "bad\x00path"})
        assert result.status == ToolStatus.ERROR
        assert result.error_type == "SecurityError"


class TestArgvTranslation:
    def test_env_parse_translation(self, tmp_path, monkeypatch):
        rec = {}
        monkeypatch.setattr(te.subprocess, "run", _capturing_run(rec))
        env_file = tmp_path / ".env"
        env_file.write_text("A=b\n")
        ToolExecutor().execute(
            "manage_env_files", {"action": "parse", "file_path": str(env_file)}
        )
        cmd = rec["cmd"]
        assert "list" in cmd and "--hide-values" in cmd and "--no-color" in cmd

    def test_compare_files_uses_mode_flag(self, tmp_path, monkeypatch):
        rec = {}
        monkeypatch.setattr(te.subprocess, "run", _capturing_run(rec))
        a, b = tmp_path / "a.txt", tmp_path / "b.txt"
        a.write_text("x")
        b.write_text("y")
        ToolExecutor().execute(
            "compare_files", {"file1": str(a), "file2": str(b), "format": "unified"}
        )
        cmd = rec["cmd"]
        assert "--mode" in cmd and "unified" in cmd

    def test_convert_translation_flag_names(self, tmp_path, monkeypatch):
        rec = {}
        monkeypatch.setattr(te.subprocess, "run", _capturing_run(rec))
        src = tmp_path / "in.json"
        src.write_text("{}")
        ToolExecutor().execute("convert_data_format", {
            "input_file": str(src), "output_file": str(tmp_path / "out.yaml"),
            "from_format": "json", "to_format": "yaml",
        })
        cmd = rec["cmd"]
        assert "--input-format" in cmd and "--output-format" in cmd

    def test_subprocess_env_is_scrubbed_of_secrets(self, tmp_path, monkeypatch):
        rec = {}
        monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-leak")
        monkeypatch.setattr(te.subprocess, "run", _capturing_run(rec))
        src = tmp_path / "x.py"
        src.write_text("x = 1\n")
        ToolExecutor().execute("analyze_python_code", {"path": str(src)})
        assert rec["env"] is not None
        assert "OPENAI_API_KEY" not in rec["env"]


class TestFailClosed:
    def test_timeout_maps_to_timeout_status(self, tmp_path, monkeypatch):
        def _raise_timeout(cmd, *a, **k):
            raise subprocess.TimeoutExpired(cmd, k.get("timeout", 1))
        monkeypatch.setattr(te.subprocess, "run", _raise_timeout)
        src = tmp_path / "x.py"
        src.write_text("x = 1\n")
        result = ToolExecutor().execute("analyze_python_code", {"path": str(src)})
        assert result.status == ToolStatus.TIMEOUT
        assert result.error_type == "TimeoutError"

    def test_stdout_is_capped(self, tmp_path, monkeypatch):
        big = "A" * (te._MAX_OUTPUT_CHARS + 5000)
        rec = {}
        monkeypatch.setattr(te.subprocess, "run", _capturing_run(rec, stdout=big))
        src = tmp_path / "x.py"
        src.write_text("x = 1\n")
        result = ToolExecutor().execute("analyze_python_code", {"path": str(src)})
        assert len(result.stdout) <= te._MAX_OUTPUT_CHARS + 100
        assert "truncated" in result.stdout


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
