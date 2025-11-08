# Test Suite

Comprehensive pytest test suite for all personalUtils utilities.

## Installation

Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run tests for a specific utility
```bash
pytest tests/test_file_diff.py
pytest tests/test_bulk_rename.py
pytest tests/test_data_convert.py
pytest tests/test_todo_extractor.py
pytest tests/test_snippet_manager.py
pytest tests/test_env_manager.py
pytest tests/test_duplicate_finder.py
pytest tests/test_git_stats.py
pytest tests/test_import_optimizer.py
pytest tests/test_api_tester.py
```

### Run with verbose output
```bash
pytest -v
```

### Run with coverage report
```bash
pytest --cov=. --cov-report=html --cov-report=term-missing
```

### Run specific test class or method
```bash
pytest tests/test_file_diff.py::TestFileDiff::test_identical_files
```

## Test Structure

Each utility has comprehensive test coverage including:

- **FileDiff** (7 tests): File comparison modes, whitespace handling, statistics
- **BulkRename** (7 tests): Rename modes, dry run, history tracking
- **DataConvert** (9 tests): Format conversion, validation, error handling
- **TodoExtractor** (10 tests): TODO detection, priority levels, author tracking
- **SnippetManager** (11 tests): CRUD operations, search, persistence
- **EnvManager** (11 tests): Parsing, validation, merging, comparison
- **DuplicateFinder** (12 tests): Hash detection, size filtering, keep policies
- **GitStats** (13 tests): Repository analysis, reports, JSON export
- **ImportOptimizer** (10 tests): Unused imports, organization, directory scanning
- **APITester** (13 tests): HTTP methods, error handling, history

## Fixtures

Shared fixtures are defined in `conftest.py`:

- `temp_dir`: Temporary directory for file operations
- `sample_text_file`: Sample text file
- `sample_python_file`: Sample Python file with imports
- `sample_env_file`: Sample .env file
- `sample_json_file`: Sample JSON file
- `duplicate_files`: Files for duplicate detection testing

## Test Patterns

All tests follow pytest best practices:
- Use fixtures for setup/teardown
- Parametrize tests for multiple inputs
- Use temp directories for file operations
- Mock external dependencies (network, git)
- Clear, descriptive test names

## Coverage Goals

Target: >80% code coverage for all utilities

View current coverage:
```bash
pytest --cov=. --cov-report=term-missing
```
