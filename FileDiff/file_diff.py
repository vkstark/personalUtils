#!/usr/bin/env python3
"""
FileDiff - Advanced File Comparison Tool
A powerful side-by-side file comparison utility with colored output.

Author: Vishal Kumar
License: MIT
"""

import os
import sys
import argparse
import difflib
from pathlib import Path
from typing import List, Tuple, Optional, Union
from enum import Enum
import shutil

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
    BG_DARK_RED = '\033[101m'
    BG_DARK_GREEN = '\033[102m'

class DiffMode(Enum):
    """Different diff display modes"""
    UNIFIED = "unified"
    CONTEXT = "context"
    SIDE_BY_SIDE = "side_by_side"
    MINIMAL = "minimal"
    HTML = "html"

class FileDiff:
    """Advanced file comparison utility"""

    def __init__(self,
                 ignore_whitespace: bool = False,
                 ignore_blank_lines: bool = False,
                 ignore_case: bool = False,
                 context_lines: int = 3,
                 colors: bool = True,
                 show_line_numbers: bool = True,
                 tab_size: int = 4):

        self.ignore_whitespace = ignore_whitespace
        self.ignore_blank_lines = ignore_blank_lines
        self.ignore_case = ignore_case
        self.context_lines = context_lines
        self.colors = colors and self._supports_color()
        self.show_line_numbers = show_line_numbers
        self.tab_size = tab_size

        # Statistics
        self.stats = {
            'added_lines': 0,
            'deleted_lines': 0,
            'modified_lines': 0,
            'unchanged_lines': 0,
            'total_changes': 0
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

    def _normalize_line(self, line: str) -> str:
        """Normalize line based on comparison options"""
        if self.ignore_case:
            line = line.lower()
        if self.ignore_whitespace:
            line = ' '.join(line.split())
        return line

    def _read_file(self, filepath: str) -> List[str]:
        """Read file and return lines"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    lines = f.readlines()
            except Exception as e:
                raise Exception(f"Cannot read file {filepath}: {e}")

        # Process lines based on options
        if self.ignore_blank_lines:
            lines = [line for line in lines if line.strip()]

        return lines

    def _get_terminal_width(self) -> int:
        """Get terminal width"""
        try:
            return shutil.get_terminal_size().columns
        except:
            return 80

    def compare_files(self, file1: str, file2: str, mode: DiffMode = DiffMode.UNIFIED) -> str:
        """Compare two files and return formatted diff"""
        # Validate files
        if not os.path.exists(file1):
            raise FileNotFoundError(f"File not found: {file1}")
        if not os.path.exists(file2):
            raise FileNotFoundError(f"File not found: {file2}")

        # Read files
        lines1 = self._read_file(file1)
        lines2 = self._read_file(file2)

        # Reset statistics
        for key in self.stats:
            self.stats[key] = 0

        # Generate diff based on mode
        if mode == DiffMode.UNIFIED:
            return self._unified_diff(file1, file2, lines1, lines2)
        elif mode == DiffMode.CONTEXT:
            return self._context_diff(file1, file2, lines1, lines2)
        elif mode == DiffMode.SIDE_BY_SIDE:
            return self._side_by_side_diff(file1, file2, lines1, lines2)
        elif mode == DiffMode.MINIMAL:
            return self._minimal_diff(file1, file2, lines1, lines2)
        elif mode == DiffMode.HTML:
            return self._html_diff(file1, file2, lines1, lines2)
        else:
            raise ValueError(f"Unknown diff mode: {mode}")

    def _unified_diff(self, file1: str, file2: str, lines1: List[str], lines2: List[str]) -> str:
        """Generate unified diff format"""
        output = []

        # Header
        header = self._colorize(f"--- {file1}", Colors.BRIGHT_RED + Colors.BOLD)
        output.append(header)
        header = self._colorize(f"+++ {file2}", Colors.BRIGHT_GREEN + Colors.BOLD)
        output.append(header)
        output.append("")

        # Generate diff
        diff = difflib.unified_diff(
            lines1, lines2,
            fromfile=file1,
            tofile=file2,
            lineterm='',
            n=self.context_lines
        )

        # Skip the first two lines (file headers) as we already printed them
        diff_lines = list(diff)[2:]

        for line in diff_lines:
            if line.startswith('@@'):
                # Hunk header
                output.append(self._colorize(line, Colors.BRIGHT_CYAN + Colors.BOLD))
            elif line.startswith('+'):
                # Added line
                self.stats['added_lines'] += 1
                self.stats['total_changes'] += 1
                output.append(self._colorize(line, Colors.BRIGHT_GREEN))
            elif line.startswith('-'):
                # Deleted line
                self.stats['deleted_lines'] += 1
                self.stats['total_changes'] += 1
                output.append(self._colorize(line, Colors.BRIGHT_RED))
            else:
                # Context line
                self.stats['unchanged_lines'] += 1
                output.append(self._colorize(line, Colors.DIM))

        return '\n'.join(output)

    def _context_diff(self, file1: str, file2: str, lines1: List[str], lines2: List[str]) -> str:
        """Generate context diff format"""
        output = []

        # Header
        header = self._colorize(f"*** {file1}", Colors.BRIGHT_RED + Colors.BOLD)
        output.append(header)
        header = self._colorize(f"--- {file2}", Colors.BRIGHT_GREEN + Colors.BOLD)
        output.append(header)
        output.append("")

        # Generate diff
        diff = difflib.context_diff(
            lines1, lines2,
            fromfile=file1,
            tofile=file2,
            lineterm='',
            n=self.context_lines
        )

        # Skip the first two lines (file headers)
        diff_lines = list(diff)[2:]

        in_removed = False
        in_added = False

        for line in diff_lines:
            if line.startswith('***************'):
                # Separator
                output.append(self._colorize(line, Colors.BRIGHT_CYAN + Colors.BOLD))
                in_removed = False
                in_added = False
            elif line.startswith('***'):
                # Removed section header
                output.append(self._colorize(line, Colors.BRIGHT_RED + Colors.BOLD))
                in_removed = True
                in_added = False
            elif line.startswith('---'):
                # Added section header
                output.append(self._colorize(line, Colors.BRIGHT_GREEN + Colors.BOLD))
                in_removed = False
                in_added = True
            elif line.startswith('!'):
                # Changed line
                self.stats['modified_lines'] += 1
                self.stats['total_changes'] += 1
                if in_removed:
                    output.append(self._colorize(line, Colors.BRIGHT_RED))
                else:
                    output.append(self._colorize(line, Colors.BRIGHT_GREEN))
            elif line.startswith('- '):
                # Deleted line
                self.stats['deleted_lines'] += 1
                self.stats['total_changes'] += 1
                output.append(self._colorize(line, Colors.BRIGHT_RED))
            elif line.startswith('+ '):
                # Added line
                self.stats['added_lines'] += 1
                self.stats['total_changes'] += 1
                output.append(self._colorize(line, Colors.BRIGHT_GREEN))
            else:
                # Context line
                self.stats['unchanged_lines'] += 1
                output.append(self._colorize(line, Colors.DIM))

        return '\n'.join(output)

    def _side_by_side_diff(self, file1: str, file2: str, lines1: List[str], lines2: List[str]) -> str:
        """Generate side-by-side diff"""
        output = []

        # Get terminal width
        term_width = self._get_terminal_width()
        col_width = (term_width - 5) // 2  # 5 chars for separator and margins

        # Header
        header_line = f"{os.path.basename(file1):<{col_width}} │ {os.path.basename(file2):<{col_width}}"
        output.append(self._colorize(header_line, Colors.BRIGHT_CYAN + Colors.BOLD))
        output.append(self._colorize("─" * term_width, Colors.BRIGHT_CYAN))

        # Generate sequence matcher
        matcher = difflib.SequenceMatcher(None, lines1, lines2)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Lines are the same
                for i in range(i1, i2):
                    line1 = lines1[i].rstrip('\n')
                    line2 = lines2[j1 + (i - i1)].rstrip('\n')

                    # Truncate if needed
                    if len(line1) > col_width - 5:
                        line1 = line1[:col_width - 8] + "..."
                    if len(line2) > col_width - 5:
                        line2 = line2[:col_width - 8] + "..."

                    line_num = f"{i+1:4d} " if self.show_line_numbers else ""
                    left = f"{line_num}{line1:<{col_width - len(line_num)}}"
                    right = f"{j1 + (i - i1) + 1:4d} {line2}" if self.show_line_numbers else line2

                    output.append(self._colorize(f"{left} │ {right}", Colors.DIM))
                    self.stats['unchanged_lines'] += 1

            elif tag == 'delete':
                # Lines only in file1
                for i in range(i1, i2):
                    line = lines1[i].rstrip('\n')
                    if len(line) > col_width - 5:
                        line = line[:col_width - 8] + "..."

                    line_num = f"{i+1:4d} " if self.show_line_numbers else ""
                    left = f"{line_num}{line:<{col_width - len(line_num)}}"
                    right = " " * col_width

                    output.append(self._colorize(f"{left}", Colors.BG_DARK_RED + Colors.BRIGHT_WHITE) +
                                self._colorize(" < ", Colors.BRIGHT_RED + Colors.BOLD) +
                                " " * (col_width - 1))
                    self.stats['deleted_lines'] += 1
                    self.stats['total_changes'] += 1

            elif tag == 'insert':
                # Lines only in file2
                for j in range(j1, j2):
                    line = lines2[j].rstrip('\n')
                    if len(line) > col_width - 5:
                        line = line[:col_width - 8] + "..."

                    left = " " * col_width
                    line_num = f"{j+1:4d} " if self.show_line_numbers else ""
                    right = f"{line_num}{line}"

                    output.append(" " * col_width +
                                self._colorize(" > ", Colors.BRIGHT_GREEN + Colors.BOLD) +
                                self._colorize(f"{right}", Colors.BG_DARK_GREEN + Colors.BRIGHT_WHITE))
                    self.stats['added_lines'] += 1
                    self.stats['total_changes'] += 1

            elif tag == 'replace':
                # Lines are different
                for i in range(i1, i2):
                    line = lines1[i].rstrip('\n')
                    if len(line) > col_width - 5:
                        line = line[:col_width - 8] + "..."

                    line_num = f"{i+1:4d} " if self.show_line_numbers else ""
                    left = f"{line_num}{line:<{col_width - len(line_num)}}"

                    output.append(self._colorize(f"{left}", Colors.BG_DARK_RED + Colors.BRIGHT_WHITE) +
                                self._colorize(" ≠ ", Colors.BRIGHT_YELLOW + Colors.BOLD) +
                                " " * (col_width - 1))

                for j in range(j1, j2):
                    line = lines2[j].rstrip('\n')
                    if len(line) > col_width - 5:
                        line = line[:col_width - 8] + "..."

                    left = " " * col_width
                    line_num = f"{j+1:4d} " if self.show_line_numbers else ""
                    right = f"{line_num}{line}"

                    output.append(" " * col_width +
                                self._colorize(" ≠ ", Colors.BRIGHT_YELLOW + Colors.BOLD) +
                                self._colorize(f"{right}", Colors.BG_DARK_GREEN + Colors.BRIGHT_WHITE))

                self.stats['modified_lines'] += max(i2 - i1, j2 - j1)
                self.stats['total_changes'] += max(i2 - i1, j2 - j1)

        return '\n'.join(output)

    def _minimal_diff(self, file1: str, file2: str, lines1: List[str], lines2: List[str]) -> str:
        """Generate minimal diff showing only changes"""
        output = []

        # Generate sequence matcher
        matcher = difflib.SequenceMatcher(None, lines1, lines2)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                self.stats['unchanged_lines'] += (i2 - i1)
                continue

            # Show line range
            range_info = f"Lines {i1+1}-{i2} → {j1+1}-{j2}"
            output.append(self._colorize(f"\n{range_info}", Colors.BRIGHT_CYAN + Colors.BOLD))
            output.append(self._colorize("─" * len(range_info), Colors.BRIGHT_CYAN))

            if tag == 'delete':
                for i in range(i1, i2):
                    line = lines1[i].rstrip('\n')
                    output.append(self._colorize(f"- {line}", Colors.BRIGHT_RED))
                    self.stats['deleted_lines'] += 1
                    self.stats['total_changes'] += 1

            elif tag == 'insert':
                for j in range(j1, j2):
                    line = lines2[j].rstrip('\n')
                    output.append(self._colorize(f"+ {line}", Colors.BRIGHT_GREEN))
                    self.stats['added_lines'] += 1
                    self.stats['total_changes'] += 1

            elif tag == 'replace':
                for i in range(i1, i2):
                    line = lines1[i].rstrip('\n')
                    output.append(self._colorize(f"- {line}", Colors.BRIGHT_RED))
                for j in range(j1, j2):
                    line = lines2[j].rstrip('\n')
                    output.append(self._colorize(f"+ {line}", Colors.BRIGHT_GREEN))
                self.stats['modified_lines'] += max(i2 - i1, j2 - j1)
                self.stats['total_changes'] += max(i2 - i1, j2 - j1)

        return '\n'.join(output)

    def _html_diff(self, file1: str, file2: str, lines1: List[str], lines2: List[str]) -> str:
        """Generate HTML diff"""
        differ = difflib.HtmlDiff(
            tabsize=self.tab_size,
            wrapcolumn=80
        )

        html = differ.make_file(
            lines1, lines2,
            fromdesc=file1,
            todesc=file2,
            context=True,
            numlines=self.context_lines
        )

        # Count changes for stats
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, lines1, lines2).get_opcodes():
            if tag == 'equal':
                self.stats['unchanged_lines'] += (i2 - i1)
            elif tag == 'delete':
                self.stats['deleted_lines'] += (i2 - i1)
                self.stats['total_changes'] += (i2 - i1)
            elif tag == 'insert':
                self.stats['added_lines'] += (j2 - j1)
                self.stats['total_changes'] += (j2 - j1)
            elif tag == 'replace':
                self.stats['modified_lines'] += max(i2 - i1, j2 - j1)
                self.stats['total_changes'] += max(i2 - i1, j2 - j1)

        return html

    def get_statistics(self) -> str:
        """Get formatted statistics"""
        output = []
        output.append(self._colorize("\n📊 Comparison Statistics", Colors.BRIGHT_CYAN + Colors.BOLD))
        output.append(self._colorize("─" * 30, Colors.BRIGHT_CYAN))

        output.append(f"{self._colorize('Added lines:', Colors.GREEN)} {self.stats['added_lines']}")
        output.append(f"{self._colorize('Deleted lines:', Colors.RED)} {self.stats['deleted_lines']}")
        output.append(f"{self._colorize('Modified lines:', Colors.YELLOW)} {self.stats['modified_lines']}")
        output.append(f"{self._colorize('Unchanged lines:', Colors.DIM)} {self.stats['unchanged_lines']}")
        output.append(f"{self._colorize('Total changes:', Colors.BRIGHT_WHITE + Colors.BOLD)} {self.stats['total_changes']}")

        return '\n'.join(output)

    def are_files_identical(self, file1: str, file2: str) -> bool:
        """Check if two files are identical"""
        lines1 = self._read_file(file1)
        lines2 = self._read_file(file2)

        if self.ignore_whitespace or self.ignore_case:
            lines1 = [self._normalize_line(line) for line in lines1]
            lines2 = [self._normalize_line(line) for line in lines2]

        return lines1 == lines2

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="FileDiff - Advanced File Comparison Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s file1.txt file2.txt                    # Unified diff
  %(prog)s -m side_by_side file1.py file2.py      # Side-by-side comparison
  %(prog)s -m minimal old.json new.json           # Show only changes
  %(prog)s -w -b file1.txt file2.txt              # Ignore whitespace and blank lines
  %(prog)s -m html -o diff.html file1.py file2.py # HTML output
  %(prog)s --check file1.txt file2.txt            # Check if files are identical
        """)

    parser.add_argument('file1', help='First file to compare')
    parser.add_argument('file2', help='Second file to compare')

    # Diff mode
    parser.add_argument('-m', '--mode',
                       choices=['unified', 'context', 'side_by_side', 'minimal', 'html'],
                       default='unified',
                       help='Diff display mode (default: unified)')

    # Comparison options
    parser.add_argument('-w', '--ignore-whitespace', action='store_true',
                       help='Ignore whitespace differences')
    parser.add_argument('-b', '--ignore-blank-lines', action='store_true',
                       help='Ignore blank lines')
    parser.add_argument('-i', '--ignore-case', action='store_true',
                       help='Ignore case differences')
    parser.add_argument('-c', '--context', type=int, default=3, metavar='N',
                       help='Number of context lines (default: 3)')

    # Display options
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')
    parser.add_argument('--no-line-numbers', action='store_true',
                       help='Hide line numbers')
    parser.add_argument('--tab-size', type=int, default=4, metavar='N',
                       help='Tab size for display (default: 4)')

    # Output options
    parser.add_argument('-o', '--output', metavar='FILE',
                       help='Save output to file')
    parser.add_argument('-s', '--stats', action='store_true',
                       help='Show statistics')
    parser.add_argument('--check', action='store_true',
                       help='Only check if files are identical (exit 0 if same, 1 if different)')

    # Version
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')

    args = parser.parse_args()

    try:
        # Create differ
        differ = FileDiff(
            ignore_whitespace=args.ignore_whitespace,
            ignore_blank_lines=args.ignore_blank_lines,
            ignore_case=args.ignore_case,
            context_lines=args.context,
            colors=not args.no_color,
            show_line_numbers=not args.no_line_numbers,
            tab_size=args.tab_size
        )

        # Check mode
        if args.check:
            identical = differ.are_files_identical(args.file1, args.file2)
            if identical:
                print(f"{differ._colorize('✓', Colors.BRIGHT_GREEN)} Files are identical")
                sys.exit(0)
            else:
                print(f"{differ._colorize('✗', Colors.BRIGHT_RED)} Files are different")
                sys.exit(1)

        # Map mode string to enum
        mode_map = {
            'unified': DiffMode.UNIFIED,
            'context': DiffMode.CONTEXT,
            'side_by_side': DiffMode.SIDE_BY_SIDE,
            'minimal': DiffMode.MINIMAL,
            'html': DiffMode.HTML
        }
        mode = mode_map[args.mode]

        # Generate diff
        diff_output = differ.compare_files(args.file1, args.file2, mode)

        # Add statistics if requested
        if args.stats and args.mode != 'html':
            diff_output += "\n" + differ.get_statistics()

        # Output
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                # Remove color codes for file output
                import re
                clean_output = re.sub(r'\033\[[0-9;]*m', '', diff_output)
                f.write(clean_output)
            print(f"Diff saved to: {args.output}")
        else:
            print(diff_output)

        # Exit with appropriate code
        if differ.stats['total_changes'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == '__main__':
    main()
