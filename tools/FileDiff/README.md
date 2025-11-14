# FileDiff - Advanced File Comparison Tool

A powerful side-by-side file comparison utility with colored output and multiple diff formats.

## Features

- **Multiple Display Modes**
  - Unified diff (like `diff -u`)
  - Context diff (like `diff -c`)
  - Side-by-side comparison
  - Minimal diff (changes only)
  - HTML output

- **Smart Comparison Options**
  - Ignore whitespace
  - Ignore blank lines
  - Case-insensitive comparison
  - Configurable context lines

- **Beautiful Output**
  - Colored terminal output
  - Line numbers
  - Statistics
  - Clear visual indicators

## Installation

```bash
chmod +x file_diff.py
# Optional: Create symlink
ln -s $(pwd)/file_diff.py ~/bin/filediff
```

## Usage

### Basic Comparison
```bash
# Unified diff (default)
./file_diff.py file1.txt file2.txt

# Side-by-side comparison
./file_diff.py -m side_by_side old.py new.py

# Show only changes
./file_diff.py -m minimal config1.json config2.json
```

### Comparison Options
```bash
# Ignore whitespace
./file_diff.py -w file1.txt file2.txt

# Ignore blank lines
./file_diff.py -b file1.txt file2.txt

# Case-insensitive
./file_diff.py -i file1.txt file2.txt

# Combine options
./file_diff.py -w -b -i file1.txt file2.txt
```

### Output Options
```bash
# Save to file
./file_diff.py -o diff.txt file1.txt file2.txt

# HTML output
./file_diff.py -m html -o diff.html old.py new.py

# Show statistics
./file_diff.py -s file1.txt file2.txt
```

### Quick Check
```bash
# Check if files are identical (exit code 0 = same, 1 = different)
./file_diff.py --check file1.txt file2.txt
echo $?  # 0 if identical, 1 if different
```

## Display Modes

### Unified Diff
Standard unified format with context lines
```
--- file1.txt
+++ file2.txt
@@ -1,3 +1,3 @@
 unchanged line
-old line
+new line
 unchanged line
```

### Side-by-Side
Visual side-by-side comparison
```
file1.txt          │ file2.txt
───────────────────────────────
1 Hello World      │ 1 Hello World
2 Old Line       < │
  > │ 2 New Line
3 End              │ 3 End
```

### Minimal
Shows only the changes
```
Lines 5-7 → 5-6
- old line 1
- old line 2
+ new line
```

### HTML
Generates a complete HTML diff report

## Examples

```bash
# Compare Python files with side-by-side view
./file_diff.py -m side_by_side old_script.py new_script.py

# Ignore all whitespace when comparing configs
./file_diff.py -w config.prod.json config.dev.json

# Generate HTML report of changes
./file_diff.py -m html -o report.html version1.py version2.py

# Quick check in scripts
if ./file_diff.py --check expected.txt actual.txt; then
    echo "Test passed!"
else
    echo "Files differ!"
fi
```

## Command Line Options

```
positional arguments:
  file1                 First file to compare
  file2                 Second file to compare

options:
  -h, --help            show this help message and exit
  -m, --mode {unified,context,side_by_side,minimal,html}
                        Diff display mode (default: unified)
  -w, --ignore-whitespace
                        Ignore whitespace differences
  -b, --ignore-blank-lines
                        Ignore blank lines
  -i, --ignore-case     Ignore case differences
  -c N, --context N     Number of context lines (default: 3)
  --no-color            Disable colored output
  --no-line-numbers     Hide line numbers
  --tab-size N          Tab size for display (default: 4)
  -o FILE, --output FILE
                        Save output to file
  -s, --stats           Show statistics
  --check               Only check if files are identical
  --version             show program's version number and exit
```

## Exit Codes

- `0` - Files are identical (or --check passed)
- `1` - Files are different
- `2` - Error occurred

## Author

Vishal Kumar

## License

MIT
