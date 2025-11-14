# DuplicateFinder - Find Duplicate Files

Find and remove duplicate files using hash comparison, filename matching, or find empty files to free up disk space.

## Features

- **Multiple Detection Methods**
  - Hash-based (MD5, SHA1, SHA256)
  - Filename-based
  - Empty file detection

- **Smart Filtering**
  - Minimum/maximum file size
  - File extension filtering
  - Directory exclusion

- **Safe Deletion**
  - Dry-run mode
  - Interactive confirmation
  - Keep policies (first, last, shortest, longest path)
  - Automatic statistics

- **Performance**
  - Size-based pre-filtering
  - Efficient hash calculation
  - Progress indicators

## Installation

```bash
chmod +x duplicate_finder.py
# Optional: Create symlink
ln -s $(pwd)/duplicate_finder.py ~/bin/dupfinder
```

## Usage

### Find Duplicates

**Basic usage:**
```bash
# Current directory
./duplicate_finder.py .

# Specific directory
./duplicate_finder.py /path/to/dir

# Multiple paths
./duplicate_finder.py ~/Documents ~/Pictures
```

**Recursive scan:**
```bash
# Scan subdirectories
./duplicate_finder.py . --recursive

# Short form
./duplicate_finder.py . -r
```

### Detection Methods

**By hash (default):**
```bash
# MD5 hash (default, fast)
./duplicate_finder.py .

# SHA256 (more secure)
./duplicate_finder.py . --algorithm sha256

# SHA1
./duplicate_finder.py . --algorithm sha1
```

**By filename:**
```bash
# Case-insensitive (default)
./duplicate_finder.py . --by-name

# Case-sensitive
./duplicate_finder.py . --by-name --case-sensitive
```

**Empty files:**
```bash
./duplicate_finder.py . --empty
```

### Filtering

**By size:**
```bash
# Files larger than 1MB
./duplicate_finder.py . --min-size 1048576

# Files smaller than 100MB
./duplicate_finder.py . --max-size 104857600

# Between 1MB and 100MB
./duplicate_finder.py . --min-size 1048576 --max-size 104857600
```

**By extension:**
```bash
# Images only
./duplicate_finder.py . --extensions .jpg .jpeg .png .gif

# Videos
./duplicate_finder.py . --extensions .mp4 .avi .mkv .mov

# Documents
./duplicate_finder.py . --extensions .pdf .doc .docx .txt
```

**Exclude directories:**
```bash
# Exclude specific directories
./duplicate_finder.py . --exclude-dirs .git node_modules build

# Default excludes: .git, __pycache__, node_modules
```

### Deleting Duplicates

**Dry run first (recommended):**
```bash
# See what would be deleted
./duplicate_finder.py . --delete --dry-run

# With keep policy
./duplicate_finder.py . --delete --dry-run --keep first
```

**Safe deletion:**
```bash
# Interactive mode (confirm each deletion)
./duplicate_finder.py . --delete --interactive

# Keep first occurrence (default)
./duplicate_finder.py . --delete

# Keep last occurrence
./duplicate_finder.py . --delete --keep last

# Keep shortest path
./duplicate_finder.py . --delete --keep shortest

# Keep longest path
./duplicate_finder.py . --delete --keep longest
```

## Output Examples

### Duplicate Files
```
Scanning 1250 files...

Found 3 set(s) of duplicates:

1. Name: IMG_1234.jpg (2.5MB, 2 files)
   [K] /home/user/Photos/IMG_1234.jpg
   [D] /home/user/Backup/Photos/IMG_1234.jpg

2. Name: document.pdf (1.2MB, 3 files)
   [K] /home/user/Documents/document.pdf
   [D] /home/user/Downloads/document.pdf
   [D] /home/user/Desktop/document.pdf

3. Name: video.mp4 (45.0MB, 2 files)
   [K] /home/user/Videos/video.mp4
   [D] /home/user/Old/video.mp4

📊 Statistics:
  Total files scanned: 1250
  Total size: 25.3GB
  Unique files: 1245
  Duplicate files: 5
  Wasted space: 48.7MB
  Waste percentage: 0.2%
```

### Empty Files
```
Found 5 empty file(s):
  /home/user/test1.txt
  /home/user/test2.log
  /home/user/cache/temp.dat
  /home/user/old/empty.json
  /home/user/.placeholder
```

### Deletion (Dry Run)
```
Keeping: /home/user/Photos/IMG_1234.jpg
  [DRY RUN] Would delete: /home/user/Backup/Photos/IMG_1234.jpg

Keeping: /home/user/Documents/document.pdf
  [DRY RUN] Would delete: /home/user/Downloads/document.pdf
  [DRY RUN] Would delete: /home/user/Desktop/document.pdf

✓ Would delete 3 file(s)
```

## Common Use Cases

### Clean Up Downloads
```bash
# Find duplicate downloads
./duplicate_finder.py ~/Downloads -r

# Delete duplicates (dry run first)
./duplicate_finder.py ~/Downloads -r --delete --dry-run
./duplicate_finder.py ~/Downloads -r --delete --keep first
```

### Photo Library Cleanup
```bash
# Find duplicate photos
./duplicate_finder.py ~/Pictures -r --extensions .jpg .jpeg .png .heic

# With size filter (only large files)
./duplicate_finder.py ~/Pictures -r --min-size 1048576 --extensions .jpg .png

# Interactive deletion
./duplicate_finder.py ~/Pictures -r --delete --interactive --extensions .jpg
```

### Free Up Disk Space
```bash
# Find large duplicates
./duplicate_finder.py . -r --min-size 10485760  # 10MB+

# Find duplicate videos
./duplicate_finder.py . -r --extensions .mp4 .avi .mkv --min-size 52428800  # 50MB+
```

### Backup Verification
```bash
# Compare original and backup
./duplicate_finder.py ~/Documents ~/Backup/Documents

# Find files only in backup (possible orphans)
./duplicate_finder.py ~/Backup --by-name
```

### Clean Empty Files
```bash
# Find and list empty files
./duplicate_finder.py . -r --empty

# Manually review and delete if needed
```

## Command Line Options

```
positional arguments:
  paths                 Paths to scan

scan options:
  -r, --recursive       Scan directories recursively
  --by-name             Find duplicates by filename
  --empty               Find empty files
  --case-sensitive      Case-sensitive filename matching

filter options:
  --min-size BYTES      Minimum file size
  --max-size BYTES      Maximum file size
  --extensions EXT [EXT ...]
                        Filter by extensions
  --exclude-dirs DIR [DIR ...]
                        Exclude directories

hash options:
  --algorithm {md5,sha1,sha256}
                        Hash algorithm (default: md5)

delete options:
  --delete              Delete duplicate files
  --keep {first,last,shortest,longest}
                        Which file to keep (default: first)
  --dry-run             Preview deletions
  -i, --interactive     Confirm each deletion

display options:
  --show-hash           Show file hashes
  --no-color            Disable colored output
  -v, --verbose         Verbose output
  --version             Show version
```

## Keep Policies

- **first** - Keep the first file found (default)
- **last** - Keep the last file found
- **shortest** - Keep file with shortest path
- **longest** - Keep file with longest path

## Safety Features

1. **Dry run by default** when using `--delete`
2. **Interactive mode** for manual confirmation
3. **Clear indicators** `[K]` for kept files, `[D]` for duplicates
4. **Statistics** before deletion
5. **Error handling** for locked/protected files

## Performance Tips

1. **Use --min-size** to skip small files (they're usually not worth it)
2. **Filter by extension** to focus on specific file types
3. **Use MD5** for speed, SHA256 for security
4. **Exclude unnecessary directories** (.git, node_modules, etc.)

## Exit Codes

- `0` - Success
- `1` - Error
- `130` - Cancelled by user

## Warnings

⚠️ **Always use --dry-run first!**
⚠️ **Review the list before actual deletion!**
⚠️ **Consider backups before mass deletion!**
⚠️ **Be careful with --keep policies!**

## Author

Vishal Kumar

## License

MIT
