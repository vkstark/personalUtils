#!/usr/bin/env python3
"""
DataConvert - Universal Data Format Converter
Convert between JSON, YAML, CSV, XML, TOML, and more with validation.

Author: Vishal Kumar
License: MIT
"""

import os
import sys
import argparse
import json
import csv
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from io import StringIO

# Try to import optional dependencies
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    import toml
    TOML_AVAILABLE = True
except ImportError:
    try:
        import tomli as toml
        import tomli_w
        TOML_AVAILABLE = True
    except ImportError:
        TOML_AVAILABLE = False

# Color codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    # Text colors
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'

    # Bright colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_CYAN = '\033[96m'

class DataConverter:
    """Universal data format converter"""

    def __init__(self, colors: bool = True, pretty: bool = True, validate: bool = True):
        self.colors = colors and self._supports_color()
        self.pretty = pretty
        self.validate = validate

    def _supports_color(self) -> bool:
        """Check if terminal supports color output"""
        return (hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
                os.getenv('TERM') != 'dumb')

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled"""
        if not self.colors:
            return text
        return f"{color}{text}{Colors.RESET}"

    def detect_format(self, filepath: str) -> Optional[str]:
        """Detect file format from extension"""
        ext = Path(filepath).suffix.lower()
        format_map = {
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.csv': 'csv',
            '.xml': 'xml',
            '.toml': 'toml'
        }
        return format_map.get(ext)

    def read_file(self, filepath: str, format: Optional[str] = None) -> Any:
        """Read and parse file"""
        if format is None:
            format = self.detect_format(filepath)
            if format is None:
                raise ValueError(f"Cannot detect format for {filepath}")

        print(self._colorize(f"Reading {format.upper()} file: {filepath}", Colors.CYAN))

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        if format == 'json':
            return self._parse_json(content)
        elif format == 'yaml':
            return self._parse_yaml(content)
        elif format == 'csv':
            return self._parse_csv(content)
        elif format == 'xml':
            return self._parse_xml(content)
        elif format == 'toml':
            return self._parse_toml(content)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def write_file(self, data: Any, filepath: str, format: Optional[str] = None):
        """Write data to file in specified format"""
        if format is None:
            format = self.detect_format(filepath)
            if format is None:
                raise ValueError(f"Cannot detect format for {filepath}")

        print(self._colorize(f"Writing {format.upper()} file: {filepath}", Colors.CYAN))

        if format == 'json':
            content = self._to_json(data)
        elif format == 'yaml':
            content = self._to_yaml(data)
        elif format == 'csv':
            content = self._to_csv(data)
        elif format == 'xml':
            content = self._to_xml(data)
        elif format == 'toml':
            content = self._to_toml(data)
        else:
            raise ValueError(f"Unsupported format: {format}")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(self._colorize(f"✓ Successfully wrote to {filepath}", Colors.GREEN))

    # JSON handlers
    def _parse_json(self, content: str) -> Any:
        """Parse JSON string"""
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    def _to_json(self, data: Any) -> str:
        """Convert data to JSON string"""
        if self.pretty:
            return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
        else:
            return json.dumps(data, ensure_ascii=False)

    # YAML handlers
    def _parse_yaml(self, content: str) -> Any:
        """Parse YAML string"""
        if not YAML_AVAILABLE:
            raise ValueError("PyYAML is not installed. Install with: pip install pyyaml")
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")

    def _to_yaml(self, data: Any) -> str:
        """Convert data to YAML string"""
        if not YAML_AVAILABLE:
            raise ValueError("PyYAML is not installed. Install with: pip install pyyaml")
        return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=True)

    # CSV handlers
    def _parse_csv(self, content: str) -> List[Dict]:
        """Parse CSV string"""
        try:
            reader = csv.DictReader(StringIO(content))
            return list(reader)
        except Exception as e:
            raise ValueError(f"Invalid CSV: {e}")

    def _to_csv(self, data: Any) -> str:
        """Convert data to CSV string"""
        if not isinstance(data, list):
            raise ValueError("CSV conversion requires a list of dictionaries")

        if not data:
            return ""

        # Handle list of dicts
        if isinstance(data[0], dict):
            output = StringIO()
            fieldnames = data[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            return output.getvalue()
        else:
            raise ValueError("CSV conversion requires a list of dictionaries")

    # XML handlers
    def _parse_xml(self, content: str) -> Dict:
        """Parse XML string"""
        try:
            root = ET.fromstring(content)
            return self._xml_to_dict(root)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")

    def _xml_to_dict(self, element: ET.Element) -> Dict:
        """Convert XML element to dictionary"""
        result = {}

        # Add attributes
        if element.attrib:
            result['@attributes'] = element.attrib

        # Add text content
        if element.text and element.text.strip():
            result['@text'] = element.text.strip()

        # Add child elements
        children = {}
        for child in element:
            child_data = self._xml_to_dict(child)
            tag = child.tag

            if tag in children:
                # Multiple children with same tag - convert to list
                if not isinstance(children[tag], list):
                    children[tag] = [children[tag]]
                children[tag].append(child_data)
            else:
                children[tag] = child_data

        if children:
            result.update(children)

        # If result only has @text, return just the text
        if result.keys() == {'@text'}:
            return result['@text']

        return result if result else None

    def _to_xml(self, data: Any, root_name: str = 'root') -> str:
        """Convert data to XML string"""
        root = ET.Element(root_name)
        self._dict_to_xml(data, root)

        if self.pretty:
            rough_string = ET.tostring(root, encoding='unicode')
            reparsed = minidom.parseString(rough_string)
            return reparsed.toprettyxml(indent="  ")
        else:
            return ET.tostring(root, encoding='unicode')

    def _dict_to_xml(self, data: Any, parent: ET.Element):
        """Convert dictionary to XML elements"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key == '@attributes':
                    parent.attrib.update(value)
                elif key == '@text':
                    parent.text = str(value)
                elif isinstance(value, list):
                    for item in value:
                        child = ET.SubElement(parent, key)
                        self._dict_to_xml(item, child)
                else:
                    child = ET.SubElement(parent, key)
                    self._dict_to_xml(value, child)
        elif isinstance(data, list):
            for item in data:
                child = ET.SubElement(parent, 'item')
                self._dict_to_xml(item, child)
        else:
            parent.text = str(data)

    # TOML handlers
    def _parse_toml(self, content: str) -> Dict:
        """Parse TOML string"""
        if not TOML_AVAILABLE:
            raise ValueError("TOML library is not installed. Install with: pip install toml or tomli")
        try:
            if hasattr(toml, 'loads'):
                return toml.loads(content)
            else:
                # Using tomli
                return toml.loads(content)
        except Exception as e:
            raise ValueError(f"Invalid TOML: {e}")

    def _to_toml(self, data: Any) -> str:
        """Convert data to TOML string"""
        if not TOML_AVAILABLE:
            raise ValueError("TOML library is not installed. Install with: pip install toml or tomli-w")

        if not isinstance(data, dict):
            raise ValueError("TOML conversion requires a dictionary")

        try:
            if hasattr(toml, 'dumps'):
                return toml.dumps(data)
            else:
                # Using tomli_w
                output = StringIO()
                tomli_w.dump(data, output)
                return output.getvalue()
        except Exception as e:
            raise ValueError(f"Cannot convert to TOML: {e}")

    def convert(self, input_file: str, output_file: str,
                input_format: Optional[str] = None,
                output_format: Optional[str] = None):
        """Convert file from one format to another"""
        # Read input
        data = self.read_file(input_file, input_format)

        # Validate if enabled
        if self.validate:
            self._validate_data(data, output_format or self.detect_format(output_file))

        # Write output
        self.write_file(data, output_file, output_format)

    def _validate_data(self, data: Any, format: str):
        """Validate data for target format"""
        if format == 'csv':
            if not isinstance(data, list):
                raise ValueError("CSV format requires data to be a list of dictionaries")
            if data and not isinstance(data[0], dict):
                raise ValueError("CSV format requires list of dictionaries")

        elif format == 'toml':
            if not isinstance(data, dict):
                raise ValueError("TOML format requires data to be a dictionary")

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="DataConvert - Universal Data Format Converter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported Formats:
  - JSON (.json)
  - YAML (.yaml, .yml)  [requires: pip install pyyaml]
  - CSV  (.csv)
  - XML  (.xml)
  - TOML (.toml)        [requires: pip install toml or tomli tomli-w]

Examples:
  # Auto-detect formats from extensions
  %(prog)s data.json output.yaml

  # Explicit format specification
  %(prog)s -i json -o yaml data.txt output.txt

  # Convert with validation
  %(prog)s --validate config.yaml config.toml

  # Minified output
  %(prog)s --no-pretty data.yaml output.json

  # Convert CSV to JSON
  %(prog)s users.csv users.json

  # Multiple conversions
  for file in *.json; do
      %(prog)s "$file" "$${file%%.json}.yaml"
  done
        """)

    parser.add_argument('input', help='Input file path')
    parser.add_argument('output', help='Output file path')

    # Format options
    parser.add_argument('-i', '--input-format',
                       choices=['json', 'yaml', 'csv', 'xml', 'toml'],
                       help='Input format (auto-detected from extension if not specified)')
    parser.add_argument('-o', '--output-format',
                       choices=['json', 'yaml', 'csv', 'xml', 'toml'],
                       help='Output format (auto-detected from extension if not specified)')

    # Conversion options
    parser.add_argument('--no-pretty', action='store_true',
                       help='Disable pretty printing/formatting')
    parser.add_argument('--no-validate', action='store_true',
                       help='Skip data validation')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')

    # XML-specific options
    parser.add_argument('--xml-root', default='root',
                       help='Root element name for XML output (default: root)')

    # Version
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')

    args = parser.parse_args()

    try:
        # Create converter
        converter = DataConverter(
            colors=not args.no_color,
            pretty=not args.no_pretty,
            validate=not args.no_validate
        )

        # Convert
        converter.convert(
            args.input,
            args.output,
            args.input_format,
            args.output_format
        )

        if not args.no_color:
            print(f"{Colors.BRIGHT_GREEN}✓ Conversion completed successfully!{Colors.RESET}")
        else:
            print("\n✓ Conversion completed successfully!")

    except FileNotFoundError as e:
        print(f"Error: File not found: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
