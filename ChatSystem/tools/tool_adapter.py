#!/usr/bin/env python3
"""
ToolAdapter - Convert utilities into OpenAI function calling format
"""

from typing import Dict, Any, List, Optional


class ToolAdapter:
    """
    Adapts and provides tool definitions in the format required by OpenAI's
    function calling API.

    This class serves as a static container for the definitions of all available
    tools, providing methods to retrieve them in the appropriate format.
    """

    # Tool definitions for all 12 utilities
    TOOL_DEFINITIONS = {
        "CodeWhisper": {
            "name": "analyze_python_code",
            "description": "Analyze Python code files or directories. Provides comprehensive analysis including functions, classes, imports, complexity metrics, and code structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File or directory path to analyze"
                    },
                    "detailed": {
                        "type": "boolean",
                        "description": "Show detailed information including docstrings and parameters",
                        "default": False
                    },
                    "format": {
                        "type": "string",
                        "enum": ["terminal", "json", "markdown"],
                        "description": "Output format",
                        "default": "terminal"
                    }
                },
                "required": ["path"],
                "additionalProperties": False
            }
        },

        "APITester": {
            "name": "test_api_endpoint",
            "description": "Test HTTP API endpoints with various methods (GET, POST, PUT, DELETE, etc.). Returns response status, headers, and body.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "API endpoint URL"
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                        "description": "HTTP method",
                        "default": "GET"
                    },
                    "headers": {
                        "type": "object",
                        "description": "HTTP headers as key-value pairs",
                        "additionalProperties": {"type": "string"}
                    },
                    "data": {
                        "type": "string",
                        "description": "Request body (JSON string)"
                    }
                },
                "required": ["url"],
                "additionalProperties": False
            }
        },

        "DuplicateFinder": {
            "name": "find_duplicate_files",
            "description": "Find duplicate files by hash or filename. Can filter by size and extensions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to scan"
                    },
                    "by_hash": {
                        "type": "boolean",
                        "description": "Find duplicates by file hash (true) or name (false)",
                        "default": True
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Scan directories recursively",
                        "default": True
                    },
                    "extensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by file extensions (e.g., ['.py', '.txt'])"
                    }
                },
                "required": ["path"],
                "additionalProperties": False
            }
        },

        "SnippetManager": {
            "name": "manage_code_snippets",
            "description": "Store, search, and retrieve code snippets. Supports tags and multiple programming languages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "search", "list", "show", "delete"],
                        "description": "Action to perform"
                    },
                    "title": {
                        "type": "string",
                        "description": "Snippet title (for add/show)"
                    },
                    "code": {
                        "type": "string",
                        "description": "Code content (for add)"
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language (for add/search)"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["action"],
                "additionalProperties": False
            }
        },

        "BulkRename": {
            "name": "bulk_rename_files",
            "description": "Batch rename files using patterns, regex, or sequential numbering.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path containing files to rename"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern or regex"
                    },
                    "replacement": {
                        "type": "string",
                        "description": "Replacement pattern"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["replace", "regex", "sequential", "case", "prefix", "suffix"],
                        "description": "Rename mode",
                        "default": "replace"
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview changes without executing",
                        "default": True
                    }
                },
                "required": ["path", "pattern", "replacement"],
                "additionalProperties": False
            }
        },

        "EnvManager": {
            "name": "manage_env_files",
            "description": "Manage .env configuration files. Parse, validate, and switch between environments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["parse", "validate", "compare", "set"],
                        "description": "Action to perform"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to .env file",
                        "default": ".env"
                    },
                    "compare_with": {
                        "type": "string",
                        "description": "Path to second .env file for comparison"
                    }
                },
                "required": ["action"],
                "additionalProperties": False
            }
        },

        "FileDiff": {
            "name": "compare_files",
            "description": "Compare two files or directories and show differences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file1": {
                        "type": "string",
                        "description": "First file or directory path"
                    },
                    "file2": {
                        "type": "string",
                        "description": "Second file or directory path"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["unified", "context", "side-by-side"],
                        "description": "Diff output format",
                        "default": "unified"
                    }
                },
                "required": ["file1", "file2"],
                "additionalProperties": False
            }
        },

        "GitStats": {
            "name": "analyze_git_repository",
            "description": "Analyze git repository statistics including commits, contributors, file changes, and activity over time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Path to git repository",
                        "default": "."
                    },
                    "report_type": {
                        "type": "string",
                        "enum": ["summary", "full", "contributors", "files", "activity", "recent"],
                        "description": "Type of report to generate: summary (basic stats), full (all sections), contributors (top contributors), files (most changed files), activity (commit heatmap), recent (recent activity)",
                        "default": "summary"
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "For contributors/files reports: show top N items (default: 10)",
                        "default": 10
                    },
                    "recent_days": {
                        "type": "integer",
                        "description": "For recent report: number of days to look back (default: 30)",
                        "default": 30
                    },
                    "no_color": {
                        "type": "boolean",
                        "description": "Disable colored output",
                        "default": True
                    }
                },
                "required": ["repo_path"],
                "additionalProperties": False
            }
        },

        "ImportOptimizer": {
            "name": "optimize_python_imports",
            "description": "Analyze and organize Python import statements. Can find unused imports in files/directories or show properly organized imports for a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["unused", "organize"],
                        "description": "Command to execute: 'unused' finds unused imports, 'organize' shows properly organized imports"
                    },
                    "path": {
                        "type": "string",
                        "description": "For 'unused': file or directory path to analyze. For 'organize': Python file path"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "For 'unused' command: recursively scan directories",
                        "default": False
                    },
                    "no_color": {
                        "type": "boolean",
                        "description": "Disable colored output",
                        "default": True
                    }
                },
                "required": ["path"],
                "additionalProperties": False
            }
        },

        "PathSketch": {
            "name": "visualize_directory_tree",
            "description": "Visualize directory structure as a tree. Shows files and folders in a hierarchical tree format with optional file sizes, permissions, and filtering.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to visualize (default: current directory)",
                        "default": "."
                    },
                    "show_all": {
                        "type": "boolean",
                        "description": "Show hidden files and directories",
                        "default": False
                    },
                    "show_size": {
                        "type": "boolean",
                        "description": "Show file sizes",
                        "default": False
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth to traverse (e.g., 2 for two levels)",
                        "default": -1
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Filter files by regex pattern (e.g., '.*\\.py$' for Python files)"
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["name", "size", "modified"],
                        "description": "Sort entries by name, size, or modification time",
                        "default": "name"
                    },
                    "no_color": {
                        "type": "boolean",
                        "description": "Disable colored output",
                        "default": True
                    }
                },
                "required": [],
                "additionalProperties": False
            }
        },

        "TodoExtractor": {
            "name": "extract_todos",
            "description": "Extract TODO, FIXME, HACK, and other comments from code files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File or directory path to scan"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Scan directories recursively",
                        "default": True
                    },
                    "extensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File extensions to scan",
                        "default": [".py", ".js", ".ts", ".java", ".cpp"]
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keywords to search for",
                        "default": ["TODO", "FIXME", "HACK", "NOTE"]
                    }
                },
                "required": ["path"],
                "additionalProperties": False
            }
        },

        "DataConvert": {
            "name": "convert_data_format",
            "description": "Convert data between formats (JSON, YAML, CSV, XML, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_file": {
                        "type": "string",
                        "description": "Input file path"
                    },
                    "output_file": {
                        "type": "string",
                        "description": "Output file path"
                    },
                    "from_format": {
                        "type": "string",
                        "enum": ["json", "yaml", "csv", "xml"],
                        "description": "Source format"
                    },
                    "to_format": {
                        "type": "string",
                        "enum": ["json", "yaml", "csv", "xml"],
                        "description": "Target format"
                    }
                },
                "required": ["input_file", "output_file", "from_format", "to_format"],
                "additionalProperties": False
            }
        },
    }

    @classmethod
    def get_all_tools(cls) -> List[Dict[str, Any]]:
        """
        Retrieves all available tools in the OpenAI function calling format.

        This method iterates through the `TOOL_DEFINITIONS` and formats each one
        as a dictionary that is compatible with the OpenAI API.

        Returns:
            List[Dict[str, Any]]: A list of tool definitions. Each tool is a
            dictionary with a "type" of "function" and a "function" object
            containing the name, description, and parameters.
        """
        tools = []

        for util_name, definition in cls.TOOL_DEFINITIONS.items():
            tool = {
                "type": "function",
                "function": {
                    "name": definition["name"],
                    "description": definition["description"],
                    "parameters": definition["parameters"],
                }
            }

            tools.append(tool)

        return tools

    @classmethod
    def get_tool_by_name(cls, name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific tool definition by its function name.

        Args:
            name (str): The function name of the tool to retrieve (e.g.,
                "analyze_python_code").

        Returns:
            Optional[Dict[str, Any]]: The tool definition in OpenAI format if
            found, otherwise None.
        """
        for util_name, definition in cls.TOOL_DEFINITIONS.items():
            if definition["name"] == name:
                return {
                    "type": "function",
                    "function": {
                        "name": definition["name"],
                        "description": definition["description"],
                        "parameters": definition["parameters"],
                    }
                }
        return None

    @classmethod
    def get_enabled_tools(cls, enabled_utils: List[str]) -> List[Dict[str, Any]]:
        """
        Filters and retrieves the definitions for a specified list of enabled tools.

        This method is used to get the OpenAI-formatted definitions for only the
        tools that are enabled in the application's configuration.

        Args:
            enabled_utils (List[str]): A list of the names of the utilities
                to include (e.g., ["CodeWhisper", "APITester"]).

        Returns:
            List[Dict[str, Any]]: A filtered list of tool definitions in the
            OpenAI format.
        """
        tools = []

        for util_name, definition in cls.TOOL_DEFINITIONS.items():
            if util_name in enabled_utils:
                tool = {
                    "type": "function",
                    "function": {
                        "name": definition["name"],
                        "description": definition["description"],
                        "parameters": definition["parameters"],
                    }
                }

                tools.append(tool)

        return tools
