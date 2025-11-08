"""
Shared pytest fixtures for all test modules
"""
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def sample_text_file(temp_dir):
    """Create a sample text file"""
    file_path = temp_dir / "sample.txt"
    file_path.write_text("Hello World\nThis is a test file\n")
    return file_path


@pytest.fixture
def sample_python_file(temp_dir):
    """Create a sample Python file with imports"""
    file_path = temp_dir / "sample.py"
    content = """import os
import sys
import json
from pathlib import Path

# Only using os
def main():
    print(os.getcwd())

if __name__ == '__main__':
    main()
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_env_file(temp_dir):
    """Create a sample .env file"""
    file_path = temp_dir / ".env"
    content = """# Database configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=testdb

# API Keys
API_KEY=sk-test123
SECRET_KEY="my secret"
DEBUG=true
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_json_file(temp_dir):
    """Create a sample JSON file"""
    file_path = temp_dir / "data.json"
    content = '{"name": "Test", "value": 123, "active": true}'
    file_path.write_text(content)
    return file_path


@pytest.fixture
def duplicate_files(temp_dir):
    """Create duplicate files for testing"""
    file1 = temp_dir / "file1.txt"
    file2 = temp_dir / "file2.txt"
    file3 = temp_dir / "file3.txt"

    content = "duplicate content"
    file1.write_text(content)
    file2.write_text(content)
    file3.write_text("different content")

    return [file1, file2, file3]
