#!/usr/bin/env python3
"""
TodoExtractor - Extract TODO/FIXME/HACK Comments
Find and organize all TODO, FIXME, HACK, and other task comments in your codebase.

Author: Vishal Kumar
License: MIT
"""

import os
import sys
import argparse
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict
from datetime import datetime

# Color codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'

    # Text colors
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
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'

class TodoItem:
    """Represents a single TODO/FIXME/etc comment"""

    def __init__(self, tag: str, text: str, filepath: str, line_num: int,
                 priority: int = 0, author: Optional[str] = None):
        self.tag = tag
        self.text = text.strip()
        self.filepath = filepath
        self.line_num = line_num
        self.priority = priority
        self.author = author

    def __repr__(self):
        return f"TodoItem({self.tag}, {self.filepath}:{self.line_num})"

class TodoExtractor:
    """Extract and organize TODO comments from codebase"""

    # Default tags to search for with their priorities (higher = more urgent)
    DEFAULT_TAGS = {
        'FIXME': 3,
        'BUG': 3,
        'XXX': 3,
        'HACK': 2,
        'TODO': 1,
        'NOTE': 0,
        'OPTIMIZE': 1,
        'REFACTOR': 1,
        'REVIEW': 1,
        'DEPRECATED': 2
    }

    # File extensions to search by default
    DEFAULT_EXTENSIONS = [
        '.py', '.js', '.ts', '.jsx', '.tsx',
        '.java', '.c', '.cpp', '.h', '.hpp',
        '.go', '.rs', '.rb', '.php',
        '.sh', '.bash', '.zsh',
        '.css', '.scss', '.sass', '.less',
        '.html', '.xml', '.md', '.txt',
        '.yaml', '.yml', '.json', '.toml'
    ]

    def __init__(self,
                 tags: Optional[Dict[str, int]] = None,
                 extensions: Optional[List[str]] = None,
                 exclude_dirs: Optional[List[str]] = None,
                 recursive: bool = True,
                 case_sensitive: bool = False,
                 colors: bool = True,
                 verbose: bool = False):

        self.tags = tags or self.DEFAULT_TAGS
        self.extensions = extensions or self.DEFAULT_EXTENSIONS
        self.exclude_dirs = exclude_dirs or [
            '.git', 'node_modules', '__pycache__', '.venv', 'venv',
            'dist', 'build', '.next', '.nuxt', 'target'
        ]
        self.recursive = recursive
        self.case_sensitive = case_sensitive
        self.colors = colors and self._supports_color()
        self.verbose = verbose

        # Results storage
        self.todos = []
        self.stats = {
            'files_scanned': 0,
            'total_todos': 0,
            'by_tag': defaultdict(int),
            'by_file': defaultdict(int)
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

    def _should_skip_dir(self, dirpath: str) -> bool:
        """Check if directory should be skipped"""
        dir_name = os.path.basename(dirpath)
        return dir_name in self.exclude_dirs or dir_name.startswith('.')

    def _should_scan_file(self, filepath: str) -> bool:
        """Check if file should be scanned"""
        ext = os.path.splitext(filepath)[1]
        return ext in self.extensions

    def _extract_todos_from_line(self, line: str, line_num: int, filepath: str) -> List[TodoItem]:
        """Extract TODO items from a single line"""
        todos = []

        # Build regex pattern for all tags
        tag_pattern = '|'.join(re.escape(tag) for tag in self.tags.keys())

        if self.case_sensitive:
            pattern = r'\b(' + tag_pattern + r')\b:?\s*(.+?)(?:\s*\*\/|$)'
        else:
            pattern = r'\b(' + tag_pattern + r')\b:?\s*(.+?)(?:\s*\*\/|$)'
            pattern = re.compile(pattern, re.IGNORECASE)

        # Search for tags in the line
        for match in re.finditer(pattern, line) if isinstance(pattern, re.Pattern) else re.finditer(pattern, line, re.IGNORECASE):
            tag = match.group(1).upper()
            text = match.group(2).strip()

            # Extract author if present (e.g., TODO(john): fix this)
            author = None
            author_match = re.search(r'\(([^)]+)\)', text)
            if author_match:
                author = author_match.group(1)
                text = text.replace(author_match.group(0), '').strip()
                if text.startswith(':'):
                    text = text[1:].strip()

            # Extract priority if present (e.g., TODO[P1]: high priority)
            priority = self.tags.get(tag, 0)
            priority_match = re.search(r'\[P([0-9])\]', text)
            if priority_match:
                priority = int(priority_match.group(1))
                text = text.replace(priority_match.group(0), '').strip()
                if text.startswith(':'):
                    text = text[1:].strip()

            if text:  # Only add if there's actual text
                todo = TodoItem(tag, text, filepath, line_num, priority, author)
                todos.append(todo)

        return todos

    def scan_file(self, filepath: str) -> List[TodoItem]:
        """Scan a single file for TODO comments"""
        todos = []

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    extracted = self._extract_todos_from_line(line, line_num, filepath)
                    todos.extend(extracted)

            if todos and self.verbose:
                print(f"  Found {len(todos)} item(s) in {filepath}")

        except Exception as e:
            if self.verbose:
                print(f"  Error scanning {filepath}: {e}", file=sys.stderr)

        return todos

    def scan_directory(self, directory: str) -> List[TodoItem]:
        """Scan directory for TODO comments"""
        directory = Path(directory).resolve()

        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory}")

        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        print(self._colorize(f"Scanning: {directory}", Colors.CYAN))

        all_todos = []

        if self.recursive:
            for root, dirs, files in os.walk(directory):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if not self._should_skip_dir(os.path.join(root, d))]

                for filename in files:
                    filepath = os.path.join(root, filename)

                    if self._should_scan_file(filepath):
                        self.stats['files_scanned'] += 1
                        todos = self.scan_file(filepath)
                        all_todos.extend(todos)
        else:
            for item in directory.iterdir():
                if item.is_file() and self._should_scan_file(str(item)):
                    self.stats['files_scanned'] += 1
                    todos = self.scan_file(str(item))
                    all_todos.extend(todos)

        return all_todos

    def extract(self, path: str):
        """Extract TODOs from path (file or directory)"""
        path_obj = Path(path)

        if path_obj.is_file():
            self.stats['files_scanned'] = 1
            self.todos = self.scan_file(str(path_obj))
        elif path_obj.is_dir():
            self.todos = self.scan_directory(str(path_obj))
        else:
            raise ValueError(f"Path does not exist: {path}")

        # Update statistics
        self.stats['total_todos'] = len(self.todos)
        for todo in self.todos:
            self.stats['by_tag'][todo.tag] += 1
            self.stats['by_file'][todo.filepath] += 1

    def get_summary(self) -> str:
        """Get summary of found TODOs"""
        output = []

        output.append(self._colorize("\n" + "=" * 60, Colors.BRIGHT_CYAN))
        output.append(self._colorize("TODO/FIXME Summary", Colors.BRIGHT_CYAN + Colors.BOLD))
        output.append(self._colorize("=" * 60, Colors.BRIGHT_CYAN))

        output.append(f"\nFiles Scanned: {self._colorize(str(self.stats['files_scanned']), Colors.GREEN)}")
        output.append(f"Total Items: {self._colorize(str(self.stats['total_todos']), Colors.YELLOW)}")

        if self.stats['by_tag']:
            output.append(f"\n{self._colorize('By Tag:', Colors.BRIGHT_YELLOW)}")
            for tag, count in sorted(self.stats['by_tag'].items(), key=lambda x: -x[1]):
                color = self._get_tag_color(tag)
                output.append(f"  {self._colorize(tag, color)}: {count}")

        return '\n'.join(output)

    def _get_tag_color(self, tag: str) -> str:
        """Get color for tag based on priority"""
        priority = self.tags.get(tag, 0)
        if priority >= 3:
            return Colors.BRIGHT_RED
        elif priority == 2:
            return Colors.BRIGHT_YELLOW
        elif priority == 1:
            return Colors.BRIGHT_CYAN
        else:
            return Colors.DIM

    def get_detailed_report(self, group_by: str = 'file', show_line_numbers: bool = True) -> str:
        """Get detailed report of all TODOs"""
        output = []

        if group_by == 'file':
            output.append(f"\n{self._colorize('TODOs by File:', Colors.BRIGHT_MAGENTA + Colors.BOLD)}")
            output.append(self._colorize("-" * 60, Colors.BRIGHT_MAGENTA))

            grouped = defaultdict(list)
            for todo in self.todos:
                grouped[todo.filepath].append(todo)

            for filepath in sorted(grouped.keys()):
                items = grouped[filepath]
                output.append(f"\n{self._colorize(filepath, Colors.BRIGHT_BLUE)} ({len(items)} items)")

                for todo in sorted(items, key=lambda x: x.line_num):
                    self._format_todo_item(todo, output, show_line_numbers)

        elif group_by == 'tag':
            output.append(f"\n{self._colorize('TODOs by Tag:', Colors.BRIGHT_MAGENTA + Colors.BOLD)}")
            output.append(self._colorize("-" * 60, Colors.BRIGHT_MAGENTA))

            grouped = defaultdict(list)
            for todo in self.todos:
                grouped[todo.tag].append(todo)

            # Sort by priority (highest first)
            for tag in sorted(grouped.keys(), key=lambda x: -self.tags.get(x, 0)):
                items = grouped[tag]
                color = self._get_tag_color(tag)
                output.append(f"\n{self._colorize(tag, color + Colors.BOLD)} ({len(items)} items)")

                for todo in sorted(items, key=lambda x: (x.filepath, x.line_num)):
                    self._format_todo_item(todo, output, show_line_numbers)

        elif group_by == 'priority':
            output.append(f"\n{self._colorize('TODOs by Priority:', Colors.BRIGHT_MAGENTA + Colors.BOLD)}")
            output.append(self._colorize("-" * 60, Colors.BRIGHT_MAGENTA))

            grouped = defaultdict(list)
            for todo in self.todos:
                grouped[todo.priority].append(todo)

            for priority in sorted(grouped.keys(), reverse=True):
                items = grouped[priority]
                priority_label = f"Priority {priority}"
                color = Colors.BRIGHT_RED if priority >= 3 else (Colors.BRIGHT_YELLOW if priority == 2 else Colors.CYAN)
                output.append(f"\n{self._colorize(priority_label, color + Colors.BOLD)} ({len(items)} items)")

                for todo in sorted(items, key=lambda x: (x.filepath, x.line_num)):
                    self._format_todo_item(todo, output, show_line_numbers)

        return '\n'.join(output)

    def _format_todo_item(self, todo: TodoItem, output: List[str], show_line_numbers: bool):
        """Format a single TODO item for display"""
        tag_color = self._get_tag_color(todo.tag)

        # Build location string
        if show_line_numbers:
            location = f"  {todo.filepath}:{self._colorize(str(todo.line_num), Colors.DIM)}"
        else:
            location = f"  {todo.filepath}"

        # Build tag with author if present
        tag_str = self._colorize(f"[{todo.tag}]", tag_color)
        if todo.author:
            tag_str += self._colorize(f"({todo.author})", Colors.CYAN)

        # Add priority indicator if high
        if todo.priority >= 2:
            tag_str += self._colorize(f" [P{todo.priority}]", Colors.YELLOW)

        output.append(f"  {tag_str} {todo.text}")
        if show_line_numbers:
            output.append(f"    {self._colorize('→', Colors.DIM)} {todo.filepath}:{todo.line_num}")

    def export_json(self, filepath: str):
        """Export TODOs to JSON"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'stats': dict(self.stats),
            'todos': [
                {
                    'tag': todo.tag,
                    'text': todo.text,
                    'file': todo.filepath,
                    'line': todo.line_num,
                    'priority': todo.priority,
                    'author': todo.author
                }
                for todo in self.todos
            ]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        print(f"\n{self._colorize('✓', Colors.GREEN)} Exported to: {filepath}")

    def export_markdown(self, filepath: str):
        """Export TODOs to Markdown"""
        output = []

        output.append(f"# TODO Report")
        output.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"\n## Summary")
        output.append(f"\n- Files Scanned: {self.stats['files_scanned']}")
        output.append(f"- Total Items: {self.stats['total_todos']}")

        if self.stats['by_tag']:
            output.append(f"\n### By Tag")
            for tag, count in sorted(self.stats['by_tag'].items(), key=lambda x: -x[1]):
                output.append(f"- **{tag}**: {count}")

        # Group by tag for markdown
        output.append(f"\n## Detailed List")
        grouped = defaultdict(list)
        for todo in self.todos:
            grouped[todo.tag].append(todo)

        for tag in sorted(grouped.keys(), key=lambda x: -self.tags.get(x, 0)):
            items = grouped[tag]
            output.append(f"\n### {tag} ({len(items)})")

            for todo in sorted(items, key=lambda x: (x.filepath, x.line_num)):
                author_str = f" *by {todo.author}*" if todo.author else ""
                priority_str = f" `[P{todo.priority}]`" if todo.priority >= 2 else ""
                output.append(f"\n- **{todo.text}**{author_str}{priority_str}")
                output.append(f"  - `{todo.filepath}:{todo.line_num}`")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output))

        print(f"\n{self._colorize('✓', Colors.GREEN)} Exported to: {filepath}")

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="TodoExtractor - Extract TODO/FIXME/HACK Comments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Default Tags (with priorities):
  FIXME, BUG, XXX     [Priority 3 - Urgent]
  HACK, DEPRECATED    [Priority 2 - Important]
  TODO, OPTIMIZE, REFACTOR, REVIEW [Priority 1 - Normal]
  NOTE                [Priority 0 - Info]

Examples:
  # Scan current directory
  %(prog)s .

  # Scan specific directory recursively
  %(prog)s /path/to/project

  # Scan single file
  %(prog)s script.py

  # Group by tag instead of file
  %(prog)s . --group-by tag

  # Show only high-priority items
  %(prog)s . --group-by priority

  # Export to JSON
  %(prog)s . --export-json todos.json

  # Export to Markdown
  %(prog)s . --export-md TODO.md

  # Custom tags
  %(prog)s . --tags FIXME TODO HACK

  # Include specific extensions only
  %(prog)s . --extensions .py .js .ts
        """)

    parser.add_argument('path', nargs='?', default='.',
                       help='File or directory to scan (default: current directory)')

    # Scanning options
    parser.add_argument('--tags', nargs='+',
                       help='Tags to search for (default: TODO, FIXME, HACK, etc.)')
    parser.add_argument('--extensions', nargs='+',
                       help='File extensions to scan (default: common code files)')
    parser.add_argument('--exclude-dirs', nargs='+',
                       help='Additional directories to exclude')
    parser.add_argument('--no-recursive', action='store_true',
                       help='Do not scan subdirectories')
    parser.add_argument('--case-sensitive', action='store_true',
                       help='Case-sensitive tag matching')

    # Display options
    parser.add_argument('--group-by', choices=['file', 'tag', 'priority'],
                       default='file',
                       help='Group results by (default: file)')
    parser.add_argument('--no-line-numbers', action='store_true',
                       help='Hide line numbers in output')
    parser.add_argument('--summary-only', action='store_true',
                       help='Show only summary statistics')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')

    # Export options
    parser.add_argument('--export-json', metavar='FILE',
                       help='Export results to JSON file')
    parser.add_argument('--export-md', metavar='FILE',
                       help='Export results to Markdown file')

    # Version
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')

    args = parser.parse_args()

    try:
        # Prepare tags dict
        tags_dict = None
        if args.tags:
            tags_dict = {tag.upper(): 1 for tag in args.tags}

        # Create extractor
        extractor = TodoExtractor(
            tags=tags_dict,
            extensions=args.extensions,
            exclude_dirs=args.exclude_dirs,
            recursive=not args.no_recursive,
            case_sensitive=args.case_sensitive,
            colors=not args.no_color,
            verbose=args.verbose
        )

        # Extract TODOs
        extractor.extract(args.path)

        # Show results
        print(extractor.get_summary())

        if not args.summary_only:
            print(extractor.get_detailed_report(
                group_by=args.group_by,
                show_line_numbers=not args.no_line_numbers
            ))

        # Export if requested
        if args.export_json:
            extractor.export_json(args.export_json)

        if args.export_md:
            extractor.export_markdown(args.export_md)

        print()  # Final newline

        # Exit with code 1 if TODOs found (for CI/CD)
        sys.exit(1 if extractor.stats['total_todos'] > 0 else 0)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
