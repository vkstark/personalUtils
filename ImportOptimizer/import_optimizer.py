#!/usr/bin/env python3
"""
ImportOptimizer - Python Import Optimizer
Find unused imports, circular dependencies, and organize import statements.

Author: Vishal Kumar
License: MIT
"""

import os
import sys
import argparse
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

# Color codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'

    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_CYAN = '\033[96m'

class ImportAnalyzer:
    """Analyze Python imports"""

    def __init__(self, colors: bool = True, verbose: bool = False):
        self.colors = colors and self._supports_color()
        self.verbose = verbose

    def _supports_color(self) -> bool:
        """Check if terminal supports color output"""
        return (hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
                os.getenv('TERM') != 'dumb')

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text"""
        if not self.colors:
            return text
        return f"{color}{text}{Colors.RESET}"

    def analyze_file(self, filepath: str) -> Dict:
        """Analyze imports in a Python file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
        except Exception as e:
            return {'error': str(e)}

        try:
            tree = ast.parse(source, filepath)
        except SyntaxError as e:
            return {'error': f"Syntax error: {e}"}

        imports = []
        used_names = set()

        # Collect imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'type': 'import',
                        'module': alias.name,
                        'name': alias.asname or alias.name,
                        'line': node.lineno
                    })

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append({
                        'type': 'from',
                        'module': module,
                        'name': alias.asname or alias.name,
                        'imported': alias.name,
                        'line': node.lineno
                    })

            # Collect used names
            elif isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Handle module.function calls
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

        # Find unused imports
        unused = []
        for imp in imports:
            name = imp['name']
            # Skip special imports
            if name.startswith('_') or name in ('*',):
                continue
            if name not in used_names:
                unused.append(imp)

        return {
            'imports': imports,
            'unused': unused,
            'used_names': used_names
        }

    def find_unused_in_directory(self, directory: str, recursive: bool = True) -> Dict[str, List]:
        """Find unused imports in directory"""
        directory = Path(directory)
        results = {}

        pattern = '**/*.py' if recursive else '*.py'

        for filepath in directory.glob(pattern):
            if filepath.is_file():
                analysis = self.analyze_file(str(filepath))
                if 'error' not in analysis and analysis.get('unused'):
                    results[str(filepath)] = analysis['unused']

        return results

    def organize_imports(self, filepath: str) -> Tuple[List[str], List[str], List[str]]:
        """Organize imports into stdlib, third-party, and local"""
        analysis = self.analyze_file(filepath)

        if 'error' in analysis:
            return [], [], []

        stdlib = []
        third_party = []
        local = []

        # Common stdlib modules (simplified list)
        STDLIB_MODULES = {
            'os', 'sys', 're', 'json', 'time', 'datetime', 'collections',
            'itertools', 'functools', 'pathlib', 'typing', 'io', 'math',
            'random', 'string', 'copy', 'pickle', 'subprocess', 'shutil',
            'glob', 'fnmatch', 'argparse', 'logging', 'unittest', 'csv',
            'xml', 'html', 'http', 'urllib', 'hashlib', 'base64', 'tempfile'
        }

        for imp in analysis['imports']:
            module = imp['module'].split('.')[0]

            if module in STDLIB_MODULES:
                stdlib.append(imp)
            elif module.startswith('.'):
                local.append(imp)
            else:
                third_party.append(imp)

        return stdlib, third_party, local

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="ImportOptimizer - Python Import Optimizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find unused imports in file
  %(prog)s unused script.py

  # Find unused in directory
  %(prog)s unused /path/to/project -r

  # Organize imports
  %(prog)s organize script.py

  # Check all Python files
  %(prog)s unused . -r
        """)

    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    subparsers = parser.add_subparsers(dest='command')

    # Unused command
    unused_parser = subparsers.add_parser('unused', help='Find unused imports')
    unused_parser.add_argument('path', help='File or directory to analyze')
    unused_parser.add_argument('-r', '--recursive', action='store_true', help='Recursive')

    # Organize command
    organize_parser = subparsers.add_parser('organize', help='Show organized imports')
    organize_parser.add_argument('file', help='Python file to organize')

    # Version
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        analyzer = ImportAnalyzer(colors=not args.no_color, verbose=args.verbose)

        if args.command == 'unused':
            path = Path(args.path)

            if path.is_file():
                analysis = analyzer.analyze_file(str(path))
                if 'error' in analysis:
                    print(f"Error: {analysis['error']}", file=sys.stderr)
                    sys.exit(1)

                if analysis['unused']:
                    print(f"\n{analyzer._colorize('Unused imports:', Colors.BRIGHT_YELLOW + Colors.BOLD)}")
                    for imp in analysis['unused']:
                        line_info = analyzer._colorize(f"line {imp['line']}", Colors.DIM)
                        print(f"  {imp['name']} ({line_info})")
                else:
                    print(analyzer._colorize("✓ No unused imports found", Colors.GREEN))

            elif path.is_dir():
                results = analyzer.find_unused_in_directory(str(path), args.recursive)

                if results:
                    print(f"\n{analyzer._colorize(f'Found unused imports in {len(results)} file(s):', Colors.BRIGHT_YELLOW + Colors.BOLD)}\n")

                    for filepath, unused in results.items():
                        print(analyzer._colorize(filepath, Colors.CYAN))
                        for imp in unused:
                            line_info = analyzer._colorize(f"line {imp['line']}", Colors.DIM)
                            print(f"  - {imp['name']} ({line_info})")
                        print()
                else:
                    print(analyzer._colorize("✓ No unused imports found", Colors.GREEN))

        elif args.command == 'organize':
            stdlib, third_party, local = analyzer.organize_imports(args.file)

            print(f"\n{analyzer._colorize('Organized Imports:', Colors.BRIGHT_CYAN + Colors.BOLD)}\n")

            if stdlib:
                print(analyzer._colorize("# Standard library", Colors.GREEN))
                for imp in sorted(stdlib, key=lambda x: x['module']):
                    if imp['type'] == 'import':
                        print(f"import {imp['module']}")
                    else:
                        print(f"from {imp['module']} import {imp['imported']}")
                print()

            if third_party:
                print(analyzer._colorize("# Third-party", Colors.YELLOW))
                for imp in sorted(third_party, key=lambda x: x['module']):
                    if imp['type'] == 'import':
                        print(f"import {imp['module']}")
                    else:
                        print(f"from {imp['module']} import {imp['imported']}")
                print()

            if local:
                print(analyzer._colorize("# Local", Colors.BLUE))
                for imp in sorted(local, key=lambda x: x['module']):
                    if imp['type'] == 'import':
                        print(f"import {imp['module']}")
                    else:
                        print(f"from {imp['module']} import {imp['imported']}")

    except KeyboardInterrupt:
        print("\n\nCancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
