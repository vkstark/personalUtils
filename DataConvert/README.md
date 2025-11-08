# DataConvert - Universal Data Format Converter

Convert seamlessly between JSON, YAML, CSV, XML, and TOML with validation and pretty printing.

## Features

- **Multiple Format Support**
  - JSON (.json)
  - YAML (.yaml, .yml)
  - CSV (.csv)
  - XML (.xml)
  - TOML (.toml)

- **Smart Conversion**
  - Auto-detect formats from file extensions
  - Explicit format specification
  - Data validation
  - Pretty printing

- **Robust Handling**
  - Error handling and validation
  - Encoding support
  - Structure preservation

## Installation

```bash
chmod +x data_convert.py

# Install optional dependencies
pip install pyyaml        # For YAML support
pip install toml          # For TOML support (Python < 3.11)
# or
pip install tomli tomli-w # Alternative TOML library
```

## Usage

### Auto-detect Formats
The tool automatically detects formats from file extensions:

```bash
# JSON to YAML
./data_convert.py config.json config.yaml

# YAML to JSON
./data_convert.py settings.yaml settings.json

# JSON to XML
./data_convert.py data.json data.xml

# CSV to JSON
./data_convert.py users.csv users.json

# TOML to JSON
./data_convert.py config.toml config.json
```

### Explicit Format Specification
Specify input/output formats explicitly:

```bash
# When files don't have standard extensions
./data_convert.py -i json -o yaml input.txt output.txt

# Force format interpretation
./data_convert.py --input-format yaml --output-format json config config.txt
```

### Conversion Options

**Pretty Printing:**
```bash
# Disable pretty printing (minified output)
./data_convert.py --no-pretty data.yaml output.json

# Default is pretty printed
./data_convert.py data.json output.yaml
```

**Validation:**
```bash
# Skip validation (faster but less safe)
./data_convert.py --no-validate large.json output.yaml

# Default validates data before conversion
./data_convert.py data.json output.csv
```

**Output Options:**
```bash
# Disable colored output
./data_convert.py --no-color data.json output.yaml
```

## Format-Specific Notes

### JSON ↔ YAML
Perfect bidirectional conversion:
```bash
./data_convert.py config.json config.yaml
./data_convert.py config.yaml config.json
```

### JSON/YAML → CSV
Requires data to be a list of dictionaries:
```bash
# Valid data structure:
[
  {"name": "Alice", "age": 30},
  {"name": "Bob", "age": 25}
]

./data_convert.py users.json users.csv
```

### CSV → JSON/YAML
Automatically converts to list of dictionaries:
```bash
./data_convert.py data.csv data.json
./data_convert.py data.csv data.yaml
```

### XML Conversion
XML uses special keys for attributes and text:
- `@attributes` for element attributes
- `@text` for text content

```bash
./data_convert.py data.json data.xml
./data_convert.py data.xml data.json
```

### TOML Conversion
TOML requires dict structure (not lists):
```bash
# Valid for TOML
{
  "database": {
    "host": "localhost",
    "port": 5432
  }
}

./data_convert.py config.json config.toml
```

## Examples

### Configuration File Conversion
```bash
# Convert application config
./data_convert.py app_config.yaml app_config.json

# Generate TOML from JSON
./data_convert.py settings.json settings.toml
```

### Data Export/Import
```bash
# Export database query results to different formats
./data_convert.py query_results.json query_results.csv
./data_convert.py query_results.json query_results.xml
```

### Batch Conversion
```bash
# Convert all JSON files to YAML
for file in *.json; do
    ./data_convert.py "$file" "${file%.json}.yaml"
done

# Convert all YAML to TOML
for file in *.yaml; do
    ./data_convert.py "$file" "${file%.yaml}.toml"
done
```

### Pipeline Integration
```bash
# Convert and process
./data_convert.py input.json output.yaml && cat output.yaml

# Chain with other tools
curl https://api.example.com/data > data.json
./data_convert.py data.json data.csv
```

## Command Line Options

```
positional arguments:
  input                 Input file path
  output                Output file path

format options:
  -i, --input-format   Input format (json|yaml|csv|xml|toml)
  -o, --output-format  Output format (json|yaml|csv|xml|toml)

conversion options:
  --no-pretty          Disable pretty printing/formatting
  --no-validate        Skip data validation
  --no-color           Disable colored output
  --xml-root NAME      Root element name for XML output (default: root)

other:
  --version            Show version and exit
  -h, --help           Show help message
```

## Data Structure Examples

### JSON
```json
{
  "name": "Example",
  "version": "1.0",
  "features": ["fast", "reliable"]
}
```

### YAML
```yaml
name: Example
version: '1.0'
features:
  - fast
  - reliable
```

### CSV
```csv
name,age,city
Alice,30,NYC
Bob,25,LA
```

### XML
```xml
<root>
  <name>Example</name>
  <version>1.0</version>
  <features>
    <item>fast</item>
    <item>reliable</item>
  </features>
</root>
```

### TOML
```toml
name = "Example"
version = "1.0"
features = ["fast", "reliable"]
```

## Error Handling

The tool provides clear error messages:

```bash
# Invalid input file
$ ./data_convert.py missing.json output.yaml
Error: File not found: missing.json

# Invalid data structure for format
$ ./data_convert.py list.json output.toml
Error: TOML format requires data to be a dictionary

# Invalid input data
$ ./data_convert.py bad.json output.yaml
Error: Invalid JSON: Expecting value: line 1 column 1 (char 0)
```

## Dependencies

- **Core**: Python 3.6+ (no extra dependencies for JSON, CSV, XML)
- **YAML**: `pip install pyyaml`
- **TOML**: `pip install toml` or `pip install tomli tomli-w`

## Limitations

1. **CSV**: Can only represent flat list of dictionaries
2. **TOML**: Requires dictionary at root level
3. **XML**: Attribute and text handling uses special keys
4. **Complex Objects**: Custom classes may not convert properly

## Tips

- Always validate your data when converting to stricter formats (CSV, TOML)
- Use `--no-validate` only when you're certain about data structure
- Pretty printing is enabled by default for readability
- Check file extension - it's used for auto-detection

## Exit Codes

- `0` - Success
- `1` - Error (file not found, invalid format, conversion failed)

## Author

Vishal Kumar

## License

MIT
