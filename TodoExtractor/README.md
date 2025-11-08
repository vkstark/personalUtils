# TodoExtractor - Extract TODO/FIXME/HACK Comments

Find and organize all TODO, FIXME, HACK, and other task comments in your codebase with priority levels and smart grouping.

## Features

- **Multi-Tag Support**
  - TODO, FIXME, BUG, HACK, XXX
  - NOTE, OPTIMIZE, REFACTOR, REVIEW
  - DEPRECATED
  - Custom tags

- **Smart Extraction**
  - Priority levels (P0-P3)
  - Author attribution
  - Context preservation
  - Line number tracking

- **Flexible Organization**
  - Group by file, tag, or priority
  - Sort and filter options
  - Summary statistics

- **Multiple Export Formats**
  - JSON for automation
  - Markdown for documentation
  - Colored terminal output

## Installation

```bash
chmod +x todo_extractor.py
# Optional: Create symlink
ln -s $(pwd)/todo_extractor.py ~/bin/todoextract
```

## Usage

### Basic Extraction
```bash
# Scan current directory
./todo_extractor.py .

# Scan specific directory
./todo_extractor.py /path/to/project

# Scan single file
./todo_extractor.py script.py
```

### Grouping Options
```bash
# Group by file (default)
./todo_extractor.py . --group-by file

# Group by tag type
./todo_extractor.py . --group-by tag

# Group by priority level
./todo_extractor.py . --group-by priority
```

### Filtering
```bash
# Scan only specific tags
./todo_extractor.py . --tags TODO FIXME

# Scan specific file types
./todo_extractor.py . --extensions .py .js .ts

# Exclude additional directories
./todo_extractor.py . --exclude-dirs vendor external
```

### Export Options
```bash
# Export to JSON
./todo_extractor.py . --export-json todos.json

# Export to Markdown
./todo_extractor.py . --export-md TODO.md

# Both exports
./todo_extractor.py . --export-json todos.json --export-md TODO.md
```

### Display Options
```bash
# Summary only
./todo_extractor.py . --summary-only

# Hide line numbers
./todo_extractor.py . --no-line-numbers

# Verbose output
./todo_extractor.py . -v
```

## Comment Format

### Basic TODO
```python
# TODO: Implement user authentication
# FIXME: This breaks on empty input
# HACK: Temporary workaround for bug #123
```

### With Author
```python
# TODO(john): Add error handling
# FIXME(alice): Memory leak in this function
```

### With Priority
```python
# TODO[P1]: Low priority enhancement
# FIXME[P3]: Critical bug - fix immediately!
# HACK[P2]: Important refactoring needed
```

### Combined
```python
# TODO(john)[P2]: Implement caching layer
# FIXME(alice)[P3]: Security vulnerability - patch ASAP
```

## Priority Levels

### Automatic Priorities
- **P3 (Urgent)**: FIXME, BUG, XXX
- **P2 (Important)**: HACK, DEPRECATED
- **P1 (Normal)**: TODO, OPTIMIZE, REFACTOR, REVIEW
- **P0 (Info)**: NOTE

### Override with Tags
```python
# TODO[P3]: Override to urgent priority
# NOTE[P2]: Important note that needs attention
```

## Output Examples

### Summary
```
============================================================
TODO/FIXME Summary
============================================================

Files Scanned: 42
Total Items: 23

By Tag:
  TODO: 15
  FIXME: 5
  HACK: 2
  NOTE: 1
```

### Grouped by File
```
TODOs by File:
------------------------------------------------------------

src/main.py (3 items)
  [TODO] Implement user authentication
    → src/main.py:45
  [FIXME] Handle edge case for empty strings
    → src/main.py:102
  [HACK] Temporary fix for parsing
    → src/main.py:156
```

### Grouped by Tag
```
TODOs by Tag:
------------------------------------------------------------

FIXME (5 items)
  [FIXME] This breaks on empty input
    → src/parser.py:23
  [FIXME] Memory leak in loop
    → src/utils.py:87
```

### Grouped by Priority
```
TODOs by Priority:
------------------------------------------------------------

Priority 3 (2 items)
  [FIXME][P3] Critical security bug
    → src/auth.py:15
  [BUG][P3] Data corruption issue
    → src/db.py:234

Priority 2 (3 items)
  [HACK](alice)[P2] Refactor this module
    → src/legacy.py:456
```

## Export Formats

### JSON
```json
{
  "timestamp": "2024-11-08T10:30:00",
  "stats": {
    "files_scanned": 42,
    "total_todos": 23,
    "by_tag": {
      "TODO": 15,
      "FIXME": 5
    }
  },
  "todos": [
    {
      "tag": "TODO",
      "text": "Implement caching",
      "file": "src/main.py",
      "line": 45,
      "priority": 1,
      "author": "john"
    }
  ]
}
```

### Markdown
```markdown
# TODO Report

Generated: 2024-11-08 10:30:00

## Summary
- Files Scanned: 42
- Total Items: 23

### By Tag
- **FIXME**: 5
- **TODO**: 15

## Detailed List

### FIXME (5)
- **Handle edge case for empty strings**
  - `src/parser.py:23`
```

## Advanced Usage

### CI/CD Integration
```bash
# Exit code 1 if TODOs found, 0 if none
./todo_extractor.py . --summary-only
if [ $? -eq 1 ]; then
    echo "TODOs found in codebase"
fi
```

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit
./todo_extractor.py . --tags FIXME BUG --summary-only
```

### Project Documentation
```bash
# Generate TODO.md for repository
./todo_extractor.py . --export-md TODO.md --group-by priority
git add TODO.md
git commit -m "Update TODO list"
```

### Find Critical Items
```bash
# Show only high-priority items
./todo_extractor.py . --group-by priority | grep -A 20 "Priority 3"
```

### Language-Specific Scans
```bash
# Python only
./todo_extractor.py . --extensions .py

# JavaScript/TypeScript
./todo_extractor.py . --extensions .js .ts .jsx .tsx

# Multiple languages
./todo_extractor.py . --extensions .py .js .go .rs
```

## Supported File Types

By default, scans:
- **Python**: .py
- **JavaScript/TypeScript**: .js, .ts, .jsx, .tsx
- **Java**: .java
- **C/C++**: .c, .cpp, .h, .hpp
- **Go**: .go
- **Rust**: .rs
- **Ruby**: .rb
- **PHP**: .php
- **Shell**: .sh, .bash, .zsh
- **CSS**: .css, .scss, .sass, .less
- **Markup**: .html, .xml, .md
- **Config**: .yaml, .yml, .json, .toml

## Command Line Options

```
positional arguments:
  path                  File or directory to scan (default: .)

scanning options:
  --tags TAG [TAG ...]  Tags to search for
  --extensions EXT [EXT ...]
                        File extensions to scan
  --exclude-dirs DIR [DIR ...]
                        Additional directories to exclude
  --no-recursive        Do not scan subdirectories
  --case-sensitive      Case-sensitive tag matching

display options:
  --group-by {file,tag,priority}
                        Group results by (default: file)
  --no-line-numbers     Hide line numbers
  --summary-only        Show only summary
  --no-color            Disable colored output
  -v, --verbose         Verbose output

export options:
  --export-json FILE    Export to JSON
  --export-md FILE      Export to Markdown
```

## Excluded Directories

By default excludes:
- `.git`
- `node_modules`
- `__pycache__`
- `.venv`, `venv`
- `dist`, `build`
- `.next`, `.nuxt`
- `target`

Add more with `--exclude-dirs`.

## Tips

1. **Use priority tags** for better organization
2. **Include author** to track who wrote the TODO
3. **Export to Markdown** for project documentation
4. **Group by priority** to focus on urgent items
5. **Use in CI/CD** to track technical debt

## Exit Codes

- `0` - Success, no TODOs found
- `1` - Success, TODOs found (useful for CI/CD)
- `130` - Cancelled by user

## Author

Vishal Kumar

## License

MIT
