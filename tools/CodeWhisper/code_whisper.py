#!/usr/bin/env python3
"""
Enhanced Python Code Analyzer
A comprehensive tool for analyzing Python codebases and generating documentation.

Author: Vishal Kumar
License: MIT
"""

import ast
import os
import sys
import argparse
import json
import re
import time
import fnmatch
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import textwrap

# Color codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    
    # Text colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'

@dataclass
class ParameterInfo:
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None
    is_vararg: bool = False
    is_kwarg: bool = False

@dataclass
class FunctionInfo:
    name: str
    line_number: int
    parameters: List[ParameterInfo]
    return_type: Optional[str] = None
    decorators: Union[List[str], None] = None
    docstring: Optional[str] = None
    complexity: int = 0
    calls_made: Union[List[str], None] = None
    prints: Union[List[str], None] = None
    logs: Union[List[str], None] = None
    errors_handled: Union[List[str], None] = None
    is_async: bool = False
    is_property: bool = False
    is_staticmethod: bool = False
    is_classmethod: bool = False
    definition: Optional[str] = None
    end_line: Optional[int] = None

@dataclass
class ClassInfo:
    name: str
    line_number: int
    bases: List[str]
    methods: List[FunctionInfo]
    decorators: Union[List[str], None] = None
    docstring: Optional[str] = None
    properties: Union[List[str], None] = None

@dataclass
class ImportInfo:
    module: str
    names: List[str]
    aliases: Union[Dict[str, str], None] = None
    is_from_import: bool = False
    line_number: int = 0

@dataclass
class FileAnalysis:
    filepath: str
    lines_of_code: int
    imports: List[ImportInfo]
    functions: List[FunctionInfo]
    classes: List[ClassInfo]
    global_variables: List[str]
    constants: List[str]
    docstring: Optional[str] = None
    encoding: str = 'utf-8'
    syntax_errors: Union[List[str], None] = None
    complexity_score: int = 0

class PythonAnalyzer:
    """Enhanced Python code analyzer with comprehensive features"""
    
    def __init__(self, 
                 include_docstrings: bool = True,
                 include_complexity: bool = True,
                 include_calls: bool = True,
                 include_prints_logs: bool = True,
                 colors: bool = True,
                 detailed_output: bool = False,
                 include_function_definitions: bool = False):
        
        self.include_docstrings = include_docstrings
        self.include_complexity = include_complexity
        self.include_calls = include_calls
        self.include_prints_logs = include_prints_logs
        self.colors = colors and self._supports_color()
        self.detailed_output = detailed_output
        self.include_function_definitions = include_function_definitions
        
        # Statistics
        self.stats = {
            'files_analyzed': 0,
            'total_lines': 0,
            'total_functions': 0,
            'total_classes': 0,
            'total_imports': 0,
            'syntax_errors': 0,
            'avg_complexity': 0.0
        }
    
    def _supports_color(self) -> bool:
        """Check if terminal supports color output"""
        return (hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and 
                os.getenv('TERM') != 'dumb')
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled"""
        if not self.colors:
            return text
        return f"{color}{text}{Colors.RESET}"
    
    def _safe_unparse(self, node: ast.AST) -> str:
        """Safely unparse AST node with fallback"""
        if node is None:
            return None
        try:
            if hasattr(ast, 'unparse'):  # Python 3.9+
                return ast.unparse(node)
            else:
                # Fallback for older Python versions
                if isinstance(node, ast.Name):
                    return node.id
                elif isinstance(node, ast.Constant):
                    return repr(node.value)
                elif isinstance(node, ast.Attribute):
                    return f"{self._safe_unparse(node.value)}.{node.attr}"
                else:
                    return "<complex_expression>"
        except Exception:
            return "<unparseable>"
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _extract_calls(self, node: ast.AST) -> List[str]:
        """Extract function calls from a node"""
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    try:
                        value_name = self._safe_unparse(child.func.value)
                        # Check for None - _safe_unparse can return None
                        if value_name:
                            calls.append(f"{value_name}.{child.func.attr}")
                        else:
                            calls.append(f"*.{child.func.attr}")
                    except (AttributeError, TypeError, ValueError):
                        # If we can't safely unparse the value, use wildcard
                        calls.append(f"*.{child.func.attr}")
        return calls
    
    def _extract_prints_and_logs(self, node: ast.AST, source: str) -> Tuple[List[str], List[str]]:
        """Extract print and log statements"""
        prints = []
        logs = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    if child.func.id == 'print':
                        try:
                            segment = ast.get_source_segment(source, child)
                            if segment:
                                prints.append(segment)
                        except (TypeError, ValueError):
                            prints.append("print(...)")
                    elif child.func.id in ('log', 'logger', 'logging'):
                        try:
                            segment = ast.get_source_segment(source, child)
                            if segment:
                                logs.append(segment)
                        except (TypeError, ValueError):
                            logs.append("log(...)")
                elif isinstance(child.func, ast.Attribute):
                    if child.func.attr in ('debug', 'info', 'warning', 'error', 'critical'):
                        try:
                            segment = ast.get_source_segment(source, child)
                            if segment:
                                logs.append(segment)
                        except (TypeError, ValueError):
                            logs.append(f"*.{child.func.attr}(...)")
        
        return prints, logs
    
    def _extract_error_handling(self, node: ast.AST) -> List[str]:
        """Extract exception types handled"""
        handled_exceptions = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.ExceptHandler):
                if child.type:
                    if isinstance(child.type, ast.Name):
                        handled_exceptions.append(child.type.id)
                    elif isinstance(child.type, ast.Tuple):
                        for exc in child.type.elts:
                            if isinstance(exc, ast.Name):
                                handled_exceptions.append(exc.id)
                else:
                    handled_exceptions.append("Exception")
        
        return handled_exceptions
    
    def _get_function_definition(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], source_lines: List[str]) -> Union[str, None]:
        """Extract the function definition source code"""
        try:
            # Get the function definition including decorators
            start_line = node.lineno - 1
            
            # Check for decorators before the function
            if node.decorator_list:
                # Find the first decorator line
                for decorator in node.decorator_list:
                    if hasattr(decorator, 'lineno'):
                        start_line = min(start_line, decorator.lineno - 1)
            
            # Find the end of the function
            end_line = start_line
            if hasattr(node, 'end_lineno') and node.end_lineno is not None:
                end_line = node.end_lineno - 1
            else:
                # Fallback: find the next function/class or end of file
                for i in range(start_line + 1, len(source_lines)):
                    line = source_lines[i].strip()
                    if line and not line.startswith(' ') and not line.startswith('\t'):
                        if line.startswith(('def ', 'class ', 'async def ')):
                            end_line = i - 1
                            break
                else:
                    end_line = len(source_lines) - 1
            
            # Extract the lines
            func_lines = source_lines[start_line:end_line + 1]
            
            # Remove common indentation
            if func_lines:
                # Find minimum indentation (excluding empty lines)
                min_indent = float('inf')
                for line in func_lines:
                    if line.strip():
                        indent = len(line) - len(line.lstrip())
                        min_indent = min(min_indent, indent)
                
                # Remove the common indentation
                if min_indent != float('inf'):
                    func_lines = [line[min_indent:] if line.strip() else line for line in func_lines]
            
            return '\n'.join(func_lines)
        except Exception:
            return None
    
    def _analyze_function_body(self, node: ast.AST, source: str) -> Tuple[int, List[str], List[str], List[str], List[str]]:
        """Analyze function body in a single walk pass to extract complexity, calls, prints, logs, and errors handled"""
        complexity = 1 if self.include_complexity else 0
        calls = []
        prints = []
        logs = []
        handled_exceptions = []

        for child in ast.walk(node):
            # 1. Complexity
            if self.include_complexity:
                if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                    complexity += 1
                elif isinstance(child, ast.ExceptHandler):
                    complexity += 1
                elif isinstance(child, (ast.And, ast.Or)):
                    complexity += 1
                elif isinstance(child, ast.BoolOp):
                    complexity += len(child.values) - 1

            # 2. Calls, prints, and logs
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    func_id = child.func.id
                    if self.include_calls:
                        calls.append(func_id)
                    if self.include_prints_logs:
                        if func_id == 'print':
                            try:
                                segment = ast.get_source_segment(source, child)
                                if segment:
                                    prints.append(segment)
                            except (TypeError, ValueError):
                                prints.append("print(...)")
                        elif func_id in ('log', 'logger', 'logging'):
                            try:
                                segment = ast.get_source_segment(source, child)
                                if segment:
                                    logs.append(segment)
                            except (TypeError, ValueError):
                                logs.append("log(...)")
                elif isinstance(child.func, ast.Attribute):
                    attr_name = child.func.attr
                    if self.include_calls or self.include_prints_logs:
                        try:
                            value_name = self._safe_unparse(child.func.value)
                        except (AttributeError, TypeError, ValueError):
                            value_name = None

                        full_call = f"{value_name}.{attr_name}" if value_name else f"*.{attr_name}"
                        if self.include_calls:
                            calls.append(full_call)
                        if self.include_prints_logs and attr_name in ('debug', 'info', 'warning', 'error', 'critical'):
                            try:
                                segment = ast.get_source_segment(source, child)
                                if segment:
                                    logs.append(segment)
                            except (TypeError, ValueError):
                                logs.append(f"*.{attr_name}(...)")

            # 3. Error handling
            elif isinstance(child, ast.ExceptHandler):
                if child.type:
                    if isinstance(child.type, ast.Name):
                        handled_exceptions.append(child.type.id)
                    elif isinstance(child.type, ast.Tuple):
                        for exc in child.type.elts:
                            if isinstance(exc, ast.Name):
                                handled_exceptions.append(exc.id)
                else:
                    handled_exceptions.append("Exception")

        return complexity, calls, prints, logs, handled_exceptions

    def _analyze_function(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], source: str) -> FunctionInfo:
        """Analyze a function definition"""
        # Extract parameters
        parameters = []
        
        # Regular arguments
        for arg in node.args.args:
            param = ParameterInfo(
                name=arg.arg,
                type_annotation=self._safe_unparse(arg.annotation) if arg.annotation else None
            )
            parameters.append(param)
        
        # Default values
        defaults = node.args.defaults
        if defaults:
            num_defaults = len(defaults)
            for i, default in enumerate(defaults):
                param_index = len(parameters) - num_defaults + i
                if param_index >= 0:
                    parameters[param_index].default_value = self._safe_unparse(default)
        
        # *args
        if node.args.vararg:
            param = ParameterInfo(
                name=f"*{node.args.vararg.arg}",
                type_annotation=self._safe_unparse(node.args.vararg.annotation) if node.args.vararg.annotation else None,
                is_vararg=True
            )
            parameters.append(param)
        
        # **kwargs
        if node.args.kwarg:
            param = ParameterInfo(
                name=f"**{node.args.kwarg.arg}",
                type_annotation=self._safe_unparse(node.args.kwarg.annotation) if node.args.kwarg.annotation else None,
                is_kwarg=True
            )
            parameters.append(param)
        
        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            decorators.append(self._safe_unparse(decorator))
        
        # Determine function type
        is_property = any('property' in dec for dec in decorators)
        is_staticmethod = any('staticmethod' in dec for dec in decorators)
        is_classmethod = any('classmethod' in dec for dec in decorators)
        
        # Extract docstring
        docstring = None
        if (self.include_docstrings and node.body and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            docstring = node.body[0].value.value
        
        # Calculate complexity, calls, prints, logs, and error handling in a single pass!
        complexity, calls_made, prints, logs, errors_handled = self._analyze_function_body(node, source)
        
        # Extract function definition if needed
        definition = None
        if self.include_function_definitions:
            source_lines = source.split('\n')
            definition = self._get_function_definition(node, source_lines)
        
        return FunctionInfo(
            name=node.name,
            line_number=node.lineno,
            parameters=parameters,
            return_type=self._safe_unparse(node.returns) if node.returns else None,
            decorators=decorators,
            docstring=docstring,
            complexity=complexity,
            calls_made=calls_made,
            prints=prints,
            logs=logs,
            errors_handled=errors_handled,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_property=is_property,
            is_staticmethod=is_staticmethod,
            is_classmethod=is_classmethod,
            definition=definition,
            end_line=node.end_lineno if hasattr(node, 'end_lineno') else None
        )
    
    def _analyze_class(self, node: ast.ClassDef, source: str) -> ClassInfo:
        """Analyze a class definition"""
        # Extract base classes
        bases = []
        for base in node.bases:
            bases.append(self._safe_unparse(base))
        
        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            decorators.append(self._safe_unparse(decorator))
        
        # Extract docstring
        docstring = None
        if (self.include_docstrings and node.body and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            docstring = node.body[0].value.value
        
        # Extract methods
        methods = []
        properties = []
        
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = self._analyze_function(item, source)
                methods.append(method_info)
                
                if method_info.is_property:
                    properties.append(method_info.name)
        
        return ClassInfo(
            name=node.name,
            line_number=node.lineno,
            bases=bases,
            methods=methods,
            decorators=decorators,
            docstring=docstring,
            properties=properties
        )
    
    def analyze_file(self, filepath: str) -> FileAnalysis:
        """Analyze a single Python file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                source = file.read()
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='latin-1') as file:
                    source = file.read()
                encoding = 'latin-1'
            except Exception as e:
                return FileAnalysis(
                    filepath=filepath,
                    lines_of_code=0,
                    imports=[],
                    functions=[],
                    classes=[],
                    global_variables=[],
                    constants=[],
                    syntax_errors=[f"Encoding error: {str(e)}"]
                )
        else:
            encoding = 'utf-8'
        
        lines_of_code = len([line for line in source.split('\n') if line.strip() and not line.strip().startswith('#')])
        
        try:
            tree = ast.parse(source, filename=filepath)
        except SyntaxError as e:
            return FileAnalysis(
                filepath=filepath,
                lines_of_code=lines_of_code,
                imports=[],
                functions=[],
                classes=[],
                global_variables=[],
                constants=[],
                encoding=encoding,
                syntax_errors=[f"Syntax error at line {e.lineno}: {e.msg}"]
            )
        
        imports = []
        functions = []
        classes = []
        global_variables = []
        constants = []
        docstring = None
        
        # Extract module docstring
        if (self.include_docstrings and tree.body and 
            isinstance(tree.body[0], ast.Expr) and 
            isinstance(tree.body[0].value, ast.Constant) and 
            isinstance(tree.body[0].value.value, str)):
            docstring = tree.body[0].value.value
        
        # Single-pass walk of the AST to collect all relevant nodes
        class_nodes = []
        function_nodes = []
        import_nodes = []
        import_from_nodes = []
        assign_nodes = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_nodes.append(node)
            elif isinstance(node, ast.ClassDef):
                class_nodes.append(node)
            elif isinstance(node, ast.Import):
                import_nodes.append(node)
            elif isinstance(node, ast.ImportFrom):
                import_from_nodes.append(node)
            elif isinstance(node, ast.Assign):
                assign_nodes.append(node)
                
        # Gather all class methods to verify top-level status in O(1)
        class_methods = set()
        for cls_node in class_nodes:
            for item in cls_node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    class_methods.add(item)

        # Process Imports
        for node in import_nodes:
            for alias in node.names:
                import_info = ImportInfo(
                    module=alias.name,
                    names=[alias.name],
                    aliases={alias.name: alias.asname} if alias.asname else {},
                    line_number=node.lineno
                )
                imports.append(import_info)
                
        # Process FromImports
        for node in import_from_nodes:
            module = node.module if node.module else ''
            names = [alias.name for alias in node.names]
            aliases = {alias.name: alias.asname for alias in node.names if alias.asname}
            
            import_info = ImportInfo(
                module=module,
                names=names,
                aliases=aliases,
                is_from_import=True,
                line_number=node.lineno
            )
            imports.append(import_info)

        # Process Functions
        for node in function_nodes:
            # Check if this function is not a class method in O(1)
            if node not in class_methods:
                try:
                    func_info = self._analyze_function(node, source)
                    functions.append(func_info)
                except Exception as e:
                    # Skip problematic functions but continue analysis
                    print(f"Warning: Could not analyze function '{node.name}': {e}", file=sys.stderr)

        # Process Classes
        for node in class_nodes:
            try:
                class_info = self._analyze_class(node, source)
                classes.append(class_info)
            except Exception as e:
                # Skip problematic classes but continue analysis
                print(f"Warning: Could not analyze class '{node.name}': {e}", file=sys.stderr)

        # Process Assignments
        for node in assign_nodes:
            # Extract global variables and constants
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id.isupper():
                        constants.append(target.id)
                    else:
                        global_variables.append(target.id)
        
        # Calculate complexity score
        complexity_score = sum(func.complexity for func in functions)
        for cls in classes:
            complexity_score += sum(method.complexity for method in cls.methods)
        
        return FileAnalysis(
            filepath=filepath,
            lines_of_code=lines_of_code,
            imports=imports,
            functions=functions,
            classes=classes,
            global_variables=global_variables,
            constants=constants,
            docstring=docstring,
            encoding=encoding,
            complexity_score=complexity_score
        )
    
    def analyze_directory(self, directory: Union[str, Path], pattern: str = "*.py", 
                         exclude_patterns: Union[List[str], None] = None) -> Dict[str, FileAnalysis]:
        """Analyze all Python files in a directory"""
        directory = Path(directory)
        results = {}
        
        exclude_patterns = exclude_patterns or ['__pycache__', '.git', '.venv', 'venv']
        
        def should_exclude(file_path: Path) -> bool:
            """Check if file should be excluded based on patterns"""
            file_str = str(file_path)
            file_name = file_path.name
            
            for pat in exclude_patterns:
                # Handle glob patterns (containing * or ?)
                if '*' in pat or '?' in pat:
                    if fnmatch.fnmatch(file_name, pat) or fnmatch.fnmatch(file_str, pat):
                        return True
                # Handle simple string matching
                else:
                    if pat in file_str:
                        return True
            return False
        
        # Walk directory and prune in-place to avoid entering excluded dirs
        for root, dirs, files in os.walk(directory):
            # Prune directories in-place to avoid traversal
            dirs_to_keep = []
            for d in dirs:
                dir_path = Path(root) / d
                if should_exclude(dir_path):
                    continue
                dirs_to_keep.append(d)
            dirs[:] = dirs_to_keep
            
            # Filter files by pattern and exclusion
            for file_name in files:
                if fnmatch.fnmatch(file_name, pattern):
                    file_path = Path(root) / file_name
                    if should_exclude(file_path):
                        continue

                    analysis = self.analyze_file(str(file_path))
                    results[str(file_path)] = analysis

                    # Update statistics
                    self.stats['files_analyzed'] += 1
                    self.stats['total_lines'] += analysis.lines_of_code
                    self.stats['total_functions'] += len(analysis.functions)
                    self.stats['total_classes'] += len(analysis.classes)
                    self.stats['total_imports'] += len(analysis.imports)

                    if analysis.syntax_errors:
                        self.stats['syntax_errors'] += 1
        
        # Calculate average complexity
        total_complexity = sum(analysis.complexity_score for analysis in results.values())
        total_items = sum(len(analysis.functions) + len(analysis.classes) for analysis in results.values())
        self.stats['avg_complexity'] = total_complexity / max(total_items, 1)
        
        return results
    
    def _format_header(self, text: str, level: int = 1) -> str:
        """Format section headers with colors and borders"""
        colors = [
            Colors.BRIGHT_CYAN + Colors.BOLD,
            Colors.BRIGHT_YELLOW + Colors.BOLD,
            Colors.BRIGHT_GREEN + Colors.BOLD,
            Colors.BRIGHT_MAGENTA + Colors.BOLD
        ]
        
        color = colors[min(level - 1, len(colors) - 1)]
        
        if level == 1:
            border = "═" * len(text)
            return f"\n{self._colorize(border, color)}\n{self._colorize(text, color)}\n{self._colorize(border, color)}\n"
        elif level == 2:
            border = "─" * len(text)
            return f"\n{self._colorize(text, color)}\n{self._colorize(border, color)}\n"
        else:
            return f"\n{self._colorize('▶ ' + text, color)}\n"
    
    def _format_box(self, content: str, title: str = "") -> str:
        """Format content in a box"""
        lines = content.split('\n')
        max_width = max(len(line) for line in lines) if lines else 0
        
        if title:
            max_width = max(max_width, len(title) + 4)
        
        box_width = max_width + 4
        
        result = []
        
        # Top border
        if title:
            title_line = f"┌─ {title} " + "─" * (box_width - len(title) - 4) + "┐"
            result.append(self._colorize(title_line, Colors.CYAN))
        else:
            result.append(self._colorize("┌" + "─" * (box_width - 2) + "┐", Colors.CYAN))
        
        # Content
        for line in lines:
            padded_line = f"│ {line:<{max_width}} │"
            result.append(self._colorize("│", Colors.CYAN) + f" {line:<{max_width}} " + self._colorize("│", Colors.CYAN))
        
        # Bottom border
        result.append(self._colorize("└" + "─" * (box_width - 2) + "┘", Colors.CYAN))
        
        return "\n".join(result)
    
    def _format_method_details(self, method: FunctionInfo, indent: str = "  │    ") -> List[str]:
        """Format detailed method information including docstring, parameters, etc."""
        details = []
        
        # Docstring
        if method.docstring and self.include_docstrings:
            doc_preview = method.docstring.split('\n')[0][:80]  # First line, max 80 chars
            if len(method.docstring) > 80 or '\n' in method.docstring:
                doc_preview += "..."
            details.append(f"{indent}📖 {self._colorize(doc_preview, Colors.DIM)}")
        
        # Decorators (excluding property/staticmethod/classmethod as they're shown in the method type)
        other_decorators = []
        if method.decorators:
            for dec in method.decorators:
                if dec not in ['property', 'staticmethod', 'classmethod', '@property', '@staticmethod', '@classmethod']:
                    other_decorators.append(dec)
        if other_decorators:
            details.append(f"{indent}🎨 Decorators: {self._colorize(', '.join(other_decorators), Colors.YELLOW)}")
        
        # Detailed parameters (only in detailed mode)
        if self.detailed_output and method.parameters:
            param_details = []
            for param in method.parameters:
                param_str = self._format_parameter_string(param)
                param_details.append(param_str)
            details.append(f"{indent}📝 Parameters: {self._colorize(', '.join(param_details), Colors.DIM)}")
        
        # Return type (if not already shown in main line)
        if self.detailed_output and method.return_type:
            details.append(f"{indent}🔄 Returns: {self._colorize(method.return_type, Colors.GREEN)}")
        
        # Complexity (if high)
        if self.include_complexity and method.complexity > 5:
            details.append(f"{indent}⚠️  High Complexity: {self._colorize(str(method.complexity), Colors.YELLOW)}")
        
        # Prints and logs
        if self.include_prints_logs:
            if method.prints:
                details.append(f"{indent}🖨️  Prints: {len(method.prints)} statement(s)")
            if method.logs:
                details.append(f"{indent}📋 Logs: {len(method.logs)} statement(s)")
        
        # Error handling
        if method.errors_handled:
            details.append(f"{indent}🛡️  Handles: {self._colorize(', '.join(method.errors_handled), Colors.YELLOW)}")
        
        # Function definition (if enabled)
        if self.include_function_definitions and method.definition:
            details.append(f"{indent}{self._colorize('📄 Definition:', Colors.BRIGHT_BLUE)}")
            # Indent the definition
            for line in method.definition.split('\n')[:10]:  # Show first 10 lines
                details.append(f"{indent}  {self._colorize(line, Colors.DIM)}")
            if len(method.definition.split('\n')) > 10:
                details.append(f"{indent}  {self._colorize('... (truncated)', Colors.DIM)}")
        
        return details

    def _format_parameter_string(self, param: ParameterInfo) -> str:
        """Format a parameter with type and default value"""
        param_str = param.name
        if param.type_annotation:
            param_str += f": {param.type_annotation}"
        if param.default_value:
            param_str += f" = {param.default_value}"
        return param_str
    
    def format_analysis(self, results: Dict[str, FileAnalysis], 
                       output_format: str = 'terminal') -> str:
        """Format analysis results for display"""
        if output_format == 'json':
            return self._format_json(results)
        elif output_format == 'markdown':
            return self._format_markdown(results)
        else:
            return self._format_terminal(results)
    
    def _format_terminal(self, results: Dict[str, FileAnalysis]) -> str:
        """Format results for terminal display"""
        output = []
        
        # Header
        title = "🐍 Python Code Analysis Report"
        output.append(self._format_header(title, 1))
        
        # Statistics
        stats_content = f"""Files Analyzed: {self.stats['files_analyzed']}
Total Lines of Code: {self.stats['total_lines']}
Total Functions: {self.stats['total_functions']}
Total Classes: {self.stats['total_classes']}
Total Imports: {self.stats['total_imports']}
Average Complexity: {self.stats['avg_complexity']:.2f}
Syntax Errors: {self.stats['syntax_errors']}"""
        
        output.append(self._format_box(stats_content, "📊 Project Statistics"))
        
        # File-by-file analysis
        for filepath, analysis in results.items():
            output.append(self._format_header(f"📄 {os.path.basename(filepath)}", 2))
            output.append(f"📁 Path: {self._colorize(filepath, Colors.DIM)}")
            output.append(f"📏 Lines of Code: {self._colorize(str(analysis.lines_of_code), Colors.YELLOW)}")
            
            if analysis.syntax_errors:
                output.append(f"\n{self._colorize('❌ SYNTAX ERRORS:', Colors.BRIGHT_RED + Colors.BOLD)}")
                for error in analysis.syntax_errors:
                    output.append(f"  • {self._colorize(error, Colors.RED)}")
                continue
            
            # Module docstring
            if analysis.docstring:
                doc_preview = analysis.docstring[:100] + "..." if len(analysis.docstring) > 100 else analysis.docstring
                output.append(f"\n{self._colorize('📖 Module Description:', Colors.BRIGHT_BLUE)}")
                output.append(f"  {self._colorize(doc_preview, Colors.BLUE)}")
            
            # Imports
            if analysis.imports:
                output.append(f"\n{self._colorize('📦 IMPORTS', Colors.BRIGHT_GREEN + Colors.BOLD)}")
                for imp in analysis.imports:
                    if imp.is_from_import:
                        names_str = ", ".join(imp.names[:3])
                        if len(imp.names) > 3:
                            names_str += f" ... (+{len(imp.names) - 3} more)"
                        output.append(f"  ├─ from {self._colorize(imp.module, Colors.GREEN)} import {self._colorize(names_str, Colors.CYAN)}")
                    else:
                        output.append(f"  ├─ import {self._colorize(imp.module, Colors.GREEN)}")
            
            # Global variables and constants
            if analysis.global_variables or analysis.constants:
                output.append(f"\n{self._colorize('🌐 GLOBAL SCOPE', Colors.BRIGHT_YELLOW + Colors.BOLD)}")
                if analysis.constants:
                    const_str = ", ".join(analysis.constants[:5])
                    if len(analysis.constants) > 5:
                        const_str += f" ... (+{len(analysis.constants) - 5} more)"
                    output.append(f"  ├─ Constants: {self._colorize(const_str, Colors.YELLOW)}")
                if analysis.global_variables:
                    var_str = ", ".join(analysis.global_variables[:5])
                    if len(analysis.global_variables) > 5:
                        var_str += f" ... (+{len(analysis.global_variables) - 5} more)"
                    output.append(f"  ├─ Variables: {self._colorize(var_str, Colors.YELLOW)}")
            
            # Classes
            if analysis.classes:
                output.append(f"\n{self._colorize('🏛️  CLASSES', Colors.BRIGHT_MAGENTA + Colors.BOLD)}")
                for cls in analysis.classes:
                    inheritance = f"({', '.join(cls.bases)})" if cls.bases else ""
                    complexity_info = f" [Complexity: {sum(m.complexity for m in cls.methods)}]" if self.include_complexity else ""
                    output.append(f"  ├─ {self._colorize(cls.name, Colors.MAGENTA + Colors.BOLD)}{inheritance}{complexity_info}")
                    
                    if cls.docstring and self.detailed_output:
                        doc_preview = cls.docstring[:80] + "..." if len(cls.docstring) > 80 else cls.docstring
                        output.append(f"  │  📖 {self._colorize(doc_preview, Colors.DIM)}")
                    
                    # Methods
                    if cls.methods:
                        for i, method in enumerate(cls.methods):
                            is_last = i == len(cls.methods) - 1
                            connector = "└─" if is_last else "├─"
                            
                            method_type = ""
                            if method.is_property:
                                method_type = self._colorize("@property ", Colors.CYAN)
                            elif method.is_staticmethod:
                                method_type = self._colorize("@staticmethod ", Colors.CYAN)
                            elif method.is_classmethod:
                                method_type = self._colorize("@classmethod ", Colors.CYAN)
                            
                            # Format parameters
                            param_strs = []
                            for param in method.parameters:
                                param_strs.append(self._format_parameter_string(param))
                            params_display = f"({', '.join(param_strs)})" if param_strs else "()"
                            
                            # Return type and complexity
                            return_info = f" -> {method.return_type}" if method.return_type else ""
                            complexity_info = f" [C:{method.complexity}]" if self.include_complexity and method.complexity > 1 else ""
                            
                            output.append(f"  │  {connector} {method_type}{self._colorize(method.name, Colors.CYAN)}{params_display}{return_info}{complexity_info}")
                            
                            # ADD THIS PART - Method details similar to functions
                            if self.detailed_output or self.include_function_definitions:
                                indent = "  │  │  " if not is_last else "  │     "
                                
                                # Docstring
                                if method.docstring:
                                    doc_preview = method.docstring[:80] + "..." if len(method.docstring) > 80 else method.docstring
                                    doc_preview = doc_preview.replace('\n', ' ')
                                    output.append(f"{indent}📖 {self._colorize(doc_preview, Colors.DIM)}")
                                
                                # Decorators
                                if method.decorators and len([d for d in method.decorators if d not in ['property', 'staticmethod', 'classmethod']]) > 0:
                                    other_decorators = [d for d in method.decorators if d not in ['property', 'staticmethod', 'classmethod']]
                                    output.append(f"{indent}🎨 Decorators: {self._colorize(', '.join(other_decorators), Colors.YELLOW)}")
                                
                                # Prints and logs
                                if method.prints:
                                    output.append(f"{indent}🖨️  Prints: {len(method.prints)} statement(s)")
                                if method.logs:
                                    output.append(f"{indent}📋 Logs: {len(method.logs)} statement(s)")
                                
                                # Error handling
                                if method.errors_handled:
                                    output.append(f"{indent}🛡️  Handles: {self._colorize(', '.join(method.errors_handled), Colors.YELLOW)}")
                                
                                # Function definition
                                if self.include_function_definitions and method.definition:
                                    output.append(f"{indent}{self._colorize('📄 Definition:', Colors.BRIGHT_BLUE)}")
                                    # Show first few lines of the definition
                                    for line in method.definition.split('\n')[:5]:
                                        output.append(f"{indent}  {self._colorize(line, Colors.DIM)}")
                                    if len(method.definition.split('\n')) > 5:
                                        output.append(f"{indent}  {self._colorize('...', Colors.DIM)}")
            
            # Functions
            if analysis.functions:
                output.append(f"\n{self._colorize('⚡ FUNCTIONS', Colors.BRIGHT_CYAN + Colors.BOLD)}")
                for func in analysis.functions:
                    async_info = self._colorize("async ", Colors.YELLOW) if func.is_async else ""
                    
                    # Format parameters
                    param_strs = []
                    for param in func.parameters:
                        param_strs.append(self._format_parameter_string(param))
                    params_display = f"({', '.join(param_strs)})" if param_strs else "()"
                    
                    # Return type and complexity
                    return_info = f" -> {func.return_type}" if func.return_type else ""
                    complexity_info = f" [C:{func.complexity}]" if self.include_complexity and func.complexity > 1 else ""
                    
                    output.append(f"  ├─ {async_info}{self._colorize(func.name, Colors.CYAN + Colors.BOLD)}{params_display}{return_info}{complexity_info}")
                    
                    if self.detailed_output or self.include_function_definitions:
                        # Docstring
                        if func.docstring:
                            doc_preview = func.docstring[:80] + "..." if len(func.docstring) > 80 else func.docstring
                            doc_preview = doc_preview.replace('\n', ' ')
                            output.append(f"  │  📖 {self._colorize(doc_preview, Colors.DIM)}")
                        
                        # Decorators
                        if func.decorators:
                            output.append(f"  │  🎨 Decorators: {self._colorize(', '.join(func.decorators), Colors.YELLOW)}")
                        
                        # Prints and logs
                        if func.prints:
                            output.append(f"  │  🖨️  Prints: {len(func.prints)} statement(s)")
                        if func.logs:
                            output.append(f"  │  📋 Logs: {len(func.logs)} statement(s)")
                        
                        # Error handling
                        if func.errors_handled:
                            output.append(f"  │  🛡️  Handles: {self._colorize(', '.join(func.errors_handled), Colors.YELLOW)}")
                        
                        # Function definition
                        if self.include_function_definitions and func.definition:
                            output.append(f"  │  {self._colorize('📄 Definition:', Colors.BRIGHT_BLUE)}")
                            # Indent the definition
                            for line in func.definition.split('\n'):
                                output.append(f"  │    {self._colorize(line, Colors.DIM)}")
        
        return "\n".join(output)
    
    def _format_json(self, results: Dict[str, FileAnalysis]) -> str:
        """Format results as JSON"""
        json_data = {
            'statistics': self.stats,
            'files': {}
        }
        
        for filepath, analysis in results.items():
            json_data['files'][filepath] = asdict(analysis)
        
        return json.dumps(json_data, indent=2, default=str)
    
    def _format_markdown(self, results: Dict[str, FileAnalysis]) -> str:
        """Format results as Markdown"""
        output = []

        # Header
        output.append("# 🐍 Python Code Analysis Report\n")

        # Statistics
        output.append("## 📊 Project Statistics\n")
        output.append(f"- **Files Analyzed:** {self.stats['files_analyzed']}")
        output.append(f"- **Total Lines of Code:** {self.stats['total_lines']}")
        output.append(f"- **Total Functions:** {self.stats['total_functions']}")
        output.append(f"- **Total Classes:** {self.stats['total_classes']}")
        output.append(f"- **Total Imports:** {self.stats['total_imports']}")
        output.append(f"- **Average Complexity:** {self.stats['avg_complexity']:.2f}")
        output.append(f"- **Syntax Errors:** {self.stats['syntax_errors']}\n")

        # Files
        for filepath, analysis in results.items():
            filename = os.path.basename(filepath)
            output.append(f"## 📄 {filename}\n")
            output.append(f"**Path:** `{filepath}`  ")
            output.append(f"**Lines of Code:** {analysis.lines_of_code}  ")

            if analysis.syntax_errors:
                output.append(f"\n❌ **SYNTAX ERRORS:**\n")
                for error in analysis.syntax_errors:
                    output.append(f"- {error}")
                continue

            # Module docstring
            if analysis.docstring:
                output.append(f"\n**Description:** {analysis.docstring}\n")

            # Imports
            if analysis.imports:
                output.append("### 📦 Imports\n")
                for imp in analysis.imports:
                    if imp.is_from_import:
                        output.append(f"- `from {imp.module} import {', '.join(imp.names)}`")
                    else:
                        output.append(f"- `import {imp.module}`")
                output.append("")

            # Classes
            if analysis.classes:
                output.append("### 🏛️ Classes\n")
                for cls in analysis.classes:
                    inheritance = f" (inherits from {', '.join(cls.bases)})" if cls.bases else ""
                    output.append(f"#### `{cls.name}`{inheritance}\n")

                    if cls.docstring:
                        output.append(f"{cls.docstring}\n")

                    if cls.methods:
                        output.append("**Methods:**\n")
                        for method in cls.methods:
                            # Determine decorator prefix
                            method_type = ""
                            if method.is_property:
                                method_type = "@property "
                            elif method.is_staticmethod:
                                method_type = "@staticmethod "
                            elif method.is_classmethod:
                                method_type = "@classmethod "

                            # Format parameters
                            param_strs = []
                            for param in method.parameters:
                                param_strs.append(self._format_parameter_string(param))
                            params_display = f"({', '.join(param_strs)})" if param_strs else "()"

                            # Return type and complexity
                            return_info = f" -> {method.return_type}" if method.return_type else ""
                            complexity_info = (
                                f" [C:{method.complexity}]"
                                if self.include_complexity and method.complexity > 1
                                else ""
                            )

                            # Method signature
                            output.append(
                                f"- `{method_type}{method.name}{params_display}{return_info}{complexity_info}`"
                            )

                            # Detailed method info
                            if self.detailed_output or self.include_function_definitions:
                                # Docstring preview
                                if method.docstring:
                                    doc_preview = method.docstring[:80] + "..." if len(method.docstring) > 80 else method.docstring
                                    doc_preview = doc_preview.replace("\n", " ")
                                    output.append(f"    - 📖 *{doc_preview}*")

                                # Other decorators
                                other_decorators = [
                                    d for d in (method.decorators or [])
                                    if d not in ["property", "staticmethod", "classmethod"]
                                ]
                                if other_decorators:
                                    output.append(f"    - 🎨 **Decorators:** `{', '.join(other_decorators)}`")

                                # Prints and logs
                                if method.prints:
                                    output.append(f"    - 🖨️ **Prints:** {len(method.prints)} statement(s)")
                                if method.logs:
                                    output.append(f"    - 📋 **Logs:** {len(method.logs)} statement(s)")

                                # Error handling
                                if method.errors_handled:
                                    output.append(
                                        f"    - 🛡️ **Handles Errors:** `{', '.join(method.errors_handled)}`"
                                    )

                                # Function definition excerpt
                                if self.include_function_definitions and method.definition:
                                    output.append("    - 📄 **Definition:**")
                                    output.append("```python")
                                    for line in method.definition.split("\n")[:5]:
                                        output.append(f"{line}")
                                    if len(method.definition.split("\n")) > 5:
                                        output.append("...")
                                    output.append("```\n")
                        output.append("")

            # Functions
            if analysis.functions:
                output.append("### ⚡ Functions\n")
                for func in analysis.functions:
                    # Format parameters
                    param_strs = []
                    for param in func.parameters:
                        param_strs.append(self._format_parameter_string(param))
                    params_display = ", ".join(param_strs) if param_strs else ""

                    return_info = f" -> {func.return_type}" if func.return_type else ""
                    output.append(f"#### `{func.name}({params_display}){return_info}`\n")

                    if func.docstring:
                        output.append(f"{func.docstring}\n")

                    if self.include_complexity and func.complexity > 1:
                        output.append(f"**Complexity:** {func.complexity}\n")

                    if self.include_function_definitions and func.definition:
                        output.append("**Definition:**\n")
                        output.append("```python")
                        output.append(func.definition)
                        output.append("```\n")

        return "\n".join(output)


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="Enhanced Python Code Analyzer - Comprehensive codebase analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Analyze current directory
  %(prog)s /path/to/project         # Analyze specific directory
  %(prog)s -d --complexity          # Detailed output with complexity
  %(prog)s --format json -o report.json    # JSON output to file
  %(prog)s --format markdown -o README.md  # Markdown documentation
  %(prog)s --exclude "test_*" "migrations"  # Exclude test files and migrations
  %(prog)s --function-definitions    # Include full function definitions
        """)
    
    parser.add_argument('path', nargs='?', default='.',
                       help='Directory or file path to analyze (default: current directory)')
    
    # Analysis options
    parser.add_argument('-d', '--detailed', action='store_true',
                       help='Show detailed information (parameters, docstrings, etc.)')
    parser.add_argument('--no-docstrings', action='store_true',
                       help='Exclude docstring analysis')
    parser.add_argument('--no-complexity', action='store_true',
                       help='Exclude complexity calculation')
    parser.add_argument('--no-calls', action='store_true',
                       help='Exclude function call analysis')
    parser.add_argument('--no-prints-logs', action='store_true',
                       help='Exclude print/log statement analysis')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')
    parser.add_argument('--function-definitions', action='store_true',
                       help='Include full function definitions in output')
    
    # Filtering options
    parser.add_argument('--pattern', default='*.py', metavar='PATTERN',
                       help='File pattern to match (default: *.py)')
    parser.add_argument('--exclude', action='append', metavar='PATTERN',
                       help='Exclude files matching pattern (can be used multiple times)')
    
    # Output options
    parser.add_argument('--format', choices=['terminal', 'json', 'markdown'],
                       default='terminal', help='Output format (default: terminal)')
    parser.add_argument('-o', '--output', metavar='FILE',
                       help='Save output to file')
    parser.add_argument('--stats-only', action='store_true',
                       help='Show only statistics summary')
    
    # Version
    parser.add_argument('--version', action='version', version='%(prog)s 2.0.0')
    
    args = parser.parse_args()
    
    try:
        # Create analyzer
        analyzer = PythonAnalyzer(
            include_docstrings=not args.no_docstrings,
            include_complexity=not args.no_complexity,
            include_calls=not args.no_calls,
            include_prints_logs=not args.no_prints_logs,
            colors=not args.no_color,
            detailed_output=args.detailed,
            include_function_definitions=args.function_definitions
        )
        
        # Debug: Print what we're analyzing
        if args.path != '.':
            print(f"Analyzing: {args.path}")
        
        # Analyze
        path = Path(args.path)
        if not path.exists():
            print(f"Error: Path '{path}' does not exist.", file=sys.stderr)
            sys.exit(1)
            
        if path.is_file():
            # Single file analysis
            if not str(path).endswith('.py'):
                print(f"Error: '{path}' is not a Python file.", file=sys.stderr)
                sys.exit(1)
                
            analysis = analyzer.analyze_file(str(path))
            results = {str(path): analysis}
            
            # Update stats manually for single file
            analyzer.stats['files_analyzed'] = 1
            analyzer.stats['total_lines'] = analysis.lines_of_code
            analyzer.stats['total_functions'] = len(analysis.functions)
            analyzer.stats['total_classes'] = len(analysis.classes)
            analyzer.stats['total_imports'] = len(analysis.imports)
            analyzer.stats['avg_complexity'] = analysis.complexity_score / max(
                len(analysis.functions) + len(analysis.classes), 1)
            if analysis.syntax_errors:
                analyzer.stats['syntax_errors'] = 1
        else:
            # Directory analysis
            exclude_patterns = args.exclude or ['__pycache__', '.git', '.venv', 'venv', '*.pyc', '*.pyo']
            print(f"Searching for {args.pattern} files...")
            results = analyzer.analyze_directory(str(path), args.pattern, exclude_patterns)
        
        if not results:
            print("No Python files found to analyze.")
            return
        
        # Format and display results
        if args.stats_only:
            stats_content = f"""📊 Analysis Summary:
├─ Files Analyzed: {analyzer.stats['files_analyzed']}
├─ Lines of Code: {analyzer.stats['total_lines']}
├─ Functions: {analyzer.stats['total_functions']}
├─ Classes: {analyzer.stats['total_classes']}
├─ Imports: {analyzer.stats['total_imports']}
├─ Avg Complexity: {analyzer.stats['avg_complexity']:.2f}
└─ Syntax Errors: {analyzer.stats['syntax_errors']}"""
            print(stats_content)
        else:
            output = analyzer.format_analysis(results, args.format)
            
            if args.output:
                # Remove color codes for file output if terminal format
                if args.format == 'terminal':
                    clean_output = re.sub(r'\033\[[0-9;]*m', '', output)
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(clean_output)
                else:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(output)
                print(f"Analysis saved to: {args.output}")
            else:
                print(output)
    
    except FileNotFoundError as e:
        print(f"Error: File or directory not found - {e}", file=sys.stderr)
        sys.exit(1)
    except PermissionError as e:
        print(f"Error: Permission denied - {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()