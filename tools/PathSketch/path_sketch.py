#!/usr/bin/env python3
"""
A powerful, customizable directory tree visualization tool.

Author: Vishal Kumar
License: MIT
"""

import os
import sys
import argparse
import stat
import time
from pathlib import Path
from typing import List, Optional, Union
import re
import json

# Color codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
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

class TreeStyle:
    """Different tree drawing styles"""
    ASCII = {
        'branch': '├── ',
        'last': '└── ',
        'pipe': '│   ',
        'space': '    '
    }
    
    UNICODE = {
        'branch': '├── ',
        'last': '└── ',
        'pipe': '│   ',
        'space': '    '
    }
    
    ROUNDED = {
        'branch': '├─ ',
        'last': '╰─ ',
        'pipe': '│  ',
        'space': '   '
    }

class FileInfo:
    """Container for file information"""
    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        self.is_dir = path.is_dir()
        self.is_hidden = self.name.startswith('.')
        
        try:
            self.stat = path.stat()
            self.size = self.stat.st_size
            self.modified = self.stat.st_mtime
            self.permissions = stat.filemode(self.stat.st_mode)
        except (OSError, PermissionError):
            self.stat = None
            self.size = 0
            self.modified = 0
            self.permissions = '?????????'

class DirectoryTree:
    """Enhanced directory tree generator"""
    
    def __init__(self, 
                 show_hidden: bool = False,
                 show_size: bool = False,
                 show_permissions: bool = False,
                 show_modified: bool = False,
                 max_depth: Optional[int] = None,
                 pattern: Optional[str] = None,
                 ignore_patterns: Optional[List[str]] = None,
                 style: str = 'unicode',
                 colors: bool = True,
                 sort_by: str = 'name',
                 reverse_sort: bool = False):
        
        self.show_hidden = show_hidden
        self.show_size = show_size
        self.show_permissions = show_permissions
        self.show_modified = show_modified
        self.max_depth = max_depth
        self.pattern = re.compile(pattern) if pattern else None
        self.ignore_patterns = [re.compile(p) for p in (ignore_patterns or [])]
        self.colors = colors and self._supports_color()
        self.sort_by = sort_by
        self.reverse_sort = reverse_sort
        
        # Set tree style
        if style == 'ascii':
            self.style = TreeStyle.ASCII
        elif style == 'rounded':
            self.style = TreeStyle.ROUNDED
        else:
            self.style = TreeStyle.UNICODE
            
        # Statistics
        self.stats = {
            'directories': 0,
            'files': 0,
            'total_size': 0,
            'hidden_files': 0,
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
    
    def _get_file_color(self, file_info: FileInfo) -> str:
        """Get appropriate color for file based on type"""
        if not self.colors:
            return ""
            
        if file_info.is_dir:
            return Colors.BRIGHT_BLUE + Colors.BOLD
        elif file_info.name.startswith('.'):
            return Colors.DIM
        elif any(file_info.name.endswith(ext) for ext in ['.py', '.js', '.sh', '.bat']):
            return Colors.BRIGHT_GREEN
        elif any(file_info.name.endswith(ext) for ext in ['.txt', '.md', '.rst']):
            return Colors.WHITE
        elif any(file_info.name.endswith(ext) for ext in ['.jpg', '.png', '.gif', '.svg']):
            return Colors.BRIGHT_MAGENTA
        elif any(file_info.name.endswith(ext) for ext in ['.zip', '.tar', '.gz']):
            return Colors.BRIGHT_RED
        else:
            return Colors.RESET
    
    def _format_size(self, size: float) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'K', 'M', 'G', 'T']:
            if size < 1024:
                return f"{size:3.0f}{unit}" if unit == 'B' else f"{size:3.1f}{unit}"
            size /= 1024
        return f"{size:3.1f}P"
    
    def _format_time(self, timestamp: float) -> str:
        """Format timestamp in readable format"""
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp))
    
    def _should_include(self, file_info: FileInfo) -> bool:
        """Check if file should be included based on filters"""
        # Check hidden files
        if file_info.is_hidden and not self.show_hidden:
            return False
            
        # Check pattern matching
        if self.pattern and not self.pattern.search(file_info.name):
            return False
            
        # Check ignore patterns
        for ignore_pattern in self.ignore_patterns:
            if ignore_pattern.search(file_info.name):
                return False
                
        return True
    
    def _get_entries(self, path: Path) -> List[FileInfo]:
        """Get and sort directory entries"""
        try:
            entries = []
            for item in path.iterdir():
                file_info = FileInfo(item)
                if self._should_include(file_info):
                    entries.append(file_info)
            
            # Sort entries
            if self.sort_by == 'size':
                entries.sort(key=lambda x: x.size, reverse=self.reverse_sort)
            elif self.sort_by == 'modified':
                entries.sort(key=lambda x: x.modified, reverse=self.reverse_sort)
            else:  # name
                entries.sort(key=lambda x: (not x.is_dir, x.name.lower()), 
                           reverse=self.reverse_sort)
                
            return entries
            
        except PermissionError:
            self.stats['errors'] += 1
            return []
    
    def _format_file_info(self, file_info: FileInfo) -> str:
        """Format additional file information"""
        info_parts = []
        
        if self.show_permissions:
            info_parts.append(self._colorize(file_info.permissions, Colors.DIM))
        
        if self.show_size and not file_info.is_dir:
            size_str = self._format_size(file_info.size)
            info_parts.append(self._colorize(f"[{size_str}]", Colors.YELLOW))
        
        if self.show_modified:
            time_str = self._format_time(file_info.modified)
            info_parts.append(self._colorize(f"({time_str})", Colors.CYAN))
        
        return " " + " ".join(info_parts) if info_parts else ""
    
    def generate_tree(self, start_path: Union[str, Path], output_file: Optional[str] = None) -> str:
        """Generate the directory tree"""
        start_path = Path(start_path).resolve()
        
        if not start_path.exists():
            raise FileNotFoundError(f"Path '{start_path}' does not exist")
        
        if not start_path.is_dir():
            raise NotADirectoryError(f"Path '{start_path}' is not a directory")
        
        # Reset statistics
        for key in self.stats:
            self.stats[key] = 0
        
        output_lines = []
        
        # Add header
        header = self._colorize(str(start_path), Colors.BRIGHT_CYAN + Colors.BOLD)
        output_lines.append(header)
        
        # Generate tree
        self._generate_tree_recursive(start_path, "", output_lines, 0)
        
        # Add statistics
        output_lines.append("")
        stats_text = (f"{self.stats['directories']} directories, "
                     f"{self.stats['files']} files")
        
        if self.stats['total_size'] > 0:
            stats_text += f", {self._format_size(self.stats['total_size'])} total"
        
        if self.stats['hidden_files'] > 0:
            stats_text += f", {self.stats['hidden_files']} hidden"
        
        if self.stats['errors'] > 0:
            stats_text += f", {self.stats['errors']} errors"
        
        output_lines.append(self._colorize(stats_text, Colors.DIM))
        
        result = "\n".join(output_lines)
        
        # Write to file if specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                # Remove color codes for file output
                clean_result = re.sub(r'\033\[[0-9;]*m', '', result)
                f.write(clean_result)
        
        return result
    
    def _generate_tree_recursive(self, path: Path, prefix: str, 
                                output_lines: List[str], depth: int):
        """Recursively generate tree structure"""
        if self.max_depth is not None and depth >= self.max_depth:
            return
        
        entries = self._get_entries(path)
        
        for idx, file_info in enumerate(entries):
            is_last = (idx == len(entries) - 1)
            
            # Choose connector
            connector = self.style['last'] if is_last else self.style['branch']
            
            # Format filename with color
            colored_name = self._colorize(file_info.name, 
                                        self._get_file_color(file_info))
            
            # Add file info
            info_str = self._format_file_info(file_info)
            
            # Build line
            line = f"{prefix}{connector}{colored_name}{info_str}"
            output_lines.append(line)
            
            # Update statistics
            if file_info.is_dir:
                self.stats['directories'] += 1
            else:
                self.stats['files'] += 1
                self.stats['total_size'] += file_info.size
            
            if file_info.is_hidden:
                self.stats['hidden_files'] += 1
            
            # Recurse into directories
            if file_info.is_dir:
                extension = self.style['space'] if is_last else self.style['pipe']
                self._generate_tree_recursive(file_info.path, 
                                            prefix + extension, 
                                            output_lines, depth + 1)

def create_gitignore_patterns() -> List[str]:
    """Create common ignore patterns similar to .gitignore"""
    return [
        r'\.git$',
        r'\.gitignore$',
        r'__pycache__',
        r'\.pyc$',
        r'\.pyo$',
        r'\.pyd$',
        r'\.so$',
        r'\.egg-info$',
        r'node_modules',
        r'\.DS_Store$',
        r'Thumbs\.db$',
        r'\.vscode$',
        r'\.idea$'
    ]

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="Enhanced Directory Tree Tool - Generate beautiful directory trees",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Current directory
  %(prog)s /path/to/dir             # Specific directory
  %(prog)s -a -s -L 3               # Show all files with sizes, max depth 3
  %(prog)s -P "*.py" --sort size    # Only Python files, sorted by size
  %(prog)s --ignore "*.log" -o tree.txt  # Ignore log files, save to file
  %(prog)s --style ascii --no-color     # ASCII style without colors
        """)
    
    parser.add_argument('path', nargs='?', default='.',
                       help='Directory path to analyze (default: current directory)')
    
    # Display options
    parser.add_argument('-a', '--all', action='store_true',
                       help='Show hidden files and directories')
    parser.add_argument('-s', '--size', action='store_true',
                       help='Show file sizes')
    parser.add_argument('-p', '--permissions', action='store_true',
                       help='Show file permissions')
    parser.add_argument('-t', '--time', action='store_true',
                       help='Show modification times')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')
    
    # Filtering options
    parser.add_argument('-L', '--max-depth', type=int, metavar='N',
                       help='Maximum depth to traverse')
    parser.add_argument('-P', '--pattern', metavar='REGEX',
                       help='Only show files matching pattern (regex)')
    parser.add_argument('-I', '--ignore', action='append', metavar='PATTERN',
                       help='Ignore files matching pattern (can be used multiple times)')
    parser.add_argument('--gitignore', action='store_true',
                       help='Use common .gitignore patterns')
    
    # Sorting options
    parser.add_argument('--sort', choices=['name', 'size', 'modified'], 
                       default='name', help='Sort files by (default: name)')
    parser.add_argument('-r', '--reverse', action='store_true',
                       help='Reverse sort order')
    
    # Style options
    parser.add_argument('--style', choices=['unicode', 'ascii', 'rounded'],
                       default='unicode', help='Tree drawing style (default: unicode)')
    
    # Output options
    parser.add_argument('-o', '--output', metavar='FILE',
                       help='Save output to file')
    parser.add_argument('--json', action='store_true',
                       help='Output statistics in JSON format')
    
    # Version
    parser.add_argument('--version', action='version', version='%(prog)s 2.0.0')
    
    args = parser.parse_args()
    
    try:
        # Prepare ignore patterns
        ignore_patterns = args.ignore or []
        if args.gitignore:
            ignore_patterns.extend(create_gitignore_patterns())
        
        # Create tree generator
        tree = DirectoryTree(
            show_hidden=args.all,
            show_size=args.size,
            show_permissions=args.permissions,
            show_modified=args.time,
            max_depth=args.max_depth,
            pattern=args.pattern,
            ignore_patterns=ignore_patterns,
            style=args.style,
            colors=not args.no_color,
            sort_by=args.sort,
            reverse_sort=args.reverse
        )
        
        # Generate and display tree
        output = tree.generate_tree(args.path, args.output)
        
        if not args.output:  # Only print if not saving to file
            print(output)
        
        # Output JSON statistics if requested
        if args.json:
            json_output = {
                'path': str(Path(args.path).resolve()),
                'statistics': tree.stats,
                'options': {
                    'show_hidden': args.all,
                    'show_size': args.size,
                    'max_depth': args.max_depth,
                    'pattern': args.pattern,
                    'style': args.style
                }
            }
            print(json.dumps(json_output, indent=2))
        
        if args.output:
            print(f"Tree saved to: {args.output}")
    
    except (FileNotFoundError, NotADirectoryError, PermissionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()