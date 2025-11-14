#!/usr/bin/env python3
"""
ToolExecutor - Safely execute utility tools
"""

import sys
import json
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path


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

    def __init__(self, utils_dir: Optional[str] = None):
        """
        Initializes the ToolExecutor.

        Args:
            utils_dir (Optional[str], optional): The directory containing the
                utility tools. If not provided, it is inferred from the location
                of this file. Defaults to None.
        """
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

    def execute(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a specified tool with the given arguments.

        This method finds the corresponding script for the `function_name`,
        constructs the command-line arguments, and runs the script in a
        separate process.

        Args:
            function_name (str): The name of the function to execute.
            arguments (Dict[str, Any]): A dictionary of arguments for the function.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the execution.
            It includes a "success" flag and either a "result" or "error" key.
        """

        if function_name not in self.function_to_util:
            return {
                "success": False,
                "error": f"Unknown function: {function_name}"
            }

        try:
            # Get utility script path
            util_script = self.utils_dir / self.function_to_util[function_name]

            if not util_script.exists():
                return {
                    "success": False,
                    "error": f"Utility script not found: {util_script}"
                }

            # Build command based on function
            result = self._execute_utility(function_name, util_script, arguments)

            return {
                "success": True,
                "result": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _execute_utility(
        self, function_name: str, script_path: Path, args: Dict[str, Any]
    ) -> str:
        """
        Constructs and executes the command-line instruction for a specific utility.

        This private method is responsible for translating the structured
        arguments from the AI into a list of command-line flags and arguments
        that can be passed to `subprocess.run`.

        Args:
            function_name (str): The name of the function being executed.
            script_path (Path): The path to the Python script for the utility.
            args (Dict[str, Any]): The arguments for the utility.

        Returns:
            str: The output from the utility's execution (from stdout or stderr),
            or an error message if the execution fails.
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
            # This is complex - return a structured response
            return json.dumps({
                "message": "BulkRename requires interactive confirmation. Please use the CLI directly.",
                "path": args.get("path"),
                "pattern": args.get("pattern"),
                "replacement": args.get("replacement"),
                "mode": args.get("mode"),
                "dry_run": args.get("dry_run", True)
            })

        elif function_name == "manage_env_files":
            action = args["action"]

            if action == "parse":
                # Parse and return env variables
                cmd.extend([args.get("file_path", ".env")])
                cmd.append("--no-color")
            else:
                return json.dumps({
                    "message": f"EnvManager action '{action}' - execute manually",
                    "file_path": args.get("file_path")
                })

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
            return f"Function {function_name} not fully implemented"

        # Execute command
        # Security note: Using list-based arguments without shell=True is secure
        # against command injection. Arguments are passed directly to the executable
        # without shell interpretation, even if they contain special characters.
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
                shell=False  # Explicitly disable shell for security
            )

            # Check for non-zero exit code
            if result.returncode != 0:
                error_output = result.stderr.strip() if result.stderr else "Unknown error"
                return f"Error: Command failed with exit code {result.returncode}: {error_output}"
            
            # Return output
            output = result.stdout or result.stderr
            return output.strip() if output else "Command executed successfully"

        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 60 seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"
