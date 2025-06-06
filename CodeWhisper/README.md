# 🧠 Enhanced Python Code Analyzer
Comprehensive Python codebase analysis tool with CLI support, detailed stats, and flexible output formats.

This tool scans Python files or directories to extract meaningful insights from your codebase including complexity, imports, classes, functions, docstrings, and more. It supports multiple output formats such as terminal, JSON, and Markdown, making it suitable for both CLI use and automated documentation/report generation.

# 📦 Features
- 🔍 Analyze single files or entire directories

- 📊 Generate statistics (functions, classes, imports, lines of code, etc.)

- ⚙️ Optional inclusion of:
    - Function call analysis
    - Complexity scores
    - Print/log statement analysis

- 🖨️ Output in terminal, JSON, or Markdown formats
- 📁 Exclude patterns (e.g., test_*.py, migrations/)
- 🎨 Colorized output (can be disabled)
- 🧩 Export results to files
- 🧠 Include full function definitions (optional)

<br></br>
# 🧪 Usage
```bash
python analyzer.py [options]
```

<br></br>
# 📁 Basic Examples

| Command                                              | Description                       |
| ---------------------------------------------------- | --------------------------------- |
| `python analyzer.py`                                 | Analyze current directory         |
| `python analyzer.py path/to/project`                 | Analyze a specific directory      |
| `python analyzer.py -d`                              | Show detailed analysis            |
| `python analyzer.py --format json -o report.json`    | Save results in JSON format       |
| `python analyzer.py --format markdown -o README.md`  | Export as Markdown documentation  |
| `python analyzer.py --exclude "test_*" "migrations"` | Exclude specific file patterns    |
| `python analyzer.py --function-definitions`          | Include full function definitions |

<br></br>
# 🎛️ Options
| Option                   | Description                                      |
| ------------------------ | ------------------------------------------------ |
| `-d, --detailed`         | Show detailed info (parameters, docstrings)      |
| `--no-docstrings`        | Skip docstring analysis                          |
| `--no-complexity`        | Skip complexity calculation                      |
| `--no-calls`             | Skip function call tracking                      |
| `--no-prints-logs`       | Skip print/log analysis                          |
| `--function-definitions` | Include full function bodies                     |
| `--pattern *.py`         | File pattern to match                            |
| `--exclude PATTERN`      | Exclude pattern (repeatable)                     |
| `--format`               | Output format: `terminal`, `json`, or `markdown` |
| `-o FILE`                | Output file path                                 |
| `--stats-only`           | Show summary stats only                          |
| `--no-color`             | Disable colored terminal output                  |
| `--version`              | Show version number                              |
<br></br>
# 📄 License<br>
MIT License © [Vishal Kumar]
<br></br>
# 🙌 Contributing
Contributions are welcome! Open an issue or submit a PR with improvements, bug fixes, or new features.