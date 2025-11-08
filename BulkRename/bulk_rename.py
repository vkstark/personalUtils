#!/usr/bin/env python3
"""
BulkRename - Batch File Renaming Utility
A powerful tool for renaming multiple files with regex, patterns, and undo support.

Author: Vishal Kumar
License: MIT
"""

import os
import sys
import argparse
import re
import json
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime
from enum import Enum

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

class RenameMode(Enum):
    """Different renaming modes"""
    REPLACE = "replace"
    REGEX = "regex"
    SEQUENTIAL = "sequential"
    CASE = "case"
    PREFIX = "prefix"
    SUFFIX = "suffix"
    EXTENSION = "extension"
    REMOVE = "remove"

class BulkRename:
    """Batch file renaming utility"""

    def __init__(self,
                 dry_run: bool = False,
                 interactive: bool = False,
                 recursive: bool = False,
                 include_dirs: bool = False,
                 backup: bool = True,
                 colors: bool = True,
                 verbose: bool = False):

        self.dry_run = dry_run
        self.interactive = interactive
        self.recursive = recursive
        self.include_dirs = include_dirs
        self.backup = backup
        self.colors = colors and self._supports_color()
        self.verbose = verbose

        # History for undo
        self.history_file = Path.home() / '.bulk_rename_history.json'
        self.current_operation = []

        # Statistics
        self.stats = {
            'total_files': 0,
            'renamed': 0,
            'skipped': 0,
            'errors': 0
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

    def _get_files(self, path: str, pattern: Optional[str] = None) -> List[Path]:
        """Get list of files to rename"""
        path_obj = Path(path)

        if path_obj.is_file():
            return [path_obj]

        files = []
        if self.recursive:
            if pattern:
                files = list(path_obj.rglob(pattern))
            else:
                files = list(path_obj.rglob('*'))
        else:
            if pattern:
                files = list(path_obj.glob(pattern))
            else:
                files = list(path_obj.glob('*'))

        # Filter based on options
        result = []
        for f in files:
            if f.is_file():
                result.append(f)
            elif f.is_dir() and self.include_dirs:
                result.append(f)

        return sorted(result)

    def _generate_new_name(self, filepath: Path, mode: RenameMode, **kwargs) -> Optional[str]:
        """Generate new filename based on mode"""
        old_name = filepath.name
        stem = filepath.stem
        ext = filepath.suffix

        try:
            if mode == RenameMode.REPLACE:
                # Simple string replacement
                find = kwargs.get('find', '')
                replace = kwargs.get('replace', '')
                new_name = old_name.replace(find, replace)

            elif mode == RenameMode.REGEX:
                # Regex replacement
                pattern = kwargs.get('pattern', '')
                replace = kwargs.get('replace', '')
                new_name = re.sub(pattern, replace, old_name)

            elif mode == RenameMode.SEQUENTIAL:
                # Sequential numbering
                index = kwargs.get('index', 0)
                template = kwargs.get('template', '{name}_{n}')
                digits = kwargs.get('digits', 3)
                start = kwargs.get('start', 1)

                number = start + index
                new_name = template.format(
                    name=stem,
                    n=str(number).zfill(digits),
                    ext=ext.lstrip('.')
                )
                if ext and '{ext}' not in template:
                    new_name += ext

            elif mode == RenameMode.CASE:
                # Change case
                case_type = kwargs.get('case', 'lower')
                if case_type == 'lower':
                    new_name = old_name.lower()
                elif case_type == 'upper':
                    new_name = old_name.upper()
                elif case_type == 'title':
                    new_name = old_name.title()
                elif case_type == 'capitalize':
                    new_name = old_name.capitalize()
                else:
                    new_name = old_name

            elif mode == RenameMode.PREFIX:
                # Add prefix
                prefix = kwargs.get('prefix', '')
                new_name = prefix + old_name

            elif mode == RenameMode.SUFFIX:
                # Add suffix (before extension)
                suffix = kwargs.get('suffix', '')
                new_name = stem + suffix + ext

            elif mode == RenameMode.EXTENSION:
                # Change extension
                new_ext = kwargs.get('extension', '')
                if not new_ext.startswith('.'):
                    new_ext = '.' + new_ext
                new_name = stem + new_ext

            elif mode == RenameMode.REMOVE:
                # Remove pattern
                pattern = kwargs.get('pattern', '')
                new_name = old_name.replace(pattern, '')

            else:
                return None

            # Validate new name
            if not new_name or new_name == old_name:
                return None

            # Check for invalid characters
            invalid_chars = '<>:"|?*'
            if any(char in new_name for char in invalid_chars):
                if self.verbose:
                    print(f"Warning: Invalid characters in new name: {new_name}")
                return None

            return new_name

        except Exception as e:
            if self.verbose:
                print(f"Error generating new name for {old_name}: {e}")
            return None

    def _rename_file(self, old_path: Path, new_name: str) -> Tuple[bool, str]:
        """Rename a single file"""
        new_path = old_path.parent / new_name

        # Check if target already exists
        if new_path.exists() and new_path != old_path:
            return False, f"Target already exists: {new_name}"

        try:
            if not self.dry_run:
                old_path.rename(new_path)
                self.current_operation.append({
                    'old': str(old_path),
                    'new': str(new_path),
                    'timestamp': datetime.now().isoformat()
                })
            return True, ""
        except Exception as e:
            return False, str(e)

    def rename(self, path: str, mode: RenameMode, pattern: Optional[str] = None, **kwargs) -> int:
        """Perform bulk rename operation"""
        # Reset statistics
        for key in self.stats:
            self.stats[key] = 0
        self.current_operation = []

        # Get files
        files = self._get_files(path, pattern)
        self.stats['total_files'] = len(files)

        if not files:
            print(self._colorize("No files found to rename", Colors.YELLOW))
            return 0

        # Generate rename plan
        rename_plan = []
        for i, filepath in enumerate(files):
            kwargs['index'] = i
            new_name = self._generate_new_name(filepath, mode, **kwargs)

            if new_name and new_name != filepath.name:
                rename_plan.append((filepath, new_name))

        if not rename_plan:
            print(self._colorize("No files need to be renamed", Colors.YELLOW))
            return 0

        # Show preview
        self._show_preview(rename_plan)

        # Confirm if interactive
        if self.interactive and not self.dry_run:
            response = input(f"\n{self._colorize('Proceed with rename?', Colors.BRIGHT_YELLOW)} (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print(self._colorize("Operation cancelled", Colors.YELLOW))
                return 0

        # Perform renames
        print(f"\n{self._colorize('Renaming files...', Colors.BRIGHT_CYAN + Colors.BOLD)}")

        for old_path, new_name in rename_plan:
            success, error = self._rename_file(old_path, new_name)

            if success:
                self.stats['renamed'] += 1
                status = self._colorize("✓", Colors.BRIGHT_GREEN)
                if self.verbose or self.dry_run:
                    print(f"{status} {old_path.name} → {self._colorize(new_name, Colors.GREEN)}")
            else:
                self.stats['errors'] += 1
                status = self._colorize("✗", Colors.BRIGHT_RED)
                print(f"{status} {old_path.name} - {self._colorize(error, Colors.RED)}")

        # Save history
        if not self.dry_run and self.backup and self.current_operation:
            self._save_history()

        # Show statistics
        self._show_statistics()

        return self.stats['renamed']

    def _show_preview(self, rename_plan: List[Tuple[Path, str]]):
        """Show preview of rename operations"""
        print(f"\n{self._colorize('Preview of changes:', Colors.BRIGHT_CYAN + Colors.BOLD)}")
        print(self._colorize("─" * 80, Colors.BRIGHT_CYAN))

        # Show up to 20 examples
        preview_count = min(20, len(rename_plan))

        for i, (old_path, new_name) in enumerate(rename_plan[:preview_count]):
            old_name = old_path.name
            arrow = self._colorize("→", Colors.BRIGHT_YELLOW)
            print(f"  {old_name} {arrow} {self._colorize(new_name, Colors.BRIGHT_GREEN)}")

        if len(rename_plan) > preview_count:
            remaining = len(rename_plan) - preview_count
            print(f"  {self._colorize(f'... and {remaining} more files', Colors.DIM)}")

        print(self._colorize("─" * 80, Colors.BRIGHT_CYAN))

        if self.dry_run:
            print(self._colorize("DRY RUN MODE - No changes will be made", Colors.BRIGHT_YELLOW + Colors.BOLD))

    def _show_statistics(self):
        """Show operation statistics"""
        print(f"\n{self._colorize('Statistics:', Colors.BRIGHT_CYAN + Colors.BOLD)}")
        print(f"  Total files: {self.stats['total_files']}")
        print(f"  {self._colorize('Renamed:', Colors.GREEN)} {self.stats['renamed']}")
        if self.stats['errors'] > 0:
            print(f"  {self._colorize('Errors:', Colors.RED)} {self.stats['errors']}")

    def _save_history(self):
        """Save rename history for undo"""
        try:
            history = []
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    history = json.load(f)

            # Add current operation
            history.append({
                'timestamp': datetime.now().isoformat(),
                'operations': self.current_operation
            })

            # Keep only last 50 operations
            history = history[-50:]

            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)

            if self.verbose:
                print(f"\n{self._colorize('History saved', Colors.DIM)} (use --undo to revert)")

        except Exception as e:
            if self.verbose:
                print(f"Warning: Could not save history: {e}")

    def undo_last(self) -> bool:
        """Undo the last rename operation"""
        if not self.history_file.exists():
            print(self._colorize("No history found", Colors.YELLOW))
            return False

        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)

            if not history:
                print(self._colorize("No operations to undo", Colors.YELLOW))
                return False

            # Get last operation
            last_op = history.pop()
            operations = last_op['operations']

            print(f"{self._colorize('Undoing operation from', Colors.BRIGHT_CYAN)} {last_op['timestamp']}")
            print(f"Reverting {len(operations)} file(s)...")

            success_count = 0
            for op in reversed(operations):
                old_path = Path(op['old'])
                new_path = Path(op['new'])

                if new_path.exists():
                    try:
                        new_path.rename(old_path)
                        success_count += 1
                        print(f"{self._colorize('✓', Colors.GREEN)} Reverted: {new_path.name} → {old_path.name}")
                    except Exception as e:
                        print(f"{self._colorize('✗', Colors.RED)} Error reverting {new_path.name}: {e}")
                else:
                    print(f"{self._colorize('⚠', Colors.YELLOW)} File not found: {new_path}")

            # Update history
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)

            print(f"\n{self._colorize(f'Successfully reverted {success_count} file(s)', Colors.GREEN)}")
            return True

        except Exception as e:
            print(f"{self._colorize('Error:', Colors.RED)} {e}")
            return False

    def list_history(self):
        """List rename history"""
        if not self.history_file.exists():
            print(self._colorize("No history found", Colors.YELLOW))
            return

        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)

            if not history:
                print(self._colorize("No operations in history", Colors.YELLOW))
                return

            print(f"\n{self._colorize('Rename History:', Colors.BRIGHT_CYAN + Colors.BOLD)}")
            print(self._colorize("─" * 80, Colors.BRIGHT_CYAN))

            for i, op in enumerate(reversed(history), 1):
                timestamp = op['timestamp']
                count = len(op['operations'])
                print(f"{i}. {self._colorize(timestamp, Colors.CYAN)} - {count} file(s)")

                if self.verbose and count > 0:
                    # Show first few operations
                    for j, rename_op in enumerate(op['operations'][:3]):
                        old_name = Path(rename_op['old']).name
                        new_name = Path(rename_op['new']).name
                        print(f"   {old_name} → {new_name}")
                    if count > 3:
                        print(f"   ... and {count - 3} more")

        except Exception as e:
            print(f"{self._colorize('Error:', Colors.RED)} {e}")

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="BulkRename - Batch File Renaming Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Replace text in filenames
  %(prog)s replace -f "old" -r "new" /path/to/files

  # Sequential numbering
  %(prog)s sequential -t "photo_{n}" *.jpg

  # Add prefix
  %(prog)s prefix -p "backup_" *.txt

  # Change extension
  %(prog)s extension -e ".txt" *.text

  # Lowercase all filenames
  %(prog)s case -c lower *.TXT

  # Preview without making changes
  %(prog)s replace -f "test" -r "prod" --dry-run *.conf

  # Interactive mode with confirmation
  %(prog)s replace -f "v1" -r "v2" -i *.py

  # Undo last operation
  %(prog)s --undo

  # Show history
  %(prog)s --history
        """)

    parser.add_argument('mode', nargs='?',
                       choices=['replace', 'regex', 'sequential', 'case', 'prefix', 'suffix', 'extension', 'remove'],
                       help='Rename mode')

    # Mode-specific arguments
    parser.add_argument('-f', '--find', help='String to find (for replace/remove mode)')
    parser.add_argument('-r', '--replace', help='Replacement string (for replace/regex mode)')
    parser.add_argument('-p', '--pattern', help='Regex pattern (for regex mode) or glob pattern for files')
    parser.add_argument('--prefix', help='Prefix to add (for prefix mode)')
    parser.add_argument('--suffix', help='Suffix to add (for suffix mode)')
    parser.add_argument('-e', '--extension', help='New extension (for extension mode)')
    parser.add_argument('-c', '--case', choices=['lower', 'upper', 'title', 'capitalize'],
                       help='Case conversion type (for case mode)')
    parser.add_argument('-t', '--template', help='Template for sequential mode (use {n} for number, {name} for original name, {ext} for extension)')
    parser.add_argument('--digits', type=int, default=3, help='Number of digits for sequential numbering (default: 3)')
    parser.add_argument('--start', type=int, default=1, help='Starting number for sequential mode (default: 1)')

    # File selection
    parser.add_argument('files', nargs='*', help='Files or directories to process')
    parser.add_argument('--recursive', '-R', action='store_true', help='Process directories recursively')
    parser.add_argument('--include-dirs', action='store_true', help='Also rename directories')

    # Operation options
    parser.add_argument('--dry-run', '-n', action='store_true', help='Preview changes without renaming')
    parser.add_argument('--interactive', '-i', action='store_true', help='Ask for confirmation before renaming')
    parser.add_argument('--no-backup', action='store_true', help='Disable backup/history')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')

    # History operations
    parser.add_argument('--undo', action='store_true', help='Undo the last rename operation')
    parser.add_argument('--history', action='store_true', help='Show rename history')

    # Version
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')

    args = parser.parse_args()

    # Handle history operations
    renamer = BulkRename(
        dry_run=args.dry_run,
        interactive=args.interactive,
        recursive=args.recursive,
        include_dirs=args.include_dirs,
        backup=not args.no_backup,
        colors=not args.no_color,
        verbose=args.verbose
    )

    if args.undo:
        renamer.undo_last()
        return

    if args.history:
        renamer.list_history()
        return

    # Validate mode is provided
    if not args.mode:
        parser.print_help()
        return

    # Validate files are provided
    if not args.files:
        print("Error: No files specified", file=sys.stderr)
        sys.exit(1)

    # Map mode to enum
    mode_map = {
        'replace': RenameMode.REPLACE,
        'regex': RenameMode.REGEX,
        'sequential': RenameMode.SEQUENTIAL,
        'case': RenameMode.CASE,
        'prefix': RenameMode.PREFIX,
        'suffix': RenameMode.SUFFIX,
        'extension': RenameMode.EXTENSION,
        'remove': RenameMode.REMOVE
    }
    mode = mode_map[args.mode]

    # Build kwargs based on mode
    kwargs = {}
    if mode == RenameMode.REPLACE:
        if not args.find:
            print("Error: --find is required for replace mode", file=sys.stderr)
            sys.exit(1)
        kwargs['find'] = args.find
        kwargs['replace'] = args.replace or ''

    elif mode == RenameMode.REGEX:
        if not args.pattern:
            print("Error: --pattern is required for regex mode", file=sys.stderr)
            sys.exit(1)
        kwargs['pattern'] = args.pattern
        kwargs['replace'] = args.replace or ''

    elif mode == RenameMode.SEQUENTIAL:
        kwargs['template'] = args.template or '{name}_{n}'
        kwargs['digits'] = args.digits
        kwargs['start'] = args.start

    elif mode == RenameMode.CASE:
        if not args.case:
            print("Error: --case is required for case mode", file=sys.stderr)
            sys.exit(1)
        kwargs['case'] = args.case

    elif mode == RenameMode.PREFIX:
        if not args.prefix:
            print("Error: --prefix is required for prefix mode", file=sys.stderr)
            sys.exit(1)
        kwargs['prefix'] = args.prefix

    elif mode == RenameMode.SUFFIX:
        if not args.suffix:
            print("Error: --suffix is required for suffix mode", file=sys.stderr)
            sys.exit(1)
        kwargs['suffix'] = args.suffix

    elif mode == RenameMode.EXTENSION:
        if not args.extension:
            print("Error: --extension is required for extension mode", file=sys.stderr)
            sys.exit(1)
        kwargs['extension'] = args.extension

    elif mode == RenameMode.REMOVE:
        if not args.find:
            print("Error: --find is required for remove mode", file=sys.stderr)
            sys.exit(1)
        kwargs['pattern'] = args.find

    # Process each file/directory
    try:
        total_renamed = 0
        for target in args.files:
            if not os.path.exists(target):
                print(f"Warning: {target} does not exist, skipping", file=sys.stderr)
                continue

            renamed = renamer.rename(target, mode, args.pattern, **kwargs)
            total_renamed += renamed

        sys.exit(0 if total_renamed > 0 or args.dry_run else 1)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
