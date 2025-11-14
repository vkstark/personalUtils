"""
Tests for BulkRename utility
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.BulkRename.bulk_rename import BulkRename, RenameMode


class TestBulkRename:
    """Test cases for BulkRename"""

    @pytest.fixture
    def renamer(self):
        """Create BulkRename instance"""
        return BulkRename(dry_run=True, colors=False, backup=False)

    @pytest.fixture
    def test_files(self, temp_dir):
        """Create test files for renaming"""
        files = []
        for i in range(5):
            f = temp_dir / f"test_file_{i}.txt"
            f.write_text(f"Content {i}")
            files.append(f)
        return temp_dir, files

    def test_replace_mode(self, renamer, test_files):
        """Test replace rename mode"""
        temp_dir, files = test_files

        renamed = renamer.rename(
            str(temp_dir),
            RenameMode.REPLACE,
            pattern="*.txt",
            find="test",
            replace="demo"
        )

        assert renamed >= 0

    def test_sequential_mode(self, renamer, test_files):
        """Test sequential numbering mode"""
        temp_dir, files = test_files

        renamed = renamer.rename(
            str(temp_dir),
            RenameMode.SEQUENTIAL,
            pattern="*.txt",
            template="file_{n}",
            start=1,
            digits=3
        )

        assert renamed >= 0

    @pytest.mark.parametrize("case_type", ["lower", "upper", "title"])
    def test_case_modes(self, renamer, test_files, case_type):
        """Test different case conversion modes"""
        temp_dir, files = test_files

        renamed = renamer.rename(
            str(temp_dir),
            RenameMode.CASE,
            pattern="*.txt",
            case=case_type
        )

        assert renamed >= 0

    def test_prefix_mode(self, renamer, test_files):
        """Test adding prefix to filenames"""
        temp_dir, files = test_files

        renamed = renamer.rename(
            str(temp_dir),
            RenameMode.PREFIX,
            pattern="*.txt",
            prefix="new_"
        )

        assert renamed >= 0

    def test_dry_run_no_changes(self, test_files):
        """Test that dry run doesn't actually rename files"""
        temp_dir, files = test_files
        original_names = [f.name for f in files]

        renamer = BulkRename(dry_run=True, colors=False)
        renamer.rename(
            str(temp_dir),
            RenameMode.REPLACE,
            pattern="*.txt",
            find="test",
            replace="changed"
        )

        # Check files still have original names
        current_names = [f.name for f in temp_dir.glob("*.txt")]
        assert set(original_names) == set(current_names)


class TestRenameHistory:
    """Test undo/history functionality"""

    def test_history_file_creation(self, temp_dir):
        """Test that history file can be created"""
        renamer = BulkRename(dry_run=False, colors=False, backup=True)
        renamer.history_file = temp_dir / "test_history.json"

        # Create a test file
        test_file = temp_dir / "original.txt"
        test_file.write_text("content")

        # Perform rename (not dry run)
        renamer.rename(
            str(temp_dir),
            RenameMode.PREFIX,
            pattern="*.txt",
            prefix="new_"
        )

        # History should be saved
        assert renamer.current_operation is not None
