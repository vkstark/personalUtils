"""
Tests for SnippetManager utility
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.SnippetManager.snippet_manager import SnippetManager


class TestSnippetManager:
    """Test cases for SnippetManager"""

    @pytest.fixture
    def manager(self, temp_dir):
        """Create SnippetManager with temp storage"""
        storage_path = temp_dir / "snippets.json"
        return SnippetManager(storage_path=str(storage_path), colors=False)

    def test_add_snippet(self, manager):
        """Test adding a new snippet"""
        snippet_id = manager.add(
            title="Test Snippet",
            code="print('hello')",
            language="python",
            description="A test snippet",
            tags=["test"]
        )

        assert snippet_id is not None
        assert snippet_id in manager.snippets

    def test_get_snippet(self, manager):
        """Test retrieving a snippet"""
        snippet_id = manager.add(
            title="Get Test",
            code="console.log('test')",
            language="javascript"
        )

        snippet = manager.get(snippet_id)

        assert snippet is not None
        assert snippet.title == "Get Test"
        assert snippet.language == "javascript"

    def test_update_snippet(self, manager):
        """Test updating a snippet"""
        snippet_id = manager.add(
            title="Update Test",
            code="original code",
            language="python"
        )

        manager.update(snippet_id, code="updated code")

        snippet = manager.get(snippet_id)
        assert snippet.code == "updated code"

    def test_delete_snippet(self, manager):
        """Test deleting a snippet"""
        snippet_id = manager.add(
            title="Delete Test",
            code="code",
            language="python"
        )

        manager.delete(snippet_id)

        assert snippet_id not in manager.snippets

    def test_search_by_query(self, manager):
        """Test searching snippets by text query"""
        manager.add(
            title="Docker command",
            code="docker run nginx",
            language="bash",
            tags=["docker"]
        )

        manager.add(
            title="Python script",
            code="print('hello')",
            language="python",
            tags=["python"]
        )

        results = manager.search(query="docker")

        assert len(results) == 1
        assert results[0].title == "Docker command"


class TestSnippetSearch:
    """Test search functionality"""

    @pytest.fixture
    def manager_with_snippets(self, temp_dir):
        """Create manager with pre-loaded snippets"""
        storage_path = temp_dir / "search_test.json"
        mgr = SnippetManager(storage_path=str(storage_path), colors=False)

        mgr.add("Python Loop", "for i in range(10):", "python", tags=["loop", "python"])
        mgr.add("Bash Script", "#!/bin/bash", "bash", tags=["bash"])
        mgr.add("Python Function", "def test():", "python", tags=["function", "python"])

        return mgr

    def test_search_by_tag(self, manager_with_snippets):
        """Test searching by tags"""
        results = manager_with_snippets.search(tags=["python"])

        assert len(results) == 2
        assert all(r.language == "python" for r in results)

    def test_search_by_language(self, manager_with_snippets):
        """Test searching by language"""
        results = manager_with_snippets.search(language="bash")

        assert len(results) == 1
        assert results[0].language == "bash"

    def test_combined_search(self, manager_with_snippets):
        """Test searching with multiple criteria"""
        results = manager_with_snippets.search(
            query="function",
            language="python"
        )

        assert len(results) == 1
        assert results[0].title == "Python Function"


class TestSnippetPersistence:
    """Test storage persistence"""

    def test_save_and_load(self, temp_dir):
        """Test that snippets persist across manager instances"""
        storage_path = temp_dir / "persist.json"

        # Create manager and add snippet
        manager1 = SnippetManager(storage_path=str(storage_path), colors=False)
        snippet_id = manager1.add("Test", "code", "python")

        # Create new manager instance with same storage
        manager2 = SnippetManager(storage_path=str(storage_path), colors=False)

        # Snippet should be loaded
        assert snippet_id in manager2.snippets
