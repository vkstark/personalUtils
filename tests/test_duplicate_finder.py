"""
Tests for DuplicateFinder utility
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from DuplicateFinder.duplicate_finder import DuplicateFinder


class TestDuplicateFinder:
    """Test cases for DuplicateFinder"""

    @pytest.fixture
    def finder(self):
        """Create DuplicateFinder instance"""
        return DuplicateFinder(colors=False)

    def test_find_duplicates_by_hash(self, finder, duplicate_files):
        """Test finding duplicates by hash"""
        # duplicate_files fixture creates 2 identical files and 1 different
        temp_dir = duplicate_files[0].parent

        duplicates = finder.find_by_hash([str(temp_dir)], recursive=False)

        # Should find one set of duplicates (file1 and file2 are identical)
        assert len(duplicates) == 1

        # Each duplicate set should have 2 files
        for hash_key, files in duplicates.items():
            assert len(files) == 2

    def test_find_duplicates_by_name(self, finder, temp_dir):
        """Test finding duplicates by filename"""
        # Create files with same names in different directories
        dir1 = temp_dir / "dir1"
        dir2 = temp_dir / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        (dir1 / "same_name.txt").write_text("content1")
        (dir2 / "same_name.txt").write_text("different content")

        duplicates = finder.find_by_name([str(temp_dir)], recursive=True)

        assert len(duplicates) == 1
        assert 'same_name.txt' in duplicates
        assert len(duplicates['same_name.txt']) == 2

    def test_find_empty_files(self, finder, temp_dir):
        """Test finding empty files"""
        # Create some empty and non-empty files
        (temp_dir / "empty1.txt").touch()
        (temp_dir / "empty2.txt").touch()
        (temp_dir / "not_empty.txt").write_text("content")

        empty_files = finder.find_empty([str(temp_dir)], recursive=False)

        assert len(empty_files) == 2
        assert any("empty1.txt" in f for f in empty_files)
        assert any("empty2.txt" in f for f in empty_files)

    def test_size_filtering(self, finder, temp_dir):
        """Test filtering files by size"""
        # Create files of different sizes
        small_file = temp_dir / "small.txt"
        medium_file = temp_dir / "medium.txt"
        large_file = temp_dir / "large.txt"

        small_file.write_text("x" * 100)  # 100 bytes
        medium_file.write_text("x" * 1000)  # 1000 bytes
        large_file.write_text("x" * 10000)  # 10000 bytes

        # Create duplicates of medium file
        medium_dup = temp_dir / "medium_dup.txt"
        medium_dup.write_text("x" * 1000)

        # Find duplicates with min_size = 500 (should exclude small.txt)
        duplicates = finder.find_by_hash([str(temp_dir)], min_size=500)

        # Should find duplicates for medium files only
        assert len(duplicates) == 1

    def test_extension_filtering(self, finder, temp_dir):
        """Test filtering files by extension"""
        # Create files with different extensions
        (temp_dir / "file1.txt").write_text("duplicate content")
        (temp_dir / "file2.txt").write_text("duplicate content")
        (temp_dir / "file1.jpg").write_text("duplicate content")
        (temp_dir / "file2.jpg").write_text("duplicate content")

        # Find only .txt duplicates
        duplicates = finder.find_by_hash([str(temp_dir)], extensions=['.txt'])

        assert len(duplicates) == 1

        # Verify all files in duplicates are .txt files
        for files in duplicates.values():
            for filepath in files:
                assert filepath.endswith('.txt')

    def test_dry_run_deletion(self, finder, duplicate_files):
        """Test dry run deletion (should not delete files)"""
        temp_dir = duplicate_files[0].parent

        duplicates = finder.find_by_hash([str(temp_dir)], recursive=False)

        # Count files before dry run
        files_before = list(temp_dir.glob('*.txt'))

        # Dry run should not delete anything
        deleted = finder.delete_duplicates(duplicates, keep='first', dry_run=True)

        files_after = list(temp_dir.glob('*.txt'))

        # All files should still exist
        assert len(files_before) == len(files_after)
        assert deleted == 0

    def test_format_size(self, finder):
        """Test file size formatting"""
        assert finder._format_size(100) == "100B"
        assert finder._format_size(1024) == "1.0KB"
        assert finder._format_size(1024 * 1024) == "1.0MB"
        assert finder._format_size(1024 * 1024 * 1024) == "1.0GB"

    def test_case_sensitive_name_matching(self, finder, temp_dir):
        """Test case-sensitive filename matching"""
        (temp_dir / "File.txt").write_text("content1")
        (temp_dir / "file.txt").write_text("content2")

        # Case-insensitive (default)
        duplicates = finder.find_by_name([str(temp_dir)], case_sensitive=False)
        assert len(duplicates) == 1

        # Reset stats
        finder.stats = {
            'total_files': 0,
            'total_size': 0,
            'duplicate_files': 0,
            'duplicate_size': 0,
            'unique_files': 0
        }

        # Case-sensitive
        duplicates = finder.find_by_name([str(temp_dir)], case_sensitive=True)
        assert len(duplicates) == 0


class TestDuplicateStatistics:
    """Test statistics tracking"""

    @pytest.fixture
    def finder(self):
        return DuplicateFinder(colors=False)

    def test_statistics_calculation(self, finder, duplicate_files):
        """Test that statistics are correctly calculated"""
        temp_dir = duplicate_files[0].parent

        duplicates = finder.find_by_hash([str(temp_dir)], recursive=False)

        # Should have scanned 3 files
        assert finder.stats['total_files'] == 3

        # Should have 1 duplicate file (out of 2 identical)
        assert finder.stats['duplicate_files'] == 1

        # Should have 2 unique files
        assert finder.stats['unique_files'] == 2

    def test_wasted_space_calculation(self, finder, temp_dir):
        """Test wasted space calculation"""
        # Create duplicates with known size
        content = "x" * 1000  # 1000 bytes
        (temp_dir / "file1.txt").write_text(content)
        (temp_dir / "file2.txt").write_text(content)
        (temp_dir / "file3.txt").write_text(content)

        duplicates = finder.find_by_hash([str(temp_dir)])

        # Wasted space should be 2 * 1000 = 2000 bytes
        # (keeping 1 of 3 identical files means 2 are wasted)
        assert finder.stats['duplicate_size'] == 2000


class TestKeepPolicies:
    """Test different keep policies for deletion"""

    @pytest.fixture
    def finder(self):
        return DuplicateFinder(colors=False)

    def test_keep_first_policy(self, finder, temp_dir):
        """Test keep='first' policy"""
        # Create duplicates
        (temp_dir / "a_file.txt").write_text("content")
        (temp_dir / "z_file.txt").write_text("content")

        duplicates = finder.find_by_hash([str(temp_dir)])

        # With keep='first', should keep the first file in the list
        # (which is alphabetically first due to sorting)
        assert len(duplicates) == 1

    def test_keep_shortest_path_policy(self, finder, temp_dir):
        """Test keep='shortest' policy"""
        # Create files in nested directories
        subdir = temp_dir / "very_long_subdirectory_name"
        subdir.mkdir()

        (temp_dir / "file.txt").write_text("content")
        (subdir / "file.txt").write_text("content")

        duplicates = finder.find_by_hash([str(temp_dir)], recursive=True)

        # Shortest path should win with keep='shortest'
        assert len(duplicates) == 1
