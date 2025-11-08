"""
Tests for TodoExtractor utility
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from TodoExtractor.todo_extractor import TodoExtractor, TodoItem


class TestTodoExtractor:
    """Test cases for TodoExtractor"""

    @pytest.fixture
    def extractor(self):
        """Create TodoExtractor instance"""
        return TodoExtractor(colors=False)

    @pytest.fixture
    def python_file_with_todos(self, temp_dir):
        """Create Python file with various TODO comments"""
        file_path = temp_dir / "todos.py"
        content = """
# TODO: Implement feature
def function1():
    # FIXME: Bug here
    pass

# HACK: Temporary solution
# TODO(john): Add tests
def function2():
    # NOTE: This is important
    # TODO[P3]: High priority task
    pass
"""
        file_path.write_text(content)
        return file_path

    def test_extract_todos_from_file(self, extractor, python_file_with_todos):
        """Test extracting TODOs from a Python file"""
        todos = extractor.scan_file(str(python_file_with_todos))

        assert len(todos) > 0
        assert any(item.tag == 'TODO' for item in todos)

    def test_extract_fixme(self, extractor, python_file_with_todos):
        """Test extracting FIXME comments"""
        todos = extractor.scan_file(str(python_file_with_todos))

        fixmes = [t for t in todos if t.tag == 'FIXME']
        assert len(fixmes) > 0

    def test_author_detection(self, extractor, python_file_with_todos):
        """Test detecting TODO author"""
        todos = extractor.scan_file(str(python_file_with_todos))

        todos_with_author = [t for t in todos if t.author]
        assert len(todos_with_author) > 0
        assert any(t.author == 'john' for t in todos_with_author)

    def test_priority_detection(self, extractor, python_file_with_todos):
        """Test detecting priority levels"""
        todos = extractor.scan_file(str(python_file_with_todos))

        high_priority = [t for t in todos if t.priority >= 3]
        assert len(high_priority) > 0

    def test_search_by_tag(self, extractor, python_file_with_todos):
        """Test filtering TODOs by tag"""
        extractor.extract(str(python_file_with_todos.parent))

        # Filter for specific tags
        fixmes = [t for t in extractor.todos if t.tag == 'FIXME']
        assert all(t.tag == 'FIXME' for t in fixmes)
        assert len(fixmes) > 0  # Should find at least one FIXME


class TestTodoStatistics:
    """Test statistics and reporting"""

    @pytest.fixture
    def extractor(self):
        return TodoExtractor(colors=False)

    def test_statistics_tracking(self, extractor, temp_dir):
        """Test that statistics are tracked"""
        # Create file with known TODOs
        file_path = temp_dir / "stats.py"
        content = "# TODO: Task 1\n# FIXME: Task 2\n# TODO: Task 3\n"
        file_path.write_text(content)

        extractor.extract(str(file_path))

        assert extractor.stats['total_todos'] == 3
        assert extractor.stats['by_tag']['TODO'] == 2
        assert extractor.stats['by_tag']['FIXME'] == 1

    def test_empty_file(self, extractor, temp_dir):
        """Test scanning file with no TODOs"""
        file_path = temp_dir / "empty.py"
        file_path.write_text("def function():\n    pass\n")

        todos = extractor.scan_file(str(file_path))

        assert len(todos) == 0


class TestTodoItemCreation:
    """Test TodoItem data class"""

    def test_create_todo_item(self):
        """Test creating a TodoItem"""
        item = TodoItem(
            tag='TODO',
            text='Do something',
            filepath='test.py',
            line_num=10,
            priority=1
        )

        assert item.tag == 'TODO'
        assert item.text == 'Do something'
        assert item.line_num == 10
        assert item.priority == 1

    def test_todo_item_with_author(self):
        """Test TodoItem with author"""
        item = TodoItem(
            tag='FIXME',
            text='Fix bug',
            filepath='test.py',
            line_num=5,
            author='alice'
        )

        assert item.author == 'alice'
