# ImportOptimizer - Python Import Optimizer

Find unused imports and organize import statements in Python files following PEP 8 guidelines.

## Features

- **Find Unused Imports**
  - Detect imports that are never used
  - File and directory scanning
  - Recursive search support

- **Organize Imports**
  - Group by stdlib, third-party, and local
  - Sort alphabetically
  - PEP 8 compliant formatting

- **Smart Analysis**
  - AST-based parsing
  - Handles aliases
  - Detects attribute access

## Installation

```bash
chmod +x import_optimizer.py
# Optional: Create symlink
ln -s $(pwd)/import_optimizer.py ~/bin/impopt
```

## Usage

### Find Unused Imports

**Single file:**
```bash
# Check one file
./import_optimizer.py unused script.py
```

**Directory:**
```bash
# Check all Python files
./import_optimizer.py unused /path/to/project -r

# Current directory
./import_optimizer.py unused . -r
```

### Organize Imports

```bash
# Show how imports should be organized
./import_optimizer.py organize script.py
```

## Output Examples

### Unused Imports
```
Unused imports:
  json (line 3)
  sys (line 2)
  unused_function (line 15)
```

### Directory Scan
```
Found unused imports in 3 file(s):

src/main.py
  - json (line 5)
  - tempfile (line 8)

src/utils.py
  - sys (line 2)

tests/test_main.py
  - pytest (line 1)
```

### Organized Imports
```
Organized Imports:

# Standard library
import json
import os
import sys
from pathlib import Path
from typing import Dict, List

# Third-party
import requests
from flask import Flask, request

# Local
from .utils import helper
from .models import User
```

## Tips

1. **Run before commits** to keep code clean
2. **Use in CI/CD** to enforce import hygiene
3. **Combine with formatters** like black or isort
4. **Review suggestions** before removing imports

## Limitations

- May not detect dynamic imports
- String-based imports not analyzed
- Some complex usage patterns might be missed

## Exit Codes

- `0` - Success
- `1` - Error

## Author

Vishal Kumar

## License

MIT
