#!/usr/bin/env python3
"""ToolExecutor - Safely execute utility tools."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .execution_result import (
    TOOL_STATUS_ERROR,
    TOOL_STATUS_MANUAL_REQUIRED,
    TOOL_STATUS_SUCCESS,
    TOOL_STATUS_TIMEOUT,
    ToolExecutionResult,
)

MAX_OUTPUT_LENGTH = 8_192


class ToolExecutor:
    """Execute utility tools safely."""

    def __init__(self, utils_dir: Optional[str] = None):
        # Get utilities directory
        if utils_dir:
            self.utils_dir = Path(utils_dir)
        else:
            # Assume we're in ChatSystem, go up one level
            self.utils_dir = Path(__file__).parent.parent.parent

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

        # Tools that may cause side effects when executed automatically
        self.side_effect_tools = {"bulk_rename_files", "manage_env_files"}

    def execute(self, function_name: str, arguments: Dict[str, Any]) -> ToolExecutionResult:
        """Execute a tool function and return a normalized result."""

        metadata = {
            "name": function_name,
            "version": "1.0",
            "side_effects": function_name in self.side_effect_tools,
        }

        if function_name not in self.function_to_util:
            return ToolExecutionResult.from_error(
                f"Unknown function: {function_name}", metadata=metadata
            )

        start_time = time.perf_counter()

        util_script = self.utils_dir / self.function_to_util[function_name]
        if not util_script.exists():
            return ToolExecutionResult.from_error(
                f"Utility script not found: {util_script}", metadata=metadata
            )

        command_or_result = self._build_command(function_name, util_script, arguments)

        if isinstance(command_or_result, ToolExecutionResult):
            result = command_or_result
            result.duration = time.perf_counter() - start_time
            result.stdout = self._truncate(result.stdout)
            result.stderr = self._truncate(result.stderr)
            result.metadata = {**metadata, **result.metadata}
            return result

        cmd, metadata_updates = command_or_result
        if metadata_updates:
            metadata.update(metadata_updates)

        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - start_time
            stdout = self._truncate((exc.stdout or "").strip())
            stderr = self._truncate((exc.stderr or "Command timed out after 60 seconds").strip())
            return ToolExecutionResult(
                status=TOOL_STATUS_TIMEOUT,
                stdout=stdout,
                stderr=stderr,
                structured_payload=None,
                duration=duration,
                metadata=metadata,
            )
        except Exception as exc:  # pragma: no cover - defensive
            duration = time.perf_counter() - start_time
            return ToolExecutionResult(
                status=TOOL_STATUS_ERROR,
                stdout="",
                stderr=str(exc),
                structured_payload=None,
                duration=duration,
                metadata=metadata,
            )

        duration = time.perf_counter() - start_time
        stdout = self._truncate((completed.stdout or "").strip())
        stderr = self._truncate((completed.stderr or "").strip())
        structured_payload = self._parse_structured_payload(stdout)

        status = TOOL_STATUS_SUCCESS
        if completed.returncode != 0:
            status = TOOL_STATUS_ERROR
            if not stderr:
                stderr = f"Command failed with exit code {completed.returncode}"

        return ToolExecutionResult(
            status=status,
            stdout=stdout,
            stderr=stderr,
            structured_payload=structured_payload,
            duration=duration,
            metadata=metadata,
        )

    def _build_command(
        self, function_name: str, script_path: Path, args: Dict[str, Any]
    ) -> Tuple[list[str], Dict[str, Any]] | ToolExecutionResult:
        """Build command line arguments for a given tool."""

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
            payload = {
                "message": "BulkRename requires interactive confirmation. Please use the CLI directly.",
                "path": args.get("path"),
                "pattern": args.get("pattern"),
                "replacement": args.get("replacement"),
                "mode": args.get("mode"),
                "dry_run": args.get("dry_run", True),
            }
            return ToolExecutionResult(
                status=TOOL_STATUS_MANUAL_REQUIRED,
                stdout="",
                stderr="",
                structured_payload=payload,
                duration=0.0,
                metadata={"name": function_name, "version": "1.0", "side_effects": True},
            )

        elif function_name == "manage_env_files":
            action = args["action"]

            if action == "parse":
                cmd.extend([args.get("file_path", ".env")])
                cmd.append("--no-color")
            else:
                payload = {
                    "message": f"EnvManager action '{action}' requires manual execution.",
                    "file_path": args.get("file_path"),
                }
                return ToolExecutionResult(
                    status=TOOL_STATUS_MANUAL_REQUIRED,
                    stdout="",
                    stderr="",
                    structured_payload=payload,
                    duration=0.0,
                    metadata={"name": function_name, "version": "1.0", "side_effects": True},
                )

        elif function_name == "compare_files":
            cmd.append(args["file1"])
            cmd.append(args["file2"])
            if args.get("format"):
                cmd.extend(["--mode", args["format"]])
            cmd.append("--no-color")

        elif function_name == "analyze_git_repository":
            cmd.append(args.get("repo_path", "."))

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

            if args.get("no_color", True):
                cmd.append("--no-color")

        elif function_name == "optimize_python_imports":
            command = args.get("command", "unused")
            cmd.append(command)
            cmd.append(args["path"])

            if command == "unused" and args.get("recursive"):
                cmd.append("--recursive")

            if args.get("no_color", True):
                cmd.append("--no-color")

        elif function_name == "visualize_directory_tree":
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
            if not args.get("recursive", True):
                cmd.append("--no-recursive")
            if args.get("extensions"):
                cmd.extend(["--extensions"] + args["extensions"])
            if args.get("keywords"):
                cmd.extend(["--tags"] + args["keywords"])
            cmd.append("--no-color")

        elif function_name == "convert_data_format":
            cmd.append(args["input_file"])
            cmd.append(args["output_file"])
            cmd.extend(["--input-format", args["from_format"]])
            cmd.extend(["--output-format", args["to_format"]])

        else:
            return ToolExecutionResult(
                status=TOOL_STATUS_ERROR,
                stdout="",
                stderr=f"Function {function_name} not fully implemented",
                structured_payload={"error": "Function not implemented"},
                duration=0.0,
                metadata={"name": function_name, "version": "1.0", "side_effects": False},
            )

        return cmd, {}

    @staticmethod
    def _truncate(value: str, limit: int = MAX_OUTPUT_LENGTH) -> str:
        if len(value) <= limit:
            return value
        return value[: limit - 3] + "..."

    @staticmethod
    def _parse_structured_payload(stdout: str) -> Optional[Any]:
        if not stdout:
            return None

        stripped = stdout.strip()
        if not stripped:
            return None

        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return None
