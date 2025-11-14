"""
Tests for DataConvert utility
"""
import pytest
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.DataConvert.data_convert import DataConverter


class TestDataConverter:
    """Test cases for DataConverter"""

    @pytest.fixture
    def converter(self):
        """Create DataConverter instance"""
        return DataConverter(colors=False, pretty=True)

    def test_json_to_dict(self, converter, sample_json_file):
        """Test parsing JSON file"""
        data = converter.read_file(str(sample_json_file), format='json')

        assert isinstance(data, dict)
        assert 'name' in data

    def test_json_parsing(self, converter):
        """Test JSON string parsing"""
        json_str = '{"key": "value", "number": 42}'
        result = converter._parse_json(json_str)

        assert result['key'] == 'value'
        assert result['number'] == 42

    def test_json_to_json_conversion(self, converter, temp_dir):
        """Test JSON to JSON roundtrip"""
        input_file = temp_dir / "input.json"
        output_file = temp_dir / "output.json"

        test_data = {"test": "data", "value": 123}
        input_file.write_text(json.dumps(test_data))

        converter.convert(str(input_file), str(output_file), 'json', 'json')

        assert output_file.exists()

        # Verify content
        output_data = json.loads(output_file.read_text())
        assert output_data == test_data

    def test_format_detection(self, converter):
        """Test automatic format detection from extension"""
        assert converter.detect_format("test.json") == "json"
        assert converter.detect_format("test.yaml") == "yaml"
        assert converter.detect_format("test.yml") == "yaml"
        assert converter.detect_format("test.csv") == "csv"
        assert converter.detect_format("test.xml") == "xml"
        assert converter.detect_format("test.toml") == "toml"

    def test_invalid_json(self, converter):
        """Test error handling for invalid JSON"""
        invalid_json = '{"key": invalid}'

        with pytest.raises(ValueError):
            converter._parse_json(invalid_json)

    def test_csv_structure_validation(self, converter, temp_dir):
        """Test CSV validation (requires list of dicts)"""
        output_file = temp_dir / "output.csv"

        # Valid data (list of dicts)
        valid_data = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]

        # This should work
        csv_output = converter._to_csv(valid_data)
        assert "name,age" in csv_output

    def test_pretty_json_output(self, converter):
        """Test pretty-printed JSON output"""
        data = {"key": "value"}

        pretty_output = converter._to_json(data)

        assert "\n" in pretty_output  # Pretty printed has newlines
        assert "  " in pretty_output  # Has indentation


class TestDataValidation:
    """Test data validation features"""

    @pytest.fixture
    def converter(self):
        return DataConverter(colors=False, validate=True)

    def test_validation_enabled(self, converter):
        """Test that validation is enabled"""
        assert converter.validate is True

    def test_csv_validation_failure(self, converter):
        """Test CSV validation with invalid data"""
        # CSV requires list of dicts, not just a dict
        invalid_data = {"key": "value"}

        with pytest.raises(ValueError, match="list of dictionaries"):
            converter._validate_data(invalid_data, 'csv')
