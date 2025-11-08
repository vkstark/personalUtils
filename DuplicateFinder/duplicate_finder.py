#!/usr/bin/env python3
"""
DuplicateFinder - Find Duplicate Files
Find duplicate files by hash, size, or similarity with deletion options.

Author: Vishal Kumar
License: MIT
"""

import os
import sys
import argparse
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
import shutil

# Color codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    # Text colors
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'

    # Bright colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_CYAN = '\033[96m'

class DuplicateFinder:
    """Find duplicate files"""

    def __init__(self, colors: bool = True, verbose: bool = False):
        self.colors = colors and self._supports_color()
        self.verbose = verbose

        # Statistics
        self.stats = {
            'total_files': 0,
            'total_size': 0,
            'duplicate_files': 0,
            'duplicate_size': 0,
            'unique_files': 0
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

    def _format_size(self, size: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f}{unit}" if unit != 'B' else f"{size}B"
            size /= 1024
        return f"{size:.1f}PB"

    def _calculate_hash(self, filepath: str, algorithm: str = 'md5',
                       chunk_size: int = 8192) -> str:
        """Calculate file hash"""
        hash_func = hashlib.new(algorithm)

        try:
            with open(filepath, 'rb') as f:
                while chunk := f.read(chunk_size):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except Exception as e:
            if self.verbose:
                print(f"Error hashing {filepath}: {e}", file=sys.stderr)
            return ""

    def _get_files(self, paths: List[str], recursive: bool = True,
                   min_size: int = 0, max_size: Optional[int] = None,
                   extensions: Optional[List[str]] = None,
                   exclude_dirs: Optional[List[str]] = None) -> List[Path]:
        """Get list of files to check"""
        files = []
        exclude_dirs = exclude_dirs or ['.git', '__pycache__', 'node_modules']

        for path_str in paths:
            path = Path(path_str)

            if path.is_file():
                files.append(path)
            elif path.is_dir():
                if recursive:
                    for item in path.rglob('*'):
                        if item.is_file():
                            # Check if in excluded directory
                            if any(excl in item.parts for excl in exclude_dirs):
                                continue
                            files.append(item)
                else:
                    for item in path.iterdir():
                        if item.is_file():
                            files.append(item)

        # Filter by size
        if min_size > 0:
            files = [f for f in files if f.stat().st_size >= min_size]

        if max_size is not None:
            files = [f for f in files if f.stat().st_size <= max_size]

        # Filter by extension
        if extensions:
            files = [f for f in files if f.suffix.lower() in extensions]

        return files

    def find_by_hash(self, paths: List[str], recursive: bool = True,
                     min_size: int = 0, max_size: Optional[int] = None,
                     extensions: Optional[List[str]] = None,
                     exclude_dirs: Optional[List[str]] = None,
                     algorithm: str = 'md5') -> Dict[str, List[str]]:
        """Find duplicates by file hash"""

        files = self._get_files(paths, recursive, min_size, max_size,
                               extensions, exclude_dirs)

        print(self._colorize(f"Scanning {len(files)} files...", Colors.CYAN))

        # Group by size first (optimization)
        size_groups = defaultdict(list)
        for filepath in files:
            try:
                size = filepath.stat().st_size
                size_groups[size].append(str(filepath))
                self.stats['total_files'] += 1
                self.stats['total_size'] += size
            except Exception as e:
                if self.verbose:
                    print(f"Error reading {filepath}: {e}", file=sys.stderr)

        # Calculate hashes only for files with same size
        hash_groups = defaultdict(list)
        files_to_hash = []

        for size, group in size_groups.items():
            if len(group) > 1:
                files_to_hash.extend(group)

        if self.verbose:
            print(f"Hashing {len(files_to_hash)} potentially duplicate files...")

        for filepath in files_to_hash:
            file_hash = self._calculate_hash(filepath, algorithm)
            if file_hash:
                hash_groups[file_hash].append(filepath)

        # Filter to only duplicates
        duplicates = {h: files for h, files in hash_groups.items() if len(files) > 1}

        # Update statistics
        for files in duplicates.values():
            self.stats['duplicate_files'] += len(files) - 1
            file_size = Path(files[0]).stat().st_size
            self.stats['duplicate_size'] += file_size * (len(files) - 1)

        self.stats['unique_files'] = self.stats['total_files'] - self.stats['duplicate_files']

        return duplicates

    def find_by_name(self, paths: List[str], recursive: bool = True,
                     case_sensitive: bool = False,
                     exclude_dirs: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """Find duplicates by filename"""

        files = self._get_files(paths, recursive, exclude_dirs=exclude_dirs)

        print(self._colorize(f"Scanning {len(files)} files...", Colors.CYAN))

        # Group by filename
        name_groups = defaultdict(list)

        for filepath in files:
            name = filepath.name
            if not case_sensitive:
                name = name.lower()

            name_groups[name].append(str(filepath))
            self.stats['total_files'] += 1

        # Filter to only duplicates
        duplicates = {name: files for name, files in name_groups.items() if len(files) > 1}

        return duplicates

    def find_empty(self, paths: List[str], recursive: bool = True,
                   exclude_dirs: Optional[List[str]] = None) -> List[str]:
        """Find empty files"""

        files = self._get_files(paths, recursive, exclude_dirs=exclude_dirs)

        empty_files = []
        for filepath in files:
            try:
                if filepath.stat().st_size == 0:
                    empty_files.append(str(filepath))
            except Exception as e:
                if self.verbose:
                    print(f"Error checking {filepath}: {e}", file=sys.stderr)

        return empty_files

    def delete_duplicates(self, duplicates: Dict[str, List[str]],
                         keep: str = 'first', dry_run: bool = True,
                         interactive: bool = False) -> int:
        """Delete duplicate files"""

        deleted_count = 0

        for hash_or_name, files in duplicates.items():
            # Determine which file to keep
            if keep == 'first':
                keep_file = files[0]
                delete_files = files[1:]
            elif keep == 'last':
                keep_file = files[-1]
                delete_files = files[:-1]
            elif keep == 'shortest':
                keep_file = min(files, key=lambda f: len(f))
                delete_files = [f for f in files if f != keep_file]
            elif keep == 'longest':
                keep_file = max(files, key=lambda f: len(f))
                delete_files = [f for f in files if f != keep_file]
            else:
                keep_file = files[0]
                delete_files = files[1:]

            print(f"\n{self._colorize('Keeping:', Colors.GREEN)} {keep_file}")

            for filepath in delete_files:
                if interactive:
                    response = input(f"  Delete {filepath}? (y/N): ")
                    if response.lower() not in ['y', 'yes']:
                        print(f"  {self._colorize('Skipped:', Colors.YELLOW)} {filepath}")
                        continue

                if dry_run:
                    print(f"  {self._colorize('[DRY RUN]', Colors.YELLOW)} Would delete: {filepath}")
                else:
                    try:
                        os.remove(filepath)
                        print(f"  {self._colorize('Deleted:', Colors.RED)} {filepath}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"  {self._colorize('Error:', Colors.RED)} Could not delete {filepath}: {e}")

        return deleted_count

    def format_duplicates(self, duplicates: Dict[str, List[str]],
                         show_hash: bool = False) -> str:
        """Format duplicates for display"""
        output = []

        if not duplicates:
            return self._colorize("No duplicates found", Colors.GREEN)

        output.append(self._colorize(f"\nFound {len(duplicates)} set(s) of duplicates:", Colors.BRIGHT_YELLOW + Colors.BOLD))

        for i, (hash_or_name, files) in enumerate(duplicates.items(), 1):
            # Get file size
            file_size = Path(files[0]).stat().st_size
            size_str = self._format_size(file_size)

            # Header
            if show_hash:
                output.append(f"\n{i}. {self._colorize('Hash:', Colors.DIM)} {hash_or_name[:16]}... ({size_str}, {len(files)} files)")
            else:
                output.append(f"\n{i}. {self._colorize('Name:', Colors.CYAN)} {hash_or_name} ({size_str}, {len(files)} files)")

            # Files
            for j, filepath in enumerate(files):
                marker = self._colorize('[K]', Colors.GREEN) if j == 0 else self._colorize('[D]', Colors.RED)
                output.append(f"   {marker} {filepath}")

        return '\n'.join(output)

    def get_stats(self) -> str:
        """Get statistics string"""
        output = []

        output.append(self._colorize("\n📊 Statistics:", Colors.BRIGHT_CYAN + Colors.BOLD))
        output.append(f"  Total files scanned: {self.stats['total_files']}")
        output.append(f"  Total size: {self._format_size(self.stats['total_size'])}")
        output.append(f"  Unique files: {self.stats['unique_files']}")
        output.append(f"  Duplicate files: {self._colorize(str(self.stats['duplicate_files']), Colors.YELLOW)}")
        output.append(f"  Wasted space: {self._colorize(self._format_size(self.stats['duplicate_size']), Colors.RED)}")

        if self.stats['duplicate_size'] > 0:
            percentage = (self.stats['duplicate_size'] / self.stats['total_size']) * 100
            output.append(f"  Waste percentage: {percentage:.1f}%")

        return '\n'.join(output)

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="DuplicateFinder - Find Duplicate Files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find duplicates in current directory
  %(prog)s .

  # Find duplicates recursively
  %(prog)s /path/to/dir --recursive

  # Find by filename only
  %(prog)s . --by-name

  # Find empty files
  %(prog)s . --empty

  # Delete duplicates (dry run first)
  %(prog)s . --delete --dry-run

  # Delete duplicates interactively
  %(prog)s . --delete --interactive

  # Filter by size and extension
  %(prog)s . --min-size 1048576 --extensions .jpg .png .mp4
        """)

    parser.add_argument('paths', nargs='+', help='Paths to scan')

    # Scan options
    parser.add_argument('-r', '--recursive', action='store_true',
                       help='Scan directories recursively')
    parser.add_argument('--by-name', action='store_true',
                       help='Find duplicates by filename instead of hash')
    parser.add_argument('--empty', action='store_true',
                       help='Find empty files')
    parser.add_argument('--case-sensitive', action='store_true',
                       help='Case-sensitive filename matching (with --by-name)')

    # Filter options
    parser.add_argument('--min-size', type=int, default=0, metavar='BYTES',
                       help='Minimum file size in bytes')
    parser.add_argument('--max-size', type=int, metavar='BYTES',
                       help='Maximum file size in bytes')
    parser.add_argument('--extensions', nargs='+', metavar='EXT',
                       help='Filter by file extensions (e.g., .jpg .png)')
    parser.add_argument('--exclude-dirs', nargs='+', metavar='DIR',
                       help='Directories to exclude')

    # Hash options
    parser.add_argument('--algorithm', choices=['md5', 'sha1', 'sha256'], default='md5',
                       help='Hash algorithm (default: md5)')

    # Delete options
    parser.add_argument('--delete', action='store_true',
                       help='Delete duplicate files')
    parser.add_argument('--keep', choices=['first', 'last', 'shortest', 'longest'],
                       default='first',
                       help='Which file to keep when deleting (default: first)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without deleting')
    parser.add_argument('-i', '--interactive', action='store_true',
                       help='Ask before deleting each file')

    # Display options
    parser.add_argument('--show-hash', action='store_true',
                       help='Show file hashes in output')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')

    # Version
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')

    args = parser.parse_args()

    try:
        finder = DuplicateFinder(colors=not args.no_color, verbose=args.verbose)

        # Find empty files
        if args.empty:
            empty = finder.find_empty(args.paths, args.recursive, args.exclude_dirs)

            if empty:
                print(self._colorize(f"\nFound {len(empty)} empty file(s):", Colors.YELLOW))
                for filepath in empty:
                    print(f"  {filepath}")
            else:
                print(finder._colorize("No empty files found", Colors.GREEN))

            sys.exit(0)

        # Find duplicates
        if args.by_name:
            duplicates = finder.find_by_name(args.paths, args.recursive,
                                            args.case_sensitive, args.exclude_dirs)
        else:
            duplicates = finder.find_by_hash(args.paths, args.recursive,
                                            args.min_size, args.max_size,
                                            args.extensions, args.exclude_dirs,
                                            args.algorithm)

        # Display results
        print(finder.format_duplicates(duplicates, args.show_hash))
        print(finder.get_stats())

        # Delete if requested
        if args.delete and duplicates:
            print()
            deleted = finder.delete_duplicates(duplicates, args.keep,
                                              args.dry_run or not args.delete,
                                              args.interactive)

            if not args.dry_run:
                print(f"\n{finder._colorize('✓', Colors.GREEN)} Deleted {deleted} file(s)")

    except KeyboardInterrupt:
        print("\n\nCancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
