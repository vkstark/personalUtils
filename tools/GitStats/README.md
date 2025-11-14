# GitStats - Repository Statistics Analyzer

Comprehensive git repository analysis tool that generates detailed statistics about commits, contributors, file changes, and activity patterns.

## Features

- **Commit Statistics**
  - Total commits, files, contributors
  - Lines added/deleted
  - Repository age and activity

- **Contributor Analysis**
  - Contribution rankings
  - Lines of code per author
  - Activity timeframes

- **File Analysis**
  - Most changed files
  - Change frequency
  - Lines modified per file

- **Activity Patterns**
  - Commits by day of week
  - Commits by hour of day
  - Recent activity tracking

- **Export Options**
  - JSON export for further processing
  - Colored terminal output
  - Customizable reports

## Installation

```bash
chmod +x git_stats.py
# Optional: Create symlink
ln -s $(pwd)/git_stats.py ~/bin/gitstats
```

## Usage

### Basic Analysis
```bash
# Analyze current repository
./git_stats.py

# Analyze specific repository
./git_stats.py /path/to/repo
```

### Detailed Reports

**Contributors Report:**
```bash
# Top 10 contributors (default)
./git_stats.py --contributors 10

# Top 20 contributors
./git_stats.py --contributors 20
```

**File Changes Report:**
```bash
# Most changed files
./git_stats.py --files 15
```

**Activity Analysis:**
```bash
# Activity heatmap (by day/hour)
./git_stats.py --activity

# Recent activity (last 30 days)
./git_stats.py --recent 30

# Last 60 days
./git_stats.py --recent 60
```

### Full Report
```bash
# Complete analysis with all sections
./git_stats.py --full

# Full report for specific repo
./git_stats.py --full /path/to/repo
```

### Export Data
```bash
# Export statistics to JSON
./git_stats.py --export stats.json

# Full report + JSON export
./git_stats.py --full --export stats.json
```

## Output Examples

### Summary Statistics
```
============================================================
Git Repository Statistics: myproject
============================================================

📊 Overview
  Repository: /path/to/myproject
  Total Commits: 523
  Total Contributors: 8
  Total Files: 142
  Active Days: 218
  First Commit: 2023-01-15
  Last Commit: 2024-11-08
  Repository Age: 663 days
  Lines Added: +15,432
  Lines Deleted: -8,291
  Net Lines: 7,141
```

### Contributors Report
```
👥 Top Contributors
------------------------------------------------------------

1. John Doe <john@example.com>
   Commits: 245
   Lines: +8,432 / -3,291 (+5,141)
   Active: 2023-01-15 to 2024-11-08

2. Jane Smith <jane@example.com>
   Commits: 178
   Lines: +5,123 / -2,845 (+2,278)
   Active: 2023-02-01 to 2024-11-05
```

### Activity Heatmap
```
📅 Commit Activity Heatmap
------------------------------------------------------------

By Day of Week:
  Monday     ████████████████████ 45
  Tuesday    ██████████████████████████ 58
  Wednesday  ████████████████████████ 54
  Thursday   ██████████████████████ 49
  Friday     ███████████████████ 42
  Saturday   ████████ 18
  Sunday     ██████ 12

By Hour of Day:
  09:00 ██████████████████ 35
  10:00 ████████████████████████ 48
  11:00 ███████████████████████ 45
  14:00 ██████████████████████ 42
  15:00 ████████████████████████████ 56
```

## Command Line Options

```
positional arguments:
  repo                  Path to git repository (default: current directory)

report sections:
  --contributors N      Show top N contributors (default: 10 with --full)
  --files N            Show top N most changed files (default: 10 with --full)
  --activity           Show activity heatmap
  --recent DAYS        Show activity in recent N days (default: 30 with --full)
  --full               Show full report with all sections

output options:
  --export FILE        Export statistics to JSON file
  --no-color           Disable colored output
  -v, --verbose        Verbose output
  --version            Show version and exit
```

## JSON Export Format

The exported JSON includes:
```json
{
  "repository": "/path/to/repo",
  "stats": {
    "total_commits": 523,
    "total_contributors": 8,
    "total_files": 142,
    "lines_added": 15432,
    "lines_deleted": 8291,
    "first_commit": "2023-01-15T10:30:00",
    "last_commit": "2024-11-08T14:20:00",
    "active_days": 218
  },
  "contributors": {
    "John Doe": {
      "email": "john@example.com",
      "commits": 245,
      "insertions": 8432,
      "deletions": 3291,
      "first_commit": "2023-01-15T10:30:00",
      "last_commit": "2024-11-08T14:20:00"
    }
  },
  "files": {
    "src/main.py": {
      "changes": 45,
      "additions": 523,
      "deletions": 234
    }
  },
  "activity": {
    "hourly": { "9": 35, "10": 48 },
    "day_of_week": { "Monday": 45, "Tuesday": 58 }
  }
}
```

## Use Cases

**1. Project Health Check:**
```bash
./git_stats.py --full
```

**2. Team Contribution Review:**
```bash
./git_stats.py --contributors 20 --recent 90
```

**3. Code Churn Analysis:**
```bash
./git_stats.py --files 20
```

**4. Automated Reporting:**
```bash
./git_stats.py --full --export report.json --no-color
```

**5. Multiple Repositories:**
```bash
for repo in ~/projects/*/; do
    echo "=== $repo ==="
    ./git_stats.py "$repo" --contributors 5
done
```

## Tips

- Use `--full` for comprehensive reports
- Combine `--export` with scripts for automated analysis
- Use `--no-color` when piping to files or other programs
- Recent activity (`--recent`) is great for sprint reviews
- Activity heatmap shows team working patterns

## Requirements

- Git must be installed and in PATH
- Python 3.6 or higher
- Repository must have at least one commit

## Author

Vishal Kumar

## License

MIT
