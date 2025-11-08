#!/usr/bin/env python3
"""
EnvManager - .env File Management Tool
Manage, validate, and switch between multiple .env files with templates and validation.

Author: Vishal Kumar
License: MIT
"""

import os
import sys
import argparse
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

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

class EnvManager:
    """Manage .env files"""

    def __init__(self, colors: bool = True, verbose: bool = False):
        self.colors = colors and self._supports_color()
        self.verbose = verbose

    def _supports_color(self) -> bool:
        """Check if terminal supports color output"""
        return (hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
                os.getenv('TERM') != 'dumb')

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled"""
        if not self.colors:
            return text
        return f"{color}{text}{Colors.RESET}"

    def parse_env_file(self, filepath: str) -> Dict[str, str]:
        """Parse .env file and return variables"""
        variables = {}

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue

                    # Parse KEY=VALUE
                    match = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$', line, re.IGNORECASE)
                    if match:
                        key, value = match.groups()

                        # Remove quotes if present
                        value = value.strip()
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]

                        variables[key] = value
                    elif self.verbose:
                        print(f"Warning: Invalid line {line_num}: {line}", file=sys.stderr)

        except FileNotFoundError:
            raise ValueError(f"File not found: {filepath}")
        except Exception as e:
            raise ValueError(f"Error reading {filepath}: {e}")

        return variables

    def write_env_file(self, filepath: str, variables: Dict[str, str],
                       comments: Optional[Dict[str, str]] = None):
        """Write variables to .env file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for key in sorted(variables.keys()):
                    value = variables[key]

                    # Add comment if provided
                    if comments and key in comments:
                        f.write(f"# {comments[key]}\n")

                    # Quote value if it contains spaces
                    if ' ' in value or '\t' in value:
                        value = f'"{value}"'

                    f.write(f"{key}={value}\n")

            if self.verbose:
                print(f"Wrote {len(variables)} variables to {filepath}")

        except Exception as e:
            raise ValueError(f"Error writing {filepath}: {e}")

    def compare(self, file1: str, file2: str) -> Dict[str, any]:
        """Compare two .env files"""
        vars1 = self.parse_env_file(file1)
        vars2 = self.parse_env_file(file2)

        keys1 = set(vars1.keys())
        keys2 = set(vars2.keys())

        return {
            'only_in_file1': sorted(keys1 - keys2),
            'only_in_file2': sorted(keys2 - keys1),
            'common': sorted(keys1 & keys2),
            'different_values': sorted([
                key for key in keys1 & keys2
                if vars1[key] != vars2[key]
            ]),
            'same_values': sorted([
                key for key in keys1 & keys2
                if vars1[key] == vars2[key]
            ])
        }

    def validate(self, filepath: str, required: Optional[List[str]] = None,
                 patterns: Optional[Dict[str, str]] = None) -> Tuple[bool, List[str]]:
        """Validate .env file"""
        errors = []
        variables = self.parse_env_file(filepath)

        # Check required variables
        if required:
            for var in required:
                if var not in variables:
                    errors.append(f"Missing required variable: {var}")
                elif not variables[var]:
                    errors.append(f"Empty value for required variable: {var}")

        # Validate patterns
        if patterns:
            for var, pattern in patterns.items():
                if var in variables:
                    if not re.match(pattern, variables[var]):
                        errors.append(f"Invalid format for {var}: does not match pattern {pattern}")

        return len(errors) == 0, errors

    def merge(self, *files: str, output: Optional[str] = None,
              priority: str = 'last') -> Dict[str, str]:
        """Merge multiple .env files"""
        merged = {}

        file_list = list(files) if priority == 'last' else list(reversed(files))

        for filepath in file_list:
            variables = self.parse_env_file(filepath)
            merged.update(variables)

        if output:
            self.write_env_file(output, merged)

        return merged

    def create_template(self, filepath: str, output: str,
                       remove_values: bool = True, add_comments: bool = True):
        """Create template from existing .env file"""
        variables = self.parse_env_file(filepath)

        template_vars = {}
        comments = {}

        for key, value in variables.items():
            if remove_values:
                # Keep structure but remove actual values
                if value:
                    template_vars[key] = ""
                    if add_comments:
                        # Detect value type for comment
                        if value.isdigit():
                            comments[key] = "Integer value"
                        elif value in ('true', 'false', 'True', 'False'):
                            comments[key] = "Boolean value"
                        elif value.startswith('http'):
                            comments[key] = "URL"
                        else:
                            comments[key] = "String value"
                else:
                    template_vars[key] = ""
            else:
                template_vars[key] = value
                if add_comments:
                    comments[key] = "Required"

        self.write_env_file(output, template_vars, comments if add_comments else None)

    def switch(self, env_file: str, target: str = '.env', backup: bool = True):
        """Switch to a different .env file"""
        source = Path(env_file)
        dest = Path(target)

        if not source.exists():
            raise ValueError(f"Source file not found: {env_file}")

        # Backup existing file
        if dest.exists() and backup:
            backup_path = dest.with_suffix(dest.suffix + '.backup')
            shutil.copy2(dest, backup_path)
            if self.verbose:
                print(f"Backed up {dest} to {backup_path}")

        # Copy new file
        shutil.copy2(source, dest)

    def list_vars(self, filepath: str, show_values: bool = True,
                  filter_pattern: Optional[str] = None) -> List[Tuple[str, str]]:
        """List variables in .env file"""
        variables = self.parse_env_file(filepath)

        # Filter if pattern provided
        if filter_pattern:
            pattern = re.compile(filter_pattern, re.IGNORECASE)
            variables = {k: v for k, v in variables.items() if pattern.search(k)}

        return [(k, v if show_values else '***') for k, v in sorted(variables.items())]

    def get_stats(self, filepath: str) -> Dict[str, any]:
        """Get statistics about .env file"""
        variables = self.parse_env_file(filepath)

        return {
            'total_vars': len(variables),
            'empty_vars': sum(1 for v in variables.values() if not v),
            'non_empty_vars': sum(1 for v in variables.values() if v),
            'avg_key_length': sum(len(k) for k in variables.keys()) / len(variables) if variables else 0,
            'avg_value_length': sum(len(v) for v in variables.values()) / len(variables) if variables else 0,
            'longest_key': max((len(k), k) for k in variables.keys())[1] if variables else None,
            'shortest_value': min((len(v), k) for k, v in variables.items() if v)[1] if any(variables.values()) else None
        }

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="EnvManager - .env File Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List variables
  %(prog)s list .env

  # List variables (hide values)
  %(prog)s list .env --hide-values

  # Compare two .env files
  %(prog)s compare .env.dev .env.prod

  # Validate .env file
  %(prog)s validate .env --required DB_HOST DB_PORT API_KEY

  # Create template
  %(prog)s template .env .env.example

  # Merge multiple files
  %(prog)s merge .env.base .env.dev -o .env

  # Switch environment
  %(prog)s switch .env.production

  # Get statistics
  %(prog)s stats .env
        """)

    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # List command
    list_parser = subparsers.add_parser('list', help='List variables in .env file')
    list_parser.add_argument('file', help='.env file to list')
    list_parser.add_argument('--hide-values', action='store_true', help='Hide variable values')
    list_parser.add_argument('--filter', help='Filter variables by pattern (regex)')

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare two .env files')
    compare_parser.add_argument('file1', help='First .env file')
    compare_parser.add_argument('file2', help='Second .env file')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate .env file')
    validate_parser.add_argument('file', help='.env file to validate')
    validate_parser.add_argument('--required', nargs='+', help='Required variables')
    validate_parser.add_argument('--pattern', nargs='+', help='Validation patterns (VAR:REGEX)')

    # Template command
    template_parser = subparsers.add_parser('template', help='Create template from .env file')
    template_parser.add_argument('input', help='Input .env file')
    template_parser.add_argument('output', help='Output template file')
    template_parser.add_argument('--keep-values', action='store_true', help='Keep original values')
    template_parser.add_argument('--no-comments', action='store_true', help='Do not add comments')

    # Merge command
    merge_parser = subparsers.add_parser('merge', help='Merge multiple .env files')
    merge_parser.add_argument('files', nargs='+', help='.env files to merge')
    merge_parser.add_argument('-o', '--output', required=True, help='Output file')
    merge_parser.add_argument('--priority', choices=['first', 'last'], default='last',
                             help='Priority for duplicate keys (default: last)')

    # Switch command
    switch_parser = subparsers.add_parser('switch', help='Switch to different .env file')
    switch_parser.add_argument('source', help='Source .env file')
    switch_parser.add_argument('-t', '--target', default='.env', help='Target file (default: .env)')
    switch_parser.add_argument('--no-backup', action='store_true', help='Do not create backup')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics about .env file')
    stats_parser.add_argument('file', help='.env file')

    # Version
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        manager = EnvManager(colors=not args.no_color, verbose=args.verbose)

        if args.command == 'list':
            variables = manager.list_vars(args.file,
                                         show_values=not args.hide_values,
                                         filter_pattern=args.filter)

            print(f"\n{manager._colorize('Variables:', Colors.BRIGHT_CYAN + Colors.BOLD)}")
            for key, value in variables:
                key_str = manager._colorize(key, Colors.GREEN)
                print(f"  {key_str}={value}")

            print(f"\n{manager._colorize(f'Total: {len(variables)} variables', Colors.DIM)}")

        elif args.command == 'compare':
            result = manager.compare(args.file1, args.file2)

            print(f"\n{manager._colorize('Comparison Results:', Colors.BRIGHT_CYAN + Colors.BOLD)}")

            if result['only_in_file1']:
                print(f"\n{manager._colorize(f'Only in {args.file1}:', Colors.RED)}")
                for var in result['only_in_file1']:
                    print(f"  - {var}")

            if result['only_in_file2']:
                print(f"\n{manager._colorize(f'Only in {args.file2}:', Colors.GREEN)}")
                for var in result['only_in_file2']:
                    print(f"  + {var}")

            if result['different_values']:
                print(f"\n{manager._colorize('Different values:', Colors.YELLOW)}")
                for var in result['different_values']:
                    print(f"  ~ {var}")

            if result['same_values']:
                print(f"\n{manager._colorize('Same values:', Colors.DIM)}")
                print(f"  {len(result['same_values'])} variables")

        elif args.command == 'validate':
            patterns = {}
            if args.pattern:
                for p in args.pattern:
                    if ':' in p:
                        var, regex = p.split(':', 1)
                        patterns[var] = regex

            valid, errors = manager.validate(args.file, args.required, patterns)

            if valid:
                print(f"{manager._colorize('✓', Colors.GREEN)} Validation passed")
            else:
                print(f"{manager._colorize('✗', Colors.RED)} Validation failed:")
                for error in errors:
                    print(f"  - {error}")
                sys.exit(1)

        elif args.command == 'template':
            manager.create_template(
                args.input,
                args.output,
                remove_values=not args.keep_values,
                add_comments=not args.no_comments
            )
            print(f"{manager._colorize('✓', Colors.GREEN)} Template created: {args.output}")

        elif args.command == 'merge':
            merged = manager.merge(*args.files, output=args.output, priority=args.priority)
            print(f"{manager._colorize('✓', Colors.GREEN)} Merged {len(args.files)} files into {args.output}")
            print(f"Total variables: {len(merged)}")

        elif args.command == 'switch':
            manager.switch(args.source, args.target, backup=not args.no_backup)
            print(f"{manager._colorize('✓', Colors.GREEN)} Switched to {args.source}")

        elif args.command == 'stats':
            stats = manager.get_stats(args.file)

            print(f"\n{manager._colorize('Statistics:', Colors.BRIGHT_CYAN + Colors.BOLD)}")
            print(f"  Total variables: {stats['total_vars']}")
            print(f"  Non-empty: {stats['non_empty_vars']}")
            print(f"  Empty: {stats['empty_vars']}")
            print(f"  Avg key length: {stats['avg_key_length']:.1f}")
            print(f"  Avg value length: {stats['avg_value_length']:.1f}")
            if stats['longest_key']:
                print(f"  Longest key: {stats['longest_key']}")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nCancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
