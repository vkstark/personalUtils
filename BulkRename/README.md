# BulkRename - Batch File Renaming Utility

A powerful tool for renaming multiple files with patterns, regex, sequential numbering, and full undo support.

## Features

- **Multiple Rename Modes**
  - Replace text in filenames
  - Regex pattern matching
  - Sequential numbering
  - Case conversion
  - Add prefix/suffix
  - Change extensions
  - Remove patterns

- **Safety Features**
  - Preview mode (dry-run)
  - Interactive confirmation
  - Undo support with history
  - Backup tracking
  - Conflict detection

- **Flexible Operation**
  - Recursive directory processing
  - Glob pattern support
  - Include/exclude directories
  - Verbose logging

## Installation

```bash
chmod +x bulk_rename.py
# Optional: Create symlink
ln -s $(pwd)/bulk_rename.py ~/bin/bulkrename
```

## Usage

### Replace Mode
Replace text in filenames:
```bash
# Replace "old" with "new"
./bulk_rename.py replace -f "old" -r "new" *.txt

# Remove text (replace with nothing)
./bulk_rename.py replace -f "_backup" -r "" *.jpg
```

### Sequential Numbering
Rename files with sequential numbers:
```bash
# Default: filename_001, filename_002, etc.
./bulk_rename.py sequential *.jpg

# Custom template
./bulk_rename.py sequential -t "photo_{n}" *.jpg

# Custom template with extension
./bulk_rename.py sequential -t "IMG_{n}.{ext}" *.jpg

# Start from 100 with 4 digits
./bulk_rename.py sequential -t "doc_{n}" --start 100 --digits 4 *.pdf
```

### Case Conversion
Change filename case:
```bash
# Lowercase
./bulk_rename.py case -c lower *.TXT

# Uppercase
./bulk_rename.py case -c upper *.txt

# Title Case
./bulk_rename.py case -c title *.md

# Capitalize
./bulk_rename.py case -c capitalize *.py
```

### Prefix/Suffix
Add prefix or suffix to filenames:
```bash
# Add prefix
./bulk_rename.py prefix --prefix "backup_" *.conf

# Add suffix (before extension)
./bulk_rename.py suffix --suffix "_v2" *.py
```

### Change Extension
Change file extensions:
```bash
# Change .text to .txt
./bulk_rename.py extension -e ".txt" *.text

# Change .jpeg to .jpg
./bulk_rename.py extension -e "jpg" *.jpeg
```

### Regex Mode
Use regex patterns for complex renaming:
```bash
# Remove numbers from filenames
./bulk_rename.py regex -p "\d+" -r "" *.txt

# Replace multiple spaces with single underscore
./bulk_rename.py regex -p "\s+" -r "_" *.md

# Extract date pattern
./bulk_rename.py regex -p "(\d{4})-(\d{2})-(\d{2})" -r "\1\2\3" *.log
```

### Remove Pattern
Remove specific patterns from filenames:
```bash
# Remove "Copy of " from filenames
./bulk_rename.py remove -f "Copy of " *.txt
```

## Options

### File Selection
```bash
# Recursive processing
./bulk_rename.py replace -f "old" -r "new" -R /path/to/dir

# Include directories too
./bulk_rename.py case -c lower --include-dirs /path/to/dir

# Use glob pattern
./bulk_rename.py replace -f "test" -r "prod" -p "*.conf" /path/to/dir
```

### Safety Options
```bash
# Dry run (preview only)
./bulk_rename.py replace -f "old" -r "new" --dry-run *.txt

# Interactive mode (confirm before renaming)
./bulk_rename.py replace -f "old" -r "new" -i *.txt

# Verbose output
./bulk_rename.py replace -f "old" -r "new" -v *.txt
```

### Undo & History
```bash
# Undo last operation
./bulk_rename.py --undo

# Show history
./bulk_rename.py --history

# Show detailed history
./bulk_rename.py --history -v
```

## Examples

### Common Use Cases

**1. Organize photos with sequential names:**
```bash
./bulk_rename.py sequential -t "vacation_2024_{n}" --start 1 *.jpg
```

**2. Clean up downloaded files:**
```bash
# Remove "(1)", "(2)" from duplicate downloads
./bulk_rename.py regex -p "\s*\(\d+\)" -r "" ~/Downloads/*
```

**3. Standardize file extensions:**
```bash
./bulk_rename.py extension -e ".txt" *.text
```

**4. Add date prefix to files:**
```bash
./bulk_rename.py prefix --prefix "2024-01-15_" *.log
```

**5. Convert all to lowercase:**
```bash
./bulk_rename.py case -c lower -R /path/to/project
```

**6. Replace spaces with underscores:**
```bash
./bulk_rename.py replace -f " " -r "_" *.md
```

**7. Remove "Copy of " prefix:**
```bash
./bulk_rename.py remove -f "Copy of " *.docx
```

**8. Batch rename with preview:**
```bash
# First, preview changes
./bulk_rename.py replace -f "draft" -r "final" --dry-run *.txt

# If looks good, apply changes
./bulk_rename.py replace -f "draft" -r "final" *.txt

# If mistake, undo
./bulk_rename.py --undo
```

## Template Variables

For sequential mode, use these variables in templates:
- `{n}` - Sequential number (with padding)
- `{name}` - Original filename (without extension)
- `{ext}` - File extension (without dot)

Example: `-t "IMG_{n}_{name}.{ext}"`

## Command Line Options

```
positional arguments:
  mode                  Rename mode (replace/regex/sequential/case/prefix/suffix/extension/remove)
  files                 Files or directories to process

mode-specific:
  -f, --find           String to find (replace/remove mode)
  -r, --replace        Replacement string (replace/regex mode)
  -p, --pattern        Regex pattern or glob pattern
  --prefix             Prefix to add
  --suffix             Suffix to add
  -e, --extension      New extension
  -c, --case          Case type (lower/upper/title/capitalize)
  -t, --template      Template for sequential mode
  --digits            Number of digits for sequential (default: 3)
  --start             Starting number (default: 1)

options:
  -R, --recursive      Process directories recursively
  --include-dirs       Also rename directories
  -n, --dry-run        Preview changes without renaming
  -i, --interactive    Ask for confirmation
  -v, --verbose        Verbose output
  --no-backup          Disable history/undo
  --no-color           Disable colored output
  --undo               Undo last operation
  --history            Show rename history
```

## Tips

1. **Always use --dry-run first** to preview changes
2. **Use interactive mode (-i)** for important files
3. **History is saved** in `~/.bulk_rename_history.json`
4. **Undo is available** for the last 50 operations
5. **Backup is automatic** unless disabled with --no-backup

## Exit Codes

- `0` - Success (files renamed or dry-run completed)
- `1` - Error or no files renamed
- `130` - Cancelled by user (Ctrl+C)

## Author

Vishal Kumar

## License

MIT
