#!/usr/bin/env python3
"""
ToolExecutor - Safely execute utility tools

Version 2.0: Returns structured ToolExecutionResult for all executions
"""

import sys
import json
import subprocess
import time
from typing import Dict, Any, Optional
from pathlib import Path

from .tool_result import ToolExecutionResult, ToolStatus


class ToolExecutor:
    """Execute utility tools safely"""

    # Timeout for tool execution in seconds
    TOOL_EXECUTION_TIMEOUT = 60.0

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

    def execute(self, function_name: str, arguments: Dict[str, Any]) -> ToolExecutionResult:
        """
        Execute a tool function.

        Args:
            function_name: Name of the function to execute
            arguments: Arguments to pass to the function

        Returns:
            ToolExecutionResult: Structured execution result
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
        Execute specific utility with arguments.

        Args:
            function_name: Name of the function being executed
            script_path: Path to the utility script
            args: Arguments to pass to the utility
            start_time: Time when execution started (for duration tracking)

        Returns:
            ToolExecutionResult: Structured execution result
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
                # Parse and return env variables
                cmd.extend([args.get("file_path", ".env")])
                cmd.append("--no-color")
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
                timeout=self.TOOL_EXECUTION_TIMEOUT,
                check=False,
                shell=False  # Explicitly disable shell for security
            )

            # Calculate final duration
            duration = time.time() - start_time

            # Try to parse structured payload from stdout
            structured_payload = None
            if result.stdout:
                try:
                    structured_payload = json.loads(result.stdout)
                except (json.JSONDecodeError, ValueError):
                    # Not JSON, that's fine - stdout will be plain text
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

            # Determine if tool has side effects
            has_side_effects = function_name in [
                "bulk_rename_files",
                "manage_env_files",
                "manage_code_snippets",  # add/delete operations
                "convert_data_format"  # writes output file
            ]

            return ToolExecutionResult(
                status=status,
                stdout=result.stdout,
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
                duration=self.TOOL_EXECUTION_TIMEOUT,
                command=" ".join(cmd),
                error_message=f"Command timed out after {self.TOOL_EXECUTION_TIMEOUT} seconds",
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
