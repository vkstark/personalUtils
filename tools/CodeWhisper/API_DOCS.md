# 🐍 Python Code Analysis Report

## 📊 Project Statistics

- **Files Analyzed:** 2
- **Total Lines of Code:** 1307
- **Total Functions:** 4
- **Total Classes:** 11
- **Total Imports:** 22
- **Average Complexity:** 26.20
- **Syntax Errors:** 0

## 📄 path_sketch.py

**Path:** `PathSketch/path_sketch.py`  
**Lines of Code:** 348  

**Description:** 
A powerful, customizable directory tree visualization tool.

Author: Vishal Kumar
License: MIT


### 📦 Imports

- `import os`
- `import sys`
- `import argparse`
- `import stat`
- `import time`
- `from pathlib import Path`
- `from typing import List, Optional, Union`
- `import re`
- `import json`

### 🏛️ Classes

#### `Colors`

#### `TreeStyle`

Different tree drawing styles

#### `FileInfo`

Container for file information

**Methods:**

- `__init__(self, path: Path) [C:2]`
    - 🛡️ **Handles Errors:** `OSError, PermissionError`

#### `DirectoryTree`

Enhanced directory tree generator

**Methods:**

- `__init__(self, show_hidden: bool = False, show_size: bool = False, show_permissions: bool = False, show_modified: bool = False, max_depth: Optional[int] = None, pattern: Optional[str] = None, ignore_patterns: Optional[List[str]] = None, style: str = 'unicode', colors: bool = True, sort_by: str = 'name', reverse_sort: bool = False) [C:7]`
- `_supports_color(self) -> bool [C:4]`
    - 📖 *Check if terminal supports color output*
- `_colorize(self, text: str, color: str) -> str [C:2]`
    - 📖 *Apply color to text if colors are enabled*
- `_get_file_color(self, file_info: FileInfo) -> str [C:8]`
    - 📖 *Get appropriate color for file based on type*
- `_format_size(self, size: float) -> str [C:3]`
    - 📖 *Format file size in human readable format*
- `_format_time(self, timestamp: float) -> str`
    - 📖 *Format timestamp in readable format*
- `_should_include(self, file_info: FileInfo) -> bool [C:9]`
    - 📖 *Check if file should be included based on filters*
- `_get_entries(self, path: Path) -> List[FileInfo] [C:6]`
    - 📖 *Get and sort directory entries*
    - 🛡️ **Handles Errors:** `PermissionError`
- `_format_file_info(self, file_info: FileInfo) -> str [C:6]`
    - 📖 *Format additional file information*
- `generate_tree(self, start_path: Union[str, Path], output_file: Optional[str] = None) -> str [C:8]`
    - 📖 *Generate the directory tree*
- `_generate_tree_recursive(self, path: Path, prefix: str, output_lines: List[str], depth: int) [C:8]`
    - 📖 *Recursively generate tree structure*

### ⚡ Functions

#### `create_gitignore_patterns() -> List[str]`

Create common ignore patterns similar to .gitignore

#### `main()`

Main function with command line interface

**Complexity:** 10

## 📄 code_whisper.py

**Path:** `CodeWhisper/code_whisper.py`  
**Lines of Code:** 959  

**Description:** 
Enhanced Python Code Analyzer
A comprehensive tool for analyzing Python codebases and generating documentation.

Author: Vishal Kumar
License: MIT


### 📦 Imports

- `import ast`
- `import os`
- `import sys`
- `import argparse`
- `import json`
- `import re`
- `import time`
- `import fnmatch`
- `from pathlib import Path`
- `from typing import Dict, List, Any, Optional, Tuple, Set, Union`
- `from dataclasses import dataclass, asdict`
- `from collections import defaultdict, Counter`
- `import textwrap`

### 🏛️ Classes

#### `Colors`

#### `ParameterInfo`

#### `FunctionInfo`

#### `ClassInfo`

#### `ImportInfo`

#### `FileAnalysis`

#### `PythonAnalyzer`

Enhanced Python code analyzer with comprehensive features

**Methods:**

- `__init__(self, include_docstrings: bool = True, include_complexity: bool = True, include_calls: bool = True, include_prints_logs: bool = True, colors: bool = True, detailed_output: bool = False, include_function_definitions: bool = False) [C:3]`
- `_supports_color(self) -> bool [C:4]`
    - 📖 *Check if terminal supports color output*
- `_colorize(self, text: str, color: str) -> str [C:2]`
    - 📖 *Apply color to text if colors are enabled*
- `_safe_unparse(self, node: ast.AST) -> str [C:7]`
    - 📖 *Safely unparse AST node with fallback*
    - 🛡️ **Handles Errors:** `Exception`
- `_calculate_complexity(self, node: ast.AST) -> int [C:6]`
    - 📖 *Calculate cyclomatic complexity of a function*
- `_extract_calls(self, node: ast.AST) -> List[str] [C:6]`
    - 📖 *Extract function calls from a node*
    - 🛡️ **Handles Errors:** `Exception`
- `_extract_prints_and_logs(self, node: ast.AST, source: str) -> Tuple[List[str], List[str]] [C:14]`
    - 📖 *Extract print and log statements*
    - 🛡️ **Handles Errors:** `TypeError, ValueError, TypeError, ValueError, TypeError, ValueError`
- `_extract_error_handling(self, node: ast.AST) -> List[str] [C:8]`
    - 📖 *Extract exception types handled*
- `_get_function_definition(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], source_lines: List[str]) -> Union[str, None] [C:18]`
    - 📖 *Extract the function definition source code*
    - 🛡️ **Handles Errors:** `Exception`
- `_analyze_function(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], source: str) -> FunctionInfo [C:18]`
    - 📖 *Analyze a function definition*
- `_analyze_class(self, node: ast.ClassDef, source: str) -> ClassInfo [C:12]`
    - 📖 *Analyze a class definition*
- `analyze_file(self, filepath: str) -> FileAnalysis [C:31]`
    - 📖 *Analyze a single Python file*
    - 🖨️ **Prints:** 2 statement(s)
    - 🛡️ **Handles Errors:** `UnicodeDecodeError, SyntaxError, Exception, Exception, Exception`
- `analyze_directory(self, directory: Union[str, Path], pattern: str = '*.py', exclude_patterns: Union[List[str], None] = None) -> Dict[str, FileAnalysis] [C:14]`
    - 📖 *Analyze all Python files in a directory*
- `_format_header(self, text: str, level: int = 1) -> str [C:3]`
    - 📖 *Format section headers with colors and borders*
- `_format_box(self, content: str, title: str = '') -> str [C:4]`
    - 📖 *Format content in a box*
- `_format_method_details(self, method: FunctionInfo, indent: str = '  │    ') -> List[str] [C:30]`
    - 📖 *Format detailed method information including docstring, parameters, etc.*
- `_format_parameter_string(self, param: ParameterInfo) -> str [C:3]`
    - 📖 *Format a parameter with type and default value*
- `format_analysis(self, results: Dict[str, FileAnalysis], output_format: str = 'terminal') -> str [C:3]`
    - 📖 *Format analysis results for display*
- `_format_terminal(self, results: Dict[str, FileAnalysis]) -> str [C:61]`
    - 📖 *Format results for terminal display*
- `_format_json(self, results: Dict[str, FileAnalysis]) -> str [C:2]`
    - 📖 *Format results as JSON*
- `_format_markdown(self, results: Dict[str, FileAnalysis]) -> str [C:44]`
    - 📖 *Format results as Markdown*

### ⚡ Functions

#### `main()`

Main function with command line interface

**Complexity:** 16

#### `should_exclude(file_path: Path) -> bool`

Check if file should be excluded based on patterns

**Complexity:** 9
