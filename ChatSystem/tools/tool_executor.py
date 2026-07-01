#!/usr/bin/env python3
"""
ToolExecutor - Safely execute utility tools

Version 2.0: Returns structured ToolExecutionResult for all executions
"""

import os
import sys
import json
import socket
import ipaddress
import subprocess
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from urllib.parse import urlparse

from .tool_result import ToolExecutionResult, ToolStatus

# Cap captured subprocess stdout so a single tool call can't exhaust memory,
# balloon the persisted 0600 history, or blow up OpenAI token spend.
_MAX_OUTPUT_CHARS = 512 * 1024

# Environment variable name-fragments to strip from the child process env
# (least privilege: none of the utilities need the parent's credentials).
_SENSITIVE_ENV_FRAGMENTS = ("API_KEY", "SECRET", "TOKEN", "PASSWORD", "PASSWD")

# Secret files no tool should surface to the model. manage_env_files is the one
# exception: it reads .env deliberately and redacts values with --hide-values.
_SECRET_FILE_NAMES = {"id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", ".netrc", ".pgpass"}
_SECRET_FILE_SUFFIXES = (".pem", ".key", ".p12", ".pfx")


def _is_blocked_ip(ip_str: str) -> bool:
    """True if the IP is loopback/link-local/private/reserved (SSRF targets)."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return (
        ip.is_loopback or ip.is_link_local or ip.is_private
        or ip.is_reserved or ip.is_multicast or ip.is_unspecified
    )


def _is_secret_file(resolved: Path) -> bool:
    """True if the path names a credentials/secrets file (.env, keys, etc.)."""
    name = resolved.name
    if name == ".env" or name.startswith(".env."):
        return True
    if name in _SECRET_FILE_NAMES:
        return True
    if resolved.suffix in _SECRET_FILE_SUFFIXES:
        return True
    return False


def _child_env() -> Dict[str, str]:
    """A copy of the environment with the parent's secrets removed."""
    return {
        k: v for k, v in os.environ.items()
        if not any(frag in k.upper() for frag in _SENSITIVE_ENV_FRAGMENTS)
    }


class ToolExecutor:
    """
    Safely executes utility tools by running them as separate subprocesses.

    This class provides a secure way to execute the various command-line
    utility tools available in the project. It maps the function names from the
    OpenAI API to the corresponding Python scripts and translates the arguments
    into command-line flags.

    Attributes:
        utils_dir (Path): The base directory where the utility tools are located.
        function_to_util (Dict[str, str]): A mapping from the OpenAI function
            name to the relative path of the utility script.
    """

    def __init__(
        self,
        utils_dir: Optional[str] = None,
        timeout: int = 60,
        sandbox_root: Optional[str] = None,
        allowed_url_hosts: Optional[List[str]] = None,
    ):
        """
        Initializes the ToolExecutor.

        Args:
            utils_dir (Optional[str], optional): The directory containing the
                utility tools. If not provided, it is inferred from the location
                of this file. Defaults to None.
            timeout (int, optional): Per-tool subprocess timeout in seconds.
                Defaults to 60.
            sandbox_root (Optional[str], optional): If set, every path-typed tool
                argument must resolve within this directory; out-of-root paths are
                rejected (defends against arbitrary file read / exfiltration). If
                None, no path sandboxing is applied. Defaults to None.
            allowed_url_hosts (Optional[List[str]], optional): Hostnames that are
                always permitted for the API-tester tool even if they resolve to a
                private address. Non-http(s) schemes and private/loopback/link-local
                destinations are otherwise blocked (SSRF defense). Defaults to None.
        """
        # Get utilities directory
        if utils_dir:
            self.utils_dir = Path(utils_dir)
        else:
            # Assume we're in ChatSystem, go up one level
            self.utils_dir = Path(__file__).parent.parent.parent

        self.timeout = timeout
        self.sandbox_root = Path(sandbox_root).resolve() if sandbox_root else None
        self.allowed_url_hosts = set(allowed_url_hosts or [])

        # Map function names to utility modules
        self.function_to_util = {
            "analyze_python_code": "tools/CodeWhisper/code_whisper.py",
            "test_api_endpoint": "tools/APITester/api_tester.py",
            "find_duplicate_files": "tools/DuplicateFinder/duplicate_finder.py",
            "manage_code_snippets": "tools/SnippetManager/snippet_manager.py",
            "bulk_rename_files": "tools/BulkRename/bulk_rename.py",
            "manage_env_files": "tools/EnvManager/env_manager.py",
            "compare_files": "tools/FileDiff/file_diff.py",
            "analyze_git_repository": "tools/GitStats/git_stats.py",
            "optimize_python_imports": "tools/ImportOptimizer/import_optimizer.py",
            "visualize_directory_tree": "tools/PathSketch/path_sketch.py",
            "extract_todos": "tools/TodoExtractor/todo_extractor.py",
            "convert_data_format": "tools/DataConvert/data_convert.py",
        }

    # Argument keys that are filesystem paths (validated against the sandbox root)
    _PATH_ARG_KEYS = ("path", "file1", "file2", "file_path", "input_file", "output_file", "repo_path")

    def _check_path(self, value: str) -> Optional[str]:
        """Return an error message if `value` is outside the sandbox root, else None."""
        if self.sandbox_root is None or not value:
            return None
        try:
            resolved = Path(value).resolve()
        except (OSError, ValueError):
            return f"Invalid path: {value}"
        if resolved == self.sandbox_root or resolved.is_relative_to(self.sandbox_root):
            return None
        return f"Path '{value}' is outside the allowed root ({self.sandbox_root})"

    def _check_url(self, url: Optional[str]) -> Optional[str]:
        """Return an error message if `url` is an unsafe SSRF target, else None."""
        parsed = urlparse(url or "")
        if parsed.scheme not in ("http", "https"):
            return f"Only http/https URLs are allowed (got scheme '{parsed.scheme or 'none'}')"
        host = parsed.hostname or ""
        if host in self.allowed_url_hosts:
            return None
        # Block literal private IPs and hostnames that resolve to them
        if _is_blocked_ip(host):
            return f"Refusing to call internal/private address: {host}"
        try:
            resolved_ips = {str(info[4][0]) for info in socket.getaddrinfo(host, None)}
        except (socket.gaierror, OSError):
            return None  # let the subprocess surface DNS failures
        for ip in resolved_ips:
            if _is_blocked_ip(ip):
                return f"Refusing to call host '{host}' which resolves to a private/internal address ({ip})"
        return None

    def _validate_arguments(self, function_name: str, args: Dict[str, Any]) -> Optional[str]:
        """Run security checks on path and URL arguments. Returns an error or None."""
        for key in self._PATH_ARG_KEYS:
            value = args.get(key)
            if isinstance(value, str):
                # A path that begins with '-' would be parsed as a flag by the
                # child tool's argparse (argument injection); it is never a path
                # a caller legitimately means.
                if value.startswith("-"):
                    return f"Path argument '{key}' may not start with '-': {value!r}"
                err = self._check_path(value)
                if err:
                    return err
                # Don't let generic tools exfiltrate secret files. manage_env_files
                # is exempt: it reads .env on purpose and redacts values.
                if function_name != "manage_env_files":
                    try:
                        resolved = Path(value).resolve()
                    except (OSError, ValueError):
                        resolved = None
                    if resolved is not None and _is_secret_file(resolved):
                        return f"Refusing to expose secret file '{value}' via {function_name}"
        if function_name == "test_api_endpoint":
            return self._check_url(args.get("url"))
        return None

    def execute(self, function_name: str, arguments: Dict[str, Any]) -> ToolExecutionResult:
        """
        Executes a specified tool with the given arguments.

        This method finds the corresponding script for the `function_name`,
        constructs the command-line arguments, and runs the script in a
        separate process.

        Args:
            function_name (str): The name of the function to execute.
            arguments (Dict[str, Any]): A dictionary of arguments for the function.

        Returns:
            ToolExecutionResult: The structured result of the execution. Use
            `to_legacy_dict()` for the legacy success/result/error dict shape.
        """

        start_time = time.time()

        # Check if function exists
        if function_name not in self.function_to_util:
            return ToolExecutionResult(
                status=ToolStatus.ERROR,
                tool_name=function_name,
                duration=time.time() - start_time,
                error_message=f"Unknown function: {function_name}",
                error_type="UnknownFunctionError"
            )

        # Security checks (path sandbox + SSRF) before doing any work
        security_error = self._validate_arguments(function_name, arguments)
        if security_error:
            return ToolExecutionResult(
                status=ToolStatus.ERROR,
                tool_name=function_name,
                duration=time.time() - start_time,
                error_message=security_error,
                error_type="SecurityError",
            )

        try:
            # Get utility script path
            util_script = self.utils_dir / self.function_to_util[function_name]

            if not util_script.exists():
                return ToolExecutionResult(
                    status=ToolStatus.ERROR,
                    tool_name=function_name,
                    duration=time.time() - start_time,
                    error_message=f"Utility script not found: {util_script}",
                    error_type="FileNotFoundError"
                )

            # Build command and execute
            result = self._execute_utility(function_name, util_script, arguments, start_time)
            return result

        except Exception as e:
            return ToolExecutionResult(
                status=ToolStatus.ERROR,
                tool_name=function_name,
                duration=time.time() - start_time,
                error_message=str(e),
                error_type=type(e).__name__
            )

    def _execute_utility(
        self, function_name: str, script_path: Path, args: Dict[str, Any], start_time: float
    ) -> ToolExecutionResult:
        """
        Constructs and executes the command-line instruction for a specific utility.

        This private method is responsible for translating the structured
        arguments from the AI into a list of command-line flags and arguments
        that can be passed to `subprocess.run`.

        Args:
            function_name (str): The name of the function being executed.
            script_path (Path): The path to the Python script for the utility.
            args (Dict[str, Any]): The arguments for the utility.
            start_time (float): The timestamp when execution started, used to calculate duration.

        Returns:
            ToolExecutionResult: A structured result object containing execution status,
            output, error information, and metadata.
        """

        # Build command line arguments based on function
        # Note: Using list-based arguments with shell=False is secure against injection
        cmd = [sys.executable, str(script_path)]

        if function_name == "analyze_python_code":
            cmd.append(args.get("path", "."))
            if args.get("detailed"):
                cmd.append("--detailed")
            if args.get("format"):
                cmd.extend(["--format", args["format"]])
            cmd.append("--no-color")

        elif function_name == "test_api_endpoint":
            cmd.append(args.get("method", "GET"))
            cmd.append(args["url"])
            if args.get("headers"):
                for key, value in args["headers"].items():
                    cmd.extend(["-H", f"{key}: {value}"])
            if args.get("data"):
                cmd.extend(["-d", args["data"]])
            cmd.append("--no-color")

        elif function_name == "find_duplicate_files":
            cmd.append(args["path"])
            if args.get("recursive"):
                cmd.append("--recursive")
            if not args.get("by_hash", True):
                cmd.append("--by-name")
            if args.get("extensions"):
                cmd.extend(["--extensions"] + args["extensions"])
            cmd.append("--no-color")

        elif function_name == "manage_code_snippets":
            action = args["action"]
            cmd.append(action)

            if action == "add":
                cmd.extend(["-t", args["title"]])
                cmd.extend(["-l", args["language"]])
                cmd.extend(["-c", args["code"]])
                if args.get("tags"):
                    cmd.extend(["--tags"] + args["tags"])

            elif action in ["show", "delete"]:
                cmd.append(args.get("title", ""))

            elif action == "search":
                if args.get("query"):
                    cmd.append(args["query"])
                if args.get("language"):
                    cmd.extend(["-l", args["language"]])
                if args.get("tags"):
                    cmd.extend(["--tags"] + args["tags"])

            cmd.append("--no-color")

        elif function_name == "bulk_rename_files":
            # This is complex - requires manual confirmation
            message = "BulkRename requires interactive confirmation. Please use the CLI directly."
            return ToolExecutionResult(
                status=ToolStatus.MANUAL_REQUIRED,
                tool_name=function_name,
                duration=time.time() - start_time,
                stdout=message,
                structured_payload={
                    "message": message,
                    "path": args.get("path"),
                    "pattern": args.get("pattern"),
                    "replacement": args.get("replacement"),
                    "mode": args.get("mode"),
                    "dry_run": args.get("dry_run", True)
                },
                has_side_effects=True
            )

        elif function_name == "manage_env_files":
            action = args["action"]

            if action == "parse":
                # EnvManager: the top-level `--no-color` flag must precede the
                # subcommand; `list` prints the parsed variables. `--hide-values`
                # keeps secret values out of the output (and conversation history).
                cmd.extend(["--no-color", "list", args.get("file_path", ".env"), "--hide-values"])
            else:
                message = f"EnvManager action '{action}' - execute manually"
                return ToolExecutionResult(
                    status=ToolStatus.MANUAL_REQUIRED,
                    tool_name=function_name,
                    duration=time.time() - start_time,
                    stdout=message,
                    structured_payload={
                        "message": message,
                        "file_path": args.get("file_path")
                    },
                    has_side_effects=True
                )

        elif function_name == "compare_files":
            cmd.append(args["file1"])
            cmd.append(args["file2"])
            if args.get("format"):
                cmd.extend(["--mode", args["format"]])  # FileDiff uses --mode, not --format
            cmd.append("--no-color")

        elif function_name == "analyze_git_repository":
            cmd.append(args.get("repo_path", "."))

            # Map report_type to appropriate git_stats.py arguments
            report_type = args.get("report_type", "summary")
            top_n = args.get("top_n", 10)
            recent_days = args.get("recent_days", 30)

            if report_type == "full":
                cmd.append("--full")
            elif report_type == "contributors":
                cmd.extend(["--contributors", str(top_n)])
            elif report_type == "files":
                cmd.extend(["--files", str(top_n)])
            elif report_type == "activity":
                cmd.append("--activity")
            elif report_type == "recent":
                cmd.extend(["--recent", str(recent_days)])
            # "summary" is default - no extra args needed

            if args.get("no_color", True):
                cmd.append("--no-color")

        elif function_name == "optimize_python_imports":
            # ImportOptimizer uses subcommands: unused or organize
            command = args.get("command", "unused")
            cmd.append(command)
            cmd.append(args["path"])

            if command == "unused" and args.get("recursive"):
                cmd.append("--recursive")

            if args.get("no_color", True):
                cmd.append("--no-color")

        elif function_name == "visualize_directory_tree":
            # PathSketch is a directory tree visualization tool
            cmd.append(args.get("path", "."))

            if args.get("show_all"):
                cmd.append("--all")
            if args.get("show_size"):
                cmd.append("--size")
            if args.get("max_depth") and args["max_depth"] > 0:
                cmd.extend(["--max-depth", str(args["max_depth"])])
            if args.get("pattern"):
                cmd.extend(["--pattern", args["pattern"]])
            if args.get("sort_by"):
                cmd.extend(["--sort", args["sort_by"]])
            if args.get("no_color", True):
                cmd.append("--no-color")

        elif function_name == "extract_todos":
            cmd.append(args["path"])
            # TodoExtractor uses --no-recursive flag (inverted logic)
            if not args.get("recursive", True):
                cmd.append("--no-recursive")
            if args.get("extensions"):
                cmd.extend(["--extensions"] + args["extensions"])
            if args.get("keywords"):
                cmd.extend(["--tags"] + args["keywords"])  # TodoExtractor uses --tags, not --keywords
            cmd.append("--no-color")

        elif function_name == "convert_data_format":
            cmd.append(args["input_file"])
            cmd.append(args["output_file"])
            cmd.extend(["--input-format", args["from_format"]])  # DataConvert uses --input-format
            cmd.extend(["--output-format", args["to_format"]])  # DataConvert uses --output-format
            cmd.append("--no-color")  # keep ANSI escapes out of output returned to the model

        else:
            return ToolExecutionResult(
                status=ToolStatus.ERROR,
                tool_name=function_name,
                duration=time.time() - start_time,
                error_message=f"Function {function_name} not fully implemented",
                error_type="NotImplementedError"
            )

        # Execute command
        # Security note: Using list-based arguments without shell=True is secure
        # against command injection. Arguments are passed directly to the executable
        # without shell interpretation, even if they contain special characters.
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
                shell=False,  # Explicitly disable shell for security
                env=_child_env(),  # least privilege: strip parent secrets
            )

            # Calculate final duration
            duration = time.time() - start_time

            # Bound captured stdout before parsing/persisting it.
            stdout = result.stdout or ""
            if len(stdout) > _MAX_OUTPUT_CHARS:
                stdout = (
                    stdout[:_MAX_OUTPUT_CHARS]
                    + f"\n... [truncated {len(result.stdout) - _MAX_OUTPUT_CHARS} chars]"
                )

            # Try to parse structured payload from stdout
            structured_payload = None
            try:
                structured_payload = json.loads(stdout)
            except (json.JSONDecodeError, ValueError):
                # Not JSON (or truncated) - stdout stays plain text
                pass

            # Determine status based on exit code
            if result.returncode == 0:
                status = ToolStatus.SUCCESS
                error_msg = None
                error_type = None
            else:
                status = ToolStatus.ERROR
                error_msg = result.stderr.strip() if result.stderr else f"Command failed with exit code {result.returncode}"
                error_type = "SubprocessError"

            # Determine if tool has side effects.
            # Note: bulk_rename_files and non-parse manage_env_files actions return
            # MANUAL_REQUIRED earlier and never reach this subprocess path; the only
            # reachable EnvManager action here ("parse"/list) is read-only.
            has_side_effects = function_name in [
                "manage_code_snippets",  # add/delete operations
                "convert_data_format",  # writes output file
            ]

            return ToolExecutionResult(
                status=status,
                stdout=stdout,
                stderr=result.stderr,
                structured_payload=structured_payload,
                duration=duration,
                tool_name=function_name,
                exit_code=result.returncode,
                command=" ".join(cmd),
                error_message=error_msg,
                error_type=error_type,
                has_side_effects=has_side_effects
            )

        except subprocess.TimeoutExpired:
            return ToolExecutionResult(
                status=ToolStatus.TIMEOUT,
                tool_name=function_name,
                duration=time.time() - start_time,
                command=" ".join(cmd),
                error_message=f"Command timed out after {self.timeout} seconds",
                error_type="TimeoutError"
            )

        except Exception as e:
            return ToolExecutionResult(
                status=ToolStatus.ERROR,
                tool_name=function_name,
                duration=time.time() - start_time,
                command=" ".join(cmd),
                error_message=f"Error executing command: {str(e)}",
                error_type=type(e).__name__
            )
