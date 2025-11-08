# SnippetManager - Code Snippet Storage and Retrieval

Organize, search, and manage your code snippets with tags, fuzzy search, and easy access from the command line.

## Features

- **Easy Storage**
  - Add snippets from files or command line
  - Automatic unique ID generation
  - Organize with tags and descriptions
  - Support for all programming languages

- **Powerful Search**
  - Search by keywords (fuzzy matching)
  - Filter by tags
  - Filter by language
  - Combine multiple filters

- **Smart Management**
  - Update existing snippets
  - Export to files
  - Import from files
  - Tag and language statistics

- **Persistent Storage**
  - JSON-based storage (~/.snippets.json)
  - Custom storage location support
  - Automatic backups on modification

## Installation

```bash
chmod +x snippet_manager.py
# Optional: Create symlink
ln -s $(pwd)/snippet_manager.py ~/bin/snippet
```

## Usage

### Adding Snippets

**From file:**
```bash
# Add snippet from file
./snippet_manager.py add -t "Quick sort algorithm" -l python -f quicksort.py --tags algorithm sorting

# With description
./snippet_manager.py add -t "Docker compose" -l yaml -f docker-compose.yml -d "Basic Docker setup" --tags docker devops
```

**From command line:**
```bash
# Add snippet directly
./snippet_manager.py add -t "Git aliases" -l bash -c "git log --oneline --graph" --tags git

# Multi-line code
./snippet_manager.py add -t "Python decorator" -l python -c "def my_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper" --tags python decorator
```

**Custom ID:**
```bash
# Specify custom ID
./snippet_manager.py add -t "Quick sort" -l python -f quicksort.py --id my-quicksort
```

### Listing & Searching

**List all snippets:**
```bash
# List all
./snippet_manager.py list

# Filter by language
./snippet_manager.py list -l python

# Filter by tags
./snippet_manager.py list --tags algorithm
```

**Search snippets:**
```bash
# Search by keyword
./snippet_manager.py search "docker"

# Search with filters
./snippet_manager.py search "algorithm" -l python
./snippet_manager.py search --tags web --language javascript

# Just filters (no query)
./snippet_manager.py search -l python --tags django
```

### Viewing Snippets

**Show full snippet:**
```bash
# Show with formatting
./snippet_manager.py show quicksort

# Show raw code only
./snippet_manager.py show quicksort --raw
```

### Exporting Snippets

```bash
# Export to file
./snippet_manager.py export quicksort output.py

# Export and run
./snippet_manager.py export quicksort script.sh && bash script.sh
```

### Updating Snippets

```bash
# Update title
./snippet_manager.py update quicksort -t "Optimized quick sort"

# Update code
./snippet_manager.py update quicksort -c "new code here"

# Update from file
./snippet_manager.py update quicksort -f updated_quicksort.py

# Update tags
./snippet_manager.py update quicksort --tags algorithm sorting python optimized

# Update description
./snippet_manager.py update quicksort -d "Highly optimized version"
```

### Deleting Snippets

```bash
# Delete with confirmation
./snippet_manager.py delete quicksort

# Delete without confirmation
./snippet_manager.py delete quicksort -y
```

### Statistics

```bash
# List all tags with counts
./snippet_manager.py tags

# List all languages with counts
./snippet_manager.py languages
```

## Output Examples

### List View
```
Found 3 snippet(s)

docker-compose-basic: Docker Compose Setup
  [yaml] #docker #devops
  Basic Docker compose configuration for web apps

quicksort: Quick Sort Algorithm
  [python] #algorithm #sorting
  Efficient implementation of quicksort

git-aliases: Useful Git Aliases
  [bash] #git #productivity
```

### Detailed View (show command)
```
quicksort: Quick Sort Algorithm
  [python] #algorithm #sorting
  Efficient implementation of quicksort

  Code:
    def quicksort(arr):
        if len(arr) <= 1:
            return arr
        pivot = arr[len(arr) // 2]
        left = [x for x in arr if x < pivot]
        middle = [x for x in arr if x == pivot]
        right = [x for x in arr if x > pivot]
        return quicksort(left) + middle + quicksort(right)

  Created: 2024-11-08 10:30
  Modified: 2024-11-08 14:20
```

### Tags View
```
Tags:
  #algorithm: 5
  #python: 4
  #web: 3
  #docker: 2
  #git: 2
```

### Languages View
```
Languages:
  python: 8
  javascript: 5
  bash: 3
  yaml: 2
```

## Advanced Usage

### Custom Storage Location
```bash
# Use custom storage file
./snippet_manager.py --storage ~/my-snippets.json add -t "Test" -l python -c "print('hello')"

# Team snippets (shared location)
./snippet_manager.py --storage /shared/team-snippets.json list
```

### Workflow Examples

**1. Quick reference:**
```bash
# Find and copy snippet
./snippet_manager.py show docker-run --raw > run.sh
bash run.sh
```

**2. Code templates:**
```bash
# Export template
./snippet_manager.py export flask-boilerplate app.py
# Edit and customize...
```

**3. Build snippet library:**
```bash
# Add commonly used patterns
for file in ~/code-templates/*.py; do
    name=$(basename "$file" .py)
    ./snippet_manager.py add -t "$name" -l python -f "$file" --tags template
done
```

**4. Share snippets:**
```bash
# Export specific snippets to share
./snippet_manager.py export useful-function function.py

# Or share entire collection
cp ~/.snippets.json ~/shared/snippets-backup.json
```

### Integration with Editor

**VSCode:**
```bash
# Export snippet in VSCode format
./snippet_manager.py show quicksort --raw > quicksort.code-snippets
```

**Vim:**
```bash
# Quick insert into vim
./snippet_manager.py show header --raw | vim -
```

## Command Reference

### Commands

- `add` - Add a new snippet
- `update` - Update an existing snippet
- `delete` - Delete a snippet
- `show` - Show snippet details
- `list` - List all snippets (with optional filters)
- `search` - Search snippets
- `export` - Export snippet to file
- `tags` - List all tags with counts
- `languages` - List all languages with counts

### Global Options

```
--storage PATH    Custom storage file location
--no-color        Disable colored output
--version         Show version
--help            Show help message
```

### Add/Update Options

```
-t, --title       Snippet title (required for add)
-l, --language    Programming language
-c, --code        Code content
-f, --file        Read code from file
-d, --description Description
--tags            Space-separated tags
--id              Custom snippet ID (add only)
```

### Search/List Options

```
query             Search query (optional)
-l, --language    Filter by language
--tags            Filter by tags
```

### Show Options

```
id                Snippet ID (required)
--raw             Show only code without formatting
```

### Delete Options

```
id                Snippet ID (required)
-y, --yes         Skip confirmation prompt
```

## Storage Format

Snippets are stored in JSON format (`~/.snippets.json`):

```json
[
  {
    "id": "quicksort",
    "title": "Quick Sort Algorithm",
    "code": "def quicksort(arr): ...",
    "language": "python",
    "description": "Efficient implementation",
    "tags": ["algorithm", "sorting"],
    "created": "2024-11-08T10:30:00",
    "modified": "2024-11-08T14:20:00"
  }
]
```

## Tips

1. **Use descriptive titles** - Makes searching easier
2. **Tag generously** - Better organization and discoverability
3. **Add descriptions** - Future you will thank you
4. **Consistent language names** - Use "python" not "Python" or "py"
5. **Export backups** - Copy ~/.snippets.json periodically
6. **Team sharing** - Use shared storage location for team snippets

## Common Use Cases

**Developer Cheat Sheet:**
```bash
./snippet_manager.py add -t "Git rebase" -l bash -c "git rebase -i HEAD~3" --tags git
./snippet_manager.py add -t "Docker cleanup" -l bash -c "docker system prune -af" --tags docker
./snippet_manager.py add -t "Python venv" -l bash -c "python -m venv venv && source venv/bin/activate" --tags python
```

**Algorithm Library:**
```bash
./snippet_manager.py add -t "Binary search" -l python -f binary_search.py --tags algorithm search
./snippet_manager.py add -t "DFS" -l python -f dfs.py --tags algorithm graph
```

**Config Templates:**
```bash
./snippet_manager.py add -t "Nginx config" -l nginx -f nginx.conf --tags devops web
./snippet_manager.py add -t "Docker compose" -l yaml -f docker-compose.yml --tags docker
```

## Exit Codes

- `0` - Success
- `1` - Error (not found, invalid arguments, etc.)
- `130` - Cancelled by user

## Author

Vishal Kumar

## License

MIT
