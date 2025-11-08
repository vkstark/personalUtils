"""
Tests for ImportOptimizer utility
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ImportOptimizer.import_optimizer import ImportAnalyzer


class TestImportAnalyzer:
    """Test cases for ImportAnalyzer"""

    @pytest.fixture
    def analyzer(self):
        """Create ImportAnalyzer instance"""
        return ImportAnalyzer(colors=False)

    def test_analyze_unused_imports(self, analyzer, sample_python_file):
        """Test detecting unused imports"""
        analysis = analyzer.analyze_file(str(sample_python_file))

        assert 'imports' in analysis
        assert 'unused' in analysis
        assert 'used_names' in analysis

        # sample_python_file has unused imports (sys, json, Path)
        assert len(analysis['unused']) > 0

    def test_analyze_all_used_imports(self, analyzer, temp_dir):
        """Test file with all imports used"""
        python_file = temp_dir / "all_used.py"
        content = """import os

def main():
    print(os.getcwd())
"""
        python_file.write_text(content)

        analysis = analyzer.analyze_file(str(python_file))

        # All imports are used
        assert len(analysis['unused']) == 0

    def test_analyze_from_imports(self, analyzer, temp_dir):
        """Test analyzing 'from' imports"""
        python_file = temp_dir / "from_imports.py"
        content = """from pathlib import Path
from os import getcwd

def main():
    p = Path('.')
    # getcwd is not used
"""
        python_file.write_text(content)

        analysis = analyzer.analyze_file(str(python_file))

        # getcwd is unused
        unused_names = [imp['name'] for imp in analysis['unused']]
        assert 'getcwd' in unused_names

    def test_analyze_aliased_imports(self, analyzer, temp_dir):
        """Test analyzing imports with aliases"""
        python_file = temp_dir / "aliased.py"
        content = """import pandas as pd
import numpy as np

def main():
    data = pd.DataFrame()
    # np is not used
"""
        python_file.write_text(content)

        analysis = analyzer.analyze_file(str(python_file))

        # np is unused
        unused_names = [imp['name'] for imp in analysis['unused']]
        assert 'np' in unused_names

        # pd is used
        assert 'pd' not in unused_names

    def test_analyze_syntax_error(self, analyzer, temp_dir):
        """Test handling syntax errors"""
        python_file = temp_dir / "syntax_error.py"
        content = """import os
def broken syntax here
"""
        python_file.write_text(content)

        analysis = analyzer.analyze_file(str(python_file))

        # Should return error
        assert 'error' in analysis

    def test_analyze_attribute_access(self, analyzer, temp_dir):
        """Test detecting attribute access (module.function)"""
        python_file = temp_dir / "attribute.py"
        content = """import os
import sys

def main():
    os.getcwd()
    # sys is unused
"""
        python_file.write_text(content)

        analysis = analyzer.analyze_file(str(python_file))

        # sys is unused, os is used via attribute access
        unused_names = [imp['name'] for imp in analysis['unused']]
        assert 'sys' in unused_names
        assert 'os' not in unused_names


class TestImportOrganizer:
    """Test import organization"""

    @pytest.fixture
    def analyzer(self):
        return ImportAnalyzer(colors=False)

    def test_organize_imports(self, analyzer, temp_dir):
        """Test organizing imports into groups"""
        python_file = temp_dir / "organize.py"
        content = """import sys
import requests
import os
from flask import Flask
"""
        python_file.write_text(content)

        stdlib, third_party, local = analyzer.organize_imports(str(python_file))

        # Check stdlib
        stdlib_modules = [imp['module'] for imp in stdlib]
        assert 'sys' in stdlib_modules
        assert 'os' in stdlib_modules

        # Check third-party
        third_party_modules = [imp['module'] for imp in third_party]
        assert 'requests' in third_party_modules
        assert 'flask' in third_party_modules

    def test_organize_stdlib_only(self, analyzer, temp_dir):
        """Test organizing file with only stdlib imports"""
        python_file = temp_dir / "stdlib_only.py"
        content = """import os
import sys
import json
from pathlib import Path
"""
        python_file.write_text(content)

        stdlib, third_party, local = analyzer.organize_imports(str(python_file))

        assert len(stdlib) == 4
        assert len(third_party) == 0
        assert len(local) == 0


class TestImportDirectory:
    """Test directory scanning"""

    @pytest.fixture
    def analyzer(self):
        return ImportAnalyzer(colors=False)

    def test_find_unused_in_directory(self, analyzer, temp_dir):
        """Test finding unused imports in directory"""
        # Create multiple Python files with unused imports
        file1 = temp_dir / "file1.py"
        file1.write_text("import os\nimport sys\nprint(os.getcwd())")

        file2 = temp_dir / "file2.py"
        file2.write_text("import json\nimport time\nprint('hello')")

        results = analyzer.find_unused_in_directory(str(temp_dir), recursive=False)

        # Should find files with unused imports
        assert len(results) >= 1

        # file2 should have unused imports (both json and time)
        file2_results = [v for k, v in results.items() if 'file2.py' in k]
        if file2_results:
            assert len(file2_results[0]) == 2

    def test_find_unused_recursive(self, analyzer, temp_dir):
        """Test recursive directory scanning"""
        # Create subdirectory with Python file
        subdir = temp_dir / "subdir"
        subdir.mkdir()

        file1 = subdir / "test.py"
        file1.write_text("import os\nimport sys\nprint('hello')")

        results = analyzer.find_unused_in_directory(str(temp_dir), recursive=True)

        # Should find the file in subdirectory
        assert any('subdir' in path for path in results.keys())

    def test_find_unused_no_results(self, analyzer, temp_dir):
        """Test directory with no unused imports"""
        # Create file with all imports used
        file1 = temp_dir / "clean.py"
        file1.write_text("import os\nprint(os.getcwd())")

        results = analyzer.find_unused_in_directory(str(temp_dir), recursive=False)

        # Should have no results for clean.py
        clean_results = [v for k, v in results.items() if 'clean.py' in k]
        assert len(clean_results) == 0
