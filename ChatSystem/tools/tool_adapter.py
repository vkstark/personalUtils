#!/usr/bin/env python3
"""
ToolAdapter - Convert utilities into OpenAI function calling format
"""

from typing import Dict, Any, List, Optional


class ToolAdapter:
    """Adapts personalUtils into OpenAI function format"""

    # Tool definitions for all 12 utilities
    TOOL_DEFINITIONS = {
        "CodeWhisper": {
            "name": "analyze_python_code",
            "description": "Analyze Python code files or directories. Provides comprehensive analysis including functions, classes, imports, complexity metrics, and code structure.",
            "strict": True,
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
            "strict": True,
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
            "strict": True,
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
            "strict": True,
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
            "strict": True,
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
            "strict": True,
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
            "strict": True,
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
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Path to git repository",
                        "default": "."
                    },
                    "stats_type": {
                        "type": "string",
                        "enum": ["summary", "contributors", "files", "timeline"],
                        "description": "Type of statistics to generate",
                        "default": "summary"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit number of results",
                        "default": 10
                    }
                },
                "required": ["repo_path"],
                "additionalProperties": False
            }
        },

        "ImportOptimizer": {
            "name": "optimize_python_imports",
            "description": "Optimize and organize Python import statements. Remove unused imports and sort them properly.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Python file path to optimize"
                    },
                    "check_only": {
                        "type": "boolean",
                        "description": "Only check without modifying",
                        "default": False
                    }
                },
                "required": ["file_path"],
                "additionalProperties": False
            }
        },

        "PathSketch": {
            "name": "path_operations",
            "description": "Perform path operations like normalization, resolution, joining, and validation.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["normalize", "resolve", "join", "split", "exists"],
                        "description": "Path operation to perform"
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to operate on"
                    },
                    "additional_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional paths (for join operation)"
                    }
                },
                "required": ["operation", "path"],
                "additionalProperties": False
            }
        },

        "TodoExtractor": {
            "name": "extract_todos",
            "description": "Extract TODO, FIXME, HACK, and other comments from code files.",
            "strict": True,
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
            "strict": True,
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
        """Get all tools in OpenAI function calling format"""
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

            # Add strict mode for structured outputs
            if definition.get("strict"):
                tool["function"]["strict"] = True

            tools.append(tool)

        return tools

    @classmethod
    def get_tool_by_name(cls, name: str) -> Optional[Dict[str, Any]]:
        """Get specific tool by function name"""
        for util_name, definition in cls.TOOL_DEFINITIONS.items():
            if definition["name"] == name:
                return {
                    "type": "function",
                    "function": {
                        "name": definition["name"],
                        "description": definition["description"],
                        "parameters": definition["parameters"],
                        "strict": definition.get("strict", False),
                    }
                }
        return None

    @classmethod
    def get_enabled_tools(cls, enabled_utils: List[str]) -> List[Dict[str, Any]]:
        """Get only enabled tools"""
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

                if definition.get("strict"):
                    tool["function"]["strict"] = True

                tools.append(tool)

        return tools
