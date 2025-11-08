#!/usr/bin/env python3
"""
SnippetManager - Code Snippet Storage and Retrieval
Organize, search, and manage code snippets with tags and fuzzy search.

Author: Vishal Kumar
License: MIT
"""

import os
import sys
import argparse
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from collections import defaultdict

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

class Snippet:
    """Represents a code snippet"""

    def __init__(self, id: str, title: str, code: str, language: str,
                 description: str = "", tags: Optional[List[str]] = None,
                 created: Optional[str] = None, modified: Optional[str] = None):
        self.id = id
        self.title = title
        self.code = code
        self.language = language
        self.description = description
        self.tags = tags or []
        self.created = created or datetime.now().isoformat()
        self.modified = modified or datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert snippet to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'code': self.code,
            'language': self.language,
            'description': self.description,
            'tags': self.tags,
            'created': self.created,
            'modified': self.modified
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Snippet':
        """Create snippet from dictionary"""
        return cls(**data)

class SnippetManager:
    """Manage code snippets"""

    def __init__(self, storage_path: Optional[str] = None, colors: bool = True):
        self.colors = colors and self._supports_color()

        # Default storage location
        if storage_path is None:
            storage_path = str(Path.home() / '.snippets.json')

        self.storage_path = Path(storage_path)
        self.snippets: Dict[str, Snippet] = {}

        # Load existing snippets
        self._load()

    def _supports_color(self) -> bool:
        """Check if terminal supports color output"""
        return (hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
                os.getenv('TERM') != 'dumb')

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled"""
        if not self.colors:
            return text
        return f"{color}{text}{Colors.RESET}"

    def _load(self):
        """Load snippets from storage"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for snippet_data in data:
                        snippet = Snippet.from_dict(snippet_data)
                        self.snippets[snippet.id] = snippet
            except Exception as e:
                print(f"Warning: Could not load snippets: {e}", file=sys.stderr)

    def _save(self):
        """Save snippets to storage"""
        try:
            data = [snippet.to_dict() for snippet in self.snippets.values()]

            # Create parent directory if it doesn't exist
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error: Could not save snippets: {e}", file=sys.stderr)
            raise

    def _generate_id(self, title: str) -> str:
        """Generate unique ID for snippet"""
        # Start with title-based ID
        base_id = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')

        # Ensure uniqueness
        if base_id not in self.snippets:
            return base_id

        # Add number suffix if needed
        counter = 1
        while f"{base_id}-{counter}" in self.snippets:
            counter += 1
        return f"{base_id}-{counter}"

    def add(self, title: str, code: str, language: str,
            description: str = "", tags: Optional[List[str]] = None,
            snippet_id: Optional[str] = None) -> str:
        """Add a new snippet"""

        # Generate or validate ID
        if snippet_id is None:
            snippet_id = self._generate_id(title)
        elif snippet_id in self.snippets:
            raise ValueError(f"Snippet with ID '{snippet_id}' already exists")

        # Create snippet
        snippet = Snippet(
            id=snippet_id,
            title=title,
            code=code,
            language=language,
            description=description,
            tags=tags or []
        )

        # Add to collection
        self.snippets[snippet_id] = snippet
        self._save()

        return snippet_id

    def update(self, snippet_id: str, title: Optional[str] = None,
               code: Optional[str] = None, language: Optional[str] = None,
               description: Optional[str] = None, tags: Optional[List[str]] = None):
        """Update an existing snippet"""

        if snippet_id not in self.snippets:
            raise ValueError(f"Snippet '{snippet_id}' not found")

        snippet = self.snippets[snippet_id]

        # Update fields
        if title is not None:
            snippet.title = title
        if code is not None:
            snippet.code = code
        if language is not None:
            snippet.language = language
        if description is not None:
            snippet.description = description
        if tags is not None:
            snippet.tags = tags

        snippet.modified = datetime.now().isoformat()
        self._save()

    def delete(self, snippet_id: str):
        """Delete a snippet"""
        if snippet_id not in self.snippets:
            raise ValueError(f"Snippet '{snippet_id}' not found")

        del self.snippets[snippet_id]
        self._save()

    def get(self, snippet_id: str) -> Optional[Snippet]:
        """Get a snippet by ID"""
        return self.snippets.get(snippet_id)

    def search(self, query: Optional[str] = None, tags: Optional[List[str]] = None,
               language: Optional[str] = None) -> List[Snippet]:
        """Search snippets"""
        results = list(self.snippets.values())

        # Filter by tags
        if tags:
            results = [s for s in results if any(tag in s.tags for tag in tags)]

        # Filter by language
        if language:
            results = [s for s in results if s.language.lower() == language.lower()]

        # Filter by query (fuzzy search in title, description, code, tags)
        if query:
            query_lower = query.lower()
            results = [
                s for s in results
                if (query_lower in s.title.lower() or
                    query_lower in s.description.lower() or
                    query_lower in s.code.lower() or
                    any(query_lower in tag.lower() for tag in s.tags))
            ]

        return results

    def list_all(self) -> List[Snippet]:
        """List all snippets"""
        return sorted(self.snippets.values(), key=lambda s: s.modified, reverse=True)

    def get_tags(self) -> Dict[str, int]:
        """Get all tags with counts"""
        tag_counts = defaultdict(int)
        for snippet in self.snippets.values():
            for tag in snippet.tags:
                tag_counts[tag] += 1
        return dict(tag_counts)

    def get_languages(self) -> Dict[str, int]:
        """Get all languages with counts"""
        lang_counts = defaultdict(int)
        for snippet in self.snippets.values():
            lang_counts[snippet.language] += 1
        return dict(lang_counts)

    def export_snippet(self, snippet_id: str, filepath: str):
        """Export snippet to file"""
        snippet = self.get(snippet_id)
        if not snippet:
            raise ValueError(f"Snippet '{snippet_id}' not found")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(snippet.code)

        print(f"{self._colorize('✓', Colors.GREEN)} Exported to: {filepath}")

    def import_snippet(self, filepath: str, title: str, language: str,
                      description: str = "", tags: Optional[List[str]] = None) -> str:
        """Import snippet from file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()

        snippet_id = self.add(title, code, language, description, tags)
        return snippet_id

    def format_snippet(self, snippet: Snippet, detailed: bool = False) -> str:
        """Format snippet for display"""
        output = []

        # Header with ID and title
        header = f"{self._colorize(snippet.id, Colors.BRIGHT_CYAN + Colors.BOLD)}: {snippet.title}"
        output.append(header)

        # Language and tags
        lang_str = self._colorize(f"[{snippet.language}]", Colors.BLUE)
        tags_str = ""
        if snippet.tags:
            tags_str = " " + " ".join([self._colorize(f"#{tag}", Colors.YELLOW) for tag in snippet.tags])
        output.append(f"  {lang_str}{tags_str}")

        # Description
        if snippet.description:
            output.append(f"  {self._colorize(snippet.description, Colors.DIM)}")

        # Code (if detailed)
        if detailed:
            output.append(f"\n  {self._colorize('Code:', Colors.GREEN)}")
            for line in snippet.code.split('\n'):
                output.append(f"    {line}")

        # Metadata (if detailed)
        if detailed:
            created = datetime.fromisoformat(snippet.created).strftime('%Y-%m-%d %H:%M')
            modified = datetime.fromisoformat(snippet.modified).strftime('%Y-%m-%d %H:%M')
            output.append(f"\n  {self._colorize('Created:', Colors.DIM)} {created}")
            output.append(f"  {self._colorize('Modified:', Colors.DIM)} {modified}")

        return '\n'.join(output)

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="SnippetManager - Code Snippet Storage and Retrieval",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add a snippet
  %(prog)s add -t "Quick sort" -l python -f quicksort.py --tags algorithm sorting

  # Add snippet from stdin
  %(prog)s add -t "Docker run" -l bash -c "docker run -d -p 80:80 nginx"

  # List all snippets
  %(prog)s list

  # Search snippets
  %(prog)s search "docker"
  %(prog)s search --tags algorithm
  %(prog)s search --language python

  # Show snippet details
  %(prog)s show quicksort

  # Copy snippet to file
  %(prog)s export quicksort output.py

  # Update snippet
  %(prog)s update quicksort --tags algorithm sorting python

  # Delete snippet
  %(prog)s delete quicksort

  # List all tags
  %(prog)s tags

  # List all languages
  %(prog)s languages
        """)

    parser.add_argument('--storage', help='Path to snippets storage file')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new snippet')
    add_parser.add_argument('-t', '--title', required=True, help='Snippet title')
    add_parser.add_argument('-l', '--language', required=True, help='Programming language')
    add_parser.add_argument('-c', '--code', help='Code content (or use -f/--file)')
    add_parser.add_argument('-f', '--file', help='Read code from file')
    add_parser.add_argument('-d', '--description', default='', help='Description')
    add_parser.add_argument('--tags', nargs='+', help='Tags')
    add_parser.add_argument('--id', help='Custom snippet ID')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update a snippet')
    update_parser.add_argument('id', help='Snippet ID')
    update_parser.add_argument('-t', '--title', help='New title')
    update_parser.add_argument('-l', '--language', help='New language')
    update_parser.add_argument('-c', '--code', help='New code content')
    update_parser.add_argument('-f', '--file', help='Read new code from file')
    update_parser.add_argument('-d', '--description', help='New description')
    update_parser.add_argument('--tags', nargs='+', help='New tags')

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a snippet')
    delete_parser.add_argument('id', help='Snippet ID')
    delete_parser.add_argument('-y', '--yes', action='store_true', help='Skip confirmation')

    # Show command
    show_parser = subparsers.add_parser('show', help='Show snippet details')
    show_parser.add_argument('id', help='Snippet ID')
    show_parser.add_argument('--raw', action='store_true', help='Show only code without formatting')

    # List command
    list_parser = subparsers.add_parser('list', help='List all snippets')
    list_parser.add_argument('-l', '--language', help='Filter by language')
    list_parser.add_argument('--tags', nargs='+', help='Filter by tags')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search snippets')
    search_parser.add_argument('query', nargs='?', help='Search query')
    search_parser.add_argument('-l', '--language', help='Filter by language')
    search_parser.add_argument('--tags', nargs='+', help='Filter by tags')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export snippet to file')
    export_parser.add_argument('id', help='Snippet ID')
    export_parser.add_argument('output', help='Output file path')

    # Tags command
    subparsers.add_parser('tags', help='List all tags')

    # Languages command
    subparsers.add_parser('languages', help='List all languages')

    # Version
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        # Create manager
        manager = SnippetManager(
            storage_path=args.storage,
            colors=not args.no_color
        )

        # Execute command
        if args.command == 'add':
            # Get code
            if args.code:
                code = args.code
            elif args.file:
                with open(args.file, 'r', encoding='utf-8') as f:
                    code = f.read()
            else:
                print("Error: Either --code or --file must be provided", file=sys.stderr)
                sys.exit(1)

            snippet_id = manager.add(
                title=args.title,
                code=code,
                language=args.language,
                description=args.description,
                tags=args.tags,
                snippet_id=args.id
            )
            print(f"{manager._colorize('✓', Colors.GREEN)} Added snippet: {snippet_id}")

        elif args.command == 'update':
            # Get code if specified
            code = args.code
            if args.file:
                with open(args.file, 'r', encoding='utf-8') as f:
                    code = f.read()

            manager.update(
                snippet_id=args.id,
                title=args.title,
                code=code,
                language=args.language,
                description=args.description,
                tags=args.tags
            )
            print(f"{manager._colorize('✓', Colors.GREEN)} Updated snippet: {args.id}")

        elif args.command == 'delete':
            if not args.yes:
                response = input(f"Delete snippet '{args.id}'? (y/N): ")
                if response.lower() not in ['y', 'yes']:
                    print("Cancelled")
                    sys.exit(0)

            manager.delete(args.id)
            print(f"{manager._colorize('✓', Colors.GREEN)} Deleted snippet: {args.id}")

        elif args.command == 'show':
            snippet = manager.get(args.id)
            if not snippet:
                print(f"Error: Snippet '{args.id}' not found", file=sys.stderr)
                sys.exit(1)

            if args.raw:
                print(snippet.code)
            else:
                print(manager.format_snippet(snippet, detailed=True))

        elif args.command == 'list':
            snippets = manager.search(language=args.language, tags=args.tags)

            if not snippets:
                print("No snippets found")
                sys.exit(0)

            print(f"\n{manager._colorize(f'Found {len(snippets)} snippet(s)', Colors.BRIGHT_CYAN + Colors.BOLD)}\n")
            for snippet in snippets:
                print(manager.format_snippet(snippet))
                print()

        elif args.command == 'search':
            snippets = manager.search(query=args.query, language=args.language, tags=args.tags)

            if not snippets:
                print("No snippets found")
                sys.exit(0)

            print(f"\n{manager._colorize(f'Found {len(snippets)} snippet(s)', Colors.BRIGHT_CYAN + Colors.BOLD)}\n")
            for snippet in snippets:
                print(manager.format_snippet(snippet))
                print()

        elif args.command == 'export':
            manager.export_snippet(args.id, args.output)

        elif args.command == 'tags':
            tags = manager.get_tags()
            if not tags:
                print("No tags found")
                sys.exit(0)

            print(f"\n{manager._colorize('Tags:', Colors.BRIGHT_CYAN + Colors.BOLD)}")
            for tag, count in sorted(tags.items(), key=lambda x: -x[1]):
                print(f"  {manager._colorize(f'#{tag}', Colors.YELLOW)}: {count}")

        elif args.command == 'languages':
            languages = manager.get_languages()
            if not languages:
                print("No languages found")
                sys.exit(0)

            print(f"\n{manager._colorize('Languages:', Colors.BRIGHT_CYAN + Colors.BOLD)}")
            for lang, count in sorted(languages.items(), key=lambda x: -x[1]):
                print(f"  {manager._colorize(lang, Colors.BLUE)}: {count}")

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
