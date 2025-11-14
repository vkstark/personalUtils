"""
Tests for EnvManager utility
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.EnvManager.env_manager import EnvManager


class TestEnvManager:
    """Test cases for EnvManager"""

    @pytest.fixture
    def manager(self):
        """Create EnvManager instance"""
        return EnvManager(colors=False)

    def test_parse_env_file(self, manager, sample_env_file):
        """Test parsing .env file"""
        variables = manager.parse_env_file(str(sample_env_file))

        assert isinstance(variables, dict)
        assert 'DB_HOST' in variables
        assert variables['DB_HOST'] == 'localhost'
        assert variables['DB_PORT'] == '5432'

    def test_parse_quoted_values(self, manager, temp_dir):
        """Test parsing values with quotes"""
        env_file = temp_dir / ".env"
        env_file.write_text('KEY1="value with spaces"\nKEY2=\'single quotes\'\n')

        variables = manager.parse_env_file(str(env_file))

        assert variables['KEY1'] == 'value with spaces'
        assert variables['KEY2'] == 'single quotes'

    def test_write_env_file(self, manager, temp_dir):
        """Test writing .env file"""
        output_file = temp_dir / ".env.output"
        variables = {
            'KEY1': 'value1',
            'KEY2': 'value2',
            'SPACED': 'value with spaces'
        }

        manager.write_env_file(str(output_file), variables)

        assert output_file.exists()

        # Read back and verify
        parsed = manager.parse_env_file(str(output_file))
        assert parsed['KEY1'] == 'value1'
        assert parsed['SPACED'] == 'value with spaces'

    def test_compare_env_files(self, manager, temp_dir):
        """Test comparing two .env files"""
        file1 = temp_dir / ".env1"
        file2 = temp_dir / ".env2"

        file1.write_text('COMMON=value\nONLY1=value1\n')
        file2.write_text('COMMON=value\nONLY2=value2\n')

        result = manager.compare(str(file1), str(file2))

        assert 'ONLY1' in result['only_in_file1']
        assert 'ONLY2' in result['only_in_file2']
        assert 'COMMON' in result['common']

    def test_validate_required_variables(self, manager, sample_env_file):
        """Test validating required variables"""
        valid, errors = manager.validate(
            str(sample_env_file),
            required=['DB_HOST', 'DB_PORT']
        )

        assert valid is True
        assert len(errors) == 0


class TestEnvValidation:
    """Test validation features"""

    @pytest.fixture
    def manager(self):
        return EnvManager(colors=False)

    def test_missing_required_variable(self, manager, temp_dir):
        """Test validation fails with missing required variable"""
        env_file = temp_dir / ".env"
        env_file.write_text('KEY1=value1\n')

        valid, errors = manager.validate(
            str(env_file),
            required=['KEY1', 'MISSING_KEY']
        )

        assert valid is False
        assert len(errors) > 0
        assert any('MISSING_KEY' in err for err in errors)

    def test_pattern_validation(self, manager, temp_dir):
        """Test regex pattern validation"""
        env_file = temp_dir / ".env"
        env_file.write_text('PORT=5432\nINVALID_PORT=abc\n')

        valid, errors = manager.validate(
            str(env_file),
            patterns={'PORT': r'^[0-9]+$', 'INVALID_PORT': r'^[0-9]+$'}
        )

        assert valid is False
        assert any('INVALID_PORT' in err for err in errors)

    def test_empty_required_value(self, manager, temp_dir):
        """Test validation fails for empty required values"""
        env_file = temp_dir / ".env"
        env_file.write_text('REQUIRED_KEY=\n')

        valid, errors = manager.validate(
            str(env_file),
            required=['REQUIRED_KEY']
        )

        assert valid is False


class TestEnvMerge:
    """Test merge functionality"""

    @pytest.fixture
    def manager(self):
        return EnvManager(colors=False)

    def test_merge_multiple_files(self, manager, temp_dir):
        """Test merging multiple .env files"""
        file1 = temp_dir / ".env.base"
        file2 = temp_dir / ".env.override"

        file1.write_text('KEY1=base\nKEY2=base\n')
        file2.write_text('KEY2=override\nKEY3=new\n')

        merged = manager.merge(str(file1), str(file2), priority='last')

        assert merged['KEY1'] == 'base'
        assert merged['KEY2'] == 'override'  # Overridden
        assert merged['KEY3'] == 'new'

    def test_merge_priority_first(self, manager, temp_dir):
        """Test merge with first priority"""
        file1 = temp_dir / "first.env"
        file2 = temp_dir / "second.env"

        file1.write_text('KEY=first\n')
        file2.write_text('KEY=second\n')

        merged = manager.merge(str(file1), str(file2), priority='first')

        assert merged['KEY'] == 'first'  # First in list wins with priority='first'
