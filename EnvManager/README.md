# EnvManager - .env File Management Tool

Manage, validate, and switch between multiple .env files with templates, comparison, and validation.

## Features

- **File Management**
  - List variables with optional value hiding
  - Compare two .env files
  - Merge multiple .env files
  - Switch between environments

- **Validation**
  - Check for required variables
  - Pattern validation with regex
  - Detect empty values
  - Comprehensive error reporting

- **Templates**
  - Generate .env.example from .env
  - Automatic comment generation
  - Value structure preservation

- **Statistics**
  - Variable counts
  - Key/value length analysis
  - Empty variable detection

## Installation

```bash
chmod +x env_manager.py
# Optional: Create symlink
ln -s $(pwd)/env_manager.py ~/bin/envman
```

## Usage

### List Variables

**Show all variables:**
```bash
# Show with values
./env_manager.py list .env

# Hide sensitive values
./env_manager.py list .env --hide-values

# Filter by pattern
./env_manager.py list .env --filter "DB_"
./env_manager.py list .env --filter "API.*KEY"
```

### Compare Files

**Compare environments:**
```bash
# Compare development and production
./env_manager.py compare .env.dev .env.prod

# Compare local and example
./env_manager.py compare .env .env.example
```

### Validate Files

**Check requirements:**
```bash
# Check for required variables
./env_manager.py validate .env --required DB_HOST DB_PORT API_KEY

# Validate with patterns
./env_manager.py validate .env --required DB_HOST \
  --pattern "DB_PORT:^[0-9]+$" "API_KEY:^sk-[a-zA-Z0-9]+$"

# Combine multiple checks
./env_manager.py validate .env \
  --required DB_HOST DB_PORT DB_NAME DB_USER DB_PASS \
  --pattern "DB_PORT:^[0-9]{4,5}$" "EMAIL:.*@.*"
```

### Create Templates

**Generate .env.example:**
```bash
# Remove values, add comments
./env_manager.py template .env .env.example

# Keep values (for documentation)
./env_manager.py template .env .env.template --keep-values

# Without comments
./env_manager.py template .env .env.example --no-comments
```

### Merge Files

**Combine multiple .env files:**
```bash
# Merge base + environment-specific
./env_manager.py merge .env.base .env.dev -o .env

# Last file wins (default)
./env_manager.py merge .env.defaults .env.local -o .env --priority last

# First file wins
./env_manager.py merge .env.defaults .env.local -o .env --priority first

# Merge multiple environments
./env_manager.py merge .env.base .env.dev .env.local -o .env
```

### Switch Environments

**Swap .env files:**
```bash
# Switch to production (creates backup)
./env_manager.py switch .env.production

# Switch without backup
./env_manager.py switch .env.dev --no-backup

# Custom target
./env_manager.py switch .env.staging -t .env.custom
```

### Statistics

```bash
# Get file statistics
./env_manager.py stats .env
```

## Output Examples

### List Command
```
Variables:
  DB_HOST=localhost
  DB_PORT=5432
  DB_NAME=myapp
  API_KEY=sk-1234567890
  DEBUG=true

Total: 5 variables
```

### Compare Command
```
Comparison Results:

Only in .env.dev:
  - DEBUG
  - LOG_LEVEL

Only in .env.prod:
  + REDIS_URL
  + CACHE_TTL

Different values:
  ~ DB_HOST
  ~ API_URL

Same values:
  2 variables
```

### Validate Command
```
✗ Validation failed:
  - Missing required variable: API_KEY
  - Empty value for required variable: DB_HOST
  - Invalid format for DB_PORT: does not match pattern ^[0-9]+$
```

### Stats Command
```
Statistics:
  Total variables: 15
  Non-empty: 14
  Empty: 1
  Avg key length: 12.3
  Avg value length: 24.7
  Longest key: DATABASE_CONNECTION_STRING
```

## Common Workflows

### Project Setup

**1. Create template for new developers:**
```bash
# Generate .env.example without secrets
./env_manager.py template .env .env.example

# Add to git
git add .env.example
git commit -m "Add environment template"
```

**2. Validate before deployment:**
```bash
# Check production environment
./env_manager.py validate .env.production \
  --required DB_HOST DB_PORT API_KEY SECRET_KEY \
  --pattern "DB_PORT:^[0-9]{4,5}$"

# Use in CI/CD
if ! ./env_manager.py validate .env.prod --required API_KEY DB_URL; then
    echo "Environment validation failed!"
    exit 1
fi
```

**3. Multi-environment management:**
```bash
# Base configuration + environment-specific
./env_manager.py merge .env.base .env.dev -o .env.development
./env_manager.py merge .env.base .env.prod -o .env.production

# Quick switch
./env_manager.py switch .env.development
```

### Development Workflow

**1. Share configuration:**
```bash
# Create sanitized template
./env_manager.py template .env .env.team --keep-values --no-comments

# Team members can customize
cp .env.team .env
# Edit .env with personal values
```

**2. Environment comparison:**
```bash
# Check differences before deployment
./env_manager.py compare .env.staging .env.production

# Identify missing variables
./env_manager.py compare .env .env.example
```

**3. Automated validation:**
```bash
#!/bin/bash
# pre-commit hook
./env_manager.py validate .env --required \
  DATABASE_URL \
  SECRET_KEY \
  API_KEY \
  --pattern "DATABASE_URL:^postgres://.*" \
  --pattern "SECRET_KEY:^.{32,}$"
```

## .env File Format

EnvManager supports standard .env format:

```bash
# Database configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=myapp

# API Keys
API_KEY=sk-1234567890
SECRET_KEY="my secret key with spaces"

# Feature flags
DEBUG=true
ENABLE_CACHE=false

# URLs
API_URL=https://api.example.com
REDIS_URL='redis://localhost:6379/0'
```

**Supported features:**
- Comments (lines starting with #)
- Empty lines (ignored)
- Single and double quotes for values
- Values with spaces (must be quoted)
- Standard KEY=VALUE format

## Validation Patterns

Common regex patterns for validation:

```bash
# Port number
--pattern "PORT:^[0-9]{2,5}$"

# URL
--pattern "API_URL:^https?://.*"

# Email
--pattern "EMAIL:^[^@]+@[^@]+\.[^@]+$"

# UUID
--pattern "UUID:^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

# API Key (custom format)
--pattern "API_KEY:^sk-[a-zA-Z0-9]{32}$"

# Boolean
--pattern "DEBUG:^(true|false)$"

# Alphanumeric only
--pattern "USERNAME:^[a-zA-Z0-9]+$"
```

## Command Reference

### Commands

- `list` - List variables in .env file
- `compare` - Compare two .env files
- `validate` - Validate .env file
- `template` - Create template from .env file
- `merge` - Merge multiple .env files
- `switch` - Switch to different .env file
- `stats` - Show statistics about .env file

### Global Options

```
--no-color        Disable colored output
-v, --verbose     Verbose output
--version         Show version
--help            Show help message
```

### List Options

```
file              .env file to list
--hide-values     Hide variable values (show as ***)
--filter PATTERN  Filter variables by regex pattern
```

### Compare Options

```
file1             First .env file
file2             Second .env file
```

### Validate Options

```
file              .env file to validate
--required VAR [VAR ...]
                  Required variables
--pattern VAR:REGEX [VAR:REGEX ...]
                  Validation patterns
```

### Template Options

```
input             Input .env file
output            Output template file
--keep-values     Keep original values
--no-comments     Do not add comments
```

### Merge Options

```
files             .env files to merge
-o, --output      Output file (required)
--priority {first,last}
                  Priority for duplicate keys
```

### Switch Options

```
source            Source .env file
-t, --target      Target file (default: .env)
--no-backup       Do not create backup
```

## Tips

1. **Always validate** before deployment
2. **Use templates** for onboarding new developers
3. **Version control** .env.example, not .env
4. **Compare files** before switching environments
5. **Backup automatically** (enabled by default in switch)
6. **Use patterns** for security-critical variables
7. **Merge carefully** - check priority settings
8. **Hide sensitive values** when sharing screenshots

## Security Best Practices

1. **Never commit .env** to version control
2. **Use strong validation** for API keys and secrets
3. **Rotate secrets** regularly
4. **Use .env.example** for documentation
5. **Encrypt production** .env files in storage
6. **Audit who has access** to production secrets
7. **Use environment-specific** files (.env.dev, .env.prod)

## Exit Codes

- `0` - Success
- `1` - Error or validation failed
- `130` - Cancelled by user

## Author

Vishal Kumar

## License

MIT
