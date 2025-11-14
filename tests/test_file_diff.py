"""
Tests for FileDiff utility
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.FileDiff.file_diff import FileDiff, DiffMode


class TestFileDiff:
    """Test cases for FileDiff"""

    @pytest.fixture
    def differ(self):
        """Create FileDiff instance without colors for testing"""
        return FileDiff(colors=False)

    @pytest.fixture
    def file_pair(self, temp_dir):
        """Create two files for comparison"""
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.txt"

        file1.write_text("Line 1\nLine 2\nLine 3\n")
        file2.write_text("Line 1\nLine 2 modified\nLine 3\n")

        return file1, file2

    def test_identical_files(self, differ, temp_dir):
        """Test comparing identical files"""
        file1 = temp_dir / "same1.txt"
        file2 = temp_dir / "same2.txt"

        content = "Same content\n"
        file1.write_text(content)
        file2.write_text(content)

        result = differ.compare_files(str(file1), str(file2))

        assert differ.stats['total_changes'] == 0
        assert differ.are_files_identical(str(file1), str(file2))

    def test_different_files(self, differ, file_pair):
        """Test comparing different files"""
        file1, file2 = file_pair

        result = differ.compare_files(str(file1), str(file2))

        assert differ.stats['total_changes'] > 0
        assert not differ.are_files_identical(str(file1), str(file2))

    @pytest.mark.parametrize("mode", [
        DiffMode.UNIFIED,
        DiffMode.CONTEXT,
        DiffMode.SIDE_BY_SIDE,
        DiffMode.MINIMAL
    ])
    def test_different_diff_modes(self, differ, file_pair, mode):
        """Test different diff output modes"""
        file1, file2 = file_pair

        result = differ.compare_files(str(file1), str(file2), mode=mode)

        assert result is not None
        assert isinstance(result, str)

    def test_ignore_whitespace(self, differ, temp_dir):
        """Test ignoring whitespace differences"""
        file1 = temp_dir / "ws1.txt"
        file2 = temp_dir / "ws2.txt"

        file1.write_text("Hello World\n")
        file2.write_text("Hello   World\n")  # Extra spaces

        differ_with_ignore = FileDiff(ignore_whitespace=True, colors=False)

        assert differ_with_ignore.are_files_identical(str(file1), str(file2))

    def test_file_not_found(self, differ, temp_dir):
        """Test error handling for non-existent files"""
        file1 = temp_dir / "exists.txt"
        file1.write_text("content")

        file2 = temp_dir / "not_exists.txt"

        with pytest.raises(FileNotFoundError):
            differ.compare_files(str(file1), str(file2))


class TestFileDiffStatistics:
    """Test statistics tracking"""

    @pytest.fixture
    def differ(self):
        return FileDiff(colors=False)

    def test_statistics_calculation(self, differ, temp_dir):
        """Test that statistics are calculated correctly"""
        file1 = temp_dir / "stats1.txt"
        file2 = temp_dir / "stats2.txt"

        file1.write_text("Line 1\nLine 2\nLine 3\n")
        file2.write_text("Line 1\nModified\nLine 3\nNew Line\n")

        differ.compare_files(str(file1), str(file2))

        # Verify stats were updated
        assert differ.stats['total_changes'] > 0
        assert 'added_lines' in differ.stats
        assert 'deleted_lines' in differ.stats

    def test_get_statistics_output(self, differ, temp_dir):
        """Test statistics output formatting"""
        file1 = temp_dir / "out1.txt"
        file2 = temp_dir / "out2.txt"

        file1.write_text("A\n")
        file2.write_text("B\n")

        differ.compare_files(str(file1), str(file2))
        stats_output = differ.get_statistics()

        assert "Statistics" in stats_output or "statistics" in stats_output.lower()
        assert isinstance(stats_output, str)
