"""
Tests for GitStats utility
"""
import pytest
import sys
import json
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.GitStats.git_stats import GitStats


class TestGitStatsBasic:
    """Basic test cases for GitStats"""

    @pytest.fixture
    def git_repo(self, temp_dir):
        """Create a minimal git repository for testing"""
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=temp_dir, check=True, capture_output=True)
        # Disable GPG signing for tests
        subprocess.run(['git', 'config', 'commit.gpgsign', 'false'], cwd=temp_dir, check=True, capture_output=True)

        # Create and commit a file
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello World\n")
        subprocess.run(['git', 'add', 'test.txt'], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=temp_dir, check=True, capture_output=True)

        return temp_dir

    def test_is_git_repo_valid(self, git_repo):
        """Test detecting valid git repository"""
        stats = GitStats(repo_path=str(git_repo), colors=False)
        assert stats.repo_path == git_repo.resolve()

    def test_is_git_repo_invalid(self, temp_dir):
        """Test detecting invalid git repository"""
        with pytest.raises(ValueError, match="Not a git repository"):
            GitStats(repo_path=str(temp_dir), colors=False)

    def test_analyze_commits(self, git_repo):
        """Test commit analysis"""
        stats = GitStats(repo_path=str(git_repo), colors=False)
        stats.analyze()

        # Should have at least 1 commit
        assert stats.stats['total_commits'] >= 1
        assert len(stats.commit_history) >= 1

    def test_analyze_contributors(self, git_repo):
        """Test contributor analysis"""
        stats = GitStats(repo_path=str(git_repo), colors=False)
        stats.analyze()

        # Should have at least 1 contributor
        assert stats.stats['total_contributors'] >= 1
        assert len(stats.contributors) >= 1

        # Check contributor has expected fields
        for name, contributor in stats.contributors.items():
            assert 'email' in contributor
            assert 'commits' in contributor
            assert 'insertions' in contributor
            assert 'deletions' in contributor
            assert contributor['commits'] >= 1

    def test_get_summary(self, git_repo):
        """Test summary report generation"""
        stats = GitStats(repo_path=str(git_repo), colors=False)
        stats.analyze()

        summary = stats.get_summary()

        # Summary should contain key information
        assert 'Total Commits' in summary
        assert 'Total Contributors' in summary
        assert 'Total Files' in summary

    def test_statistics_fields(self, git_repo):
        """Test that all expected statistics fields exist"""
        stats = GitStats(repo_path=str(git_repo), colors=False)
        stats.analyze()

        # Check all expected fields exist
        assert 'total_commits' in stats.stats
        assert 'total_files' in stats.stats
        assert 'total_contributors' in stats.stats
        assert 'lines_added' in stats.stats
        assert 'lines_deleted' in stats.stats
        assert 'first_commit' in stats.stats
        assert 'last_commit' in stats.stats
        assert 'active_days' in stats.stats


class TestGitStatsReports:
    """Test report generation"""

    @pytest.fixture
    def git_repo_with_commits(self, temp_dir):
        """Create a git repository with multiple commits"""
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=temp_dir, check=True, capture_output=True)
        # Disable GPG signing for tests
        subprocess.run(['git', 'config', 'commit.gpgsign', 'false'], cwd=temp_dir, check=True, capture_output=True)

        # Create multiple commits
        for i in range(3):
            test_file = temp_dir / f"file{i}.txt"
            test_file.write_text(f"Content {i}\n")
            subprocess.run(['git', 'add', f'file{i}.txt'], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', f'Commit {i}'], cwd=temp_dir, check=True, capture_output=True)

        return temp_dir

    def test_get_contributors_report(self, git_repo_with_commits):
        """Test contributors report generation"""
        stats = GitStats(repo_path=str(git_repo_with_commits), colors=False)
        stats.analyze()

        report = stats.get_contributors_report(top_n=5)

        # Report should contain contributor information
        assert 'Top Contributors' in report
        assert 'Test User' in report or 'test@example.com' in report

    def test_get_file_report(self, git_repo_with_commits):
        """Test file report generation"""
        stats = GitStats(repo_path=str(git_repo_with_commits), colors=False)
        stats.analyze()

        report = stats.get_file_report(top_n=5)

        # Report should contain file information
        assert 'Most Changed Files' in report

    def test_get_activity_heatmap(self, git_repo_with_commits):
        """Test activity heatmap generation"""
        stats = GitStats(repo_path=str(git_repo_with_commits), colors=False)
        stats.analyze()

        heatmap = stats.get_activity_heatmap()

        # Heatmap should contain day and hour information
        assert 'Commit Activity Heatmap' in heatmap
        assert 'By Day of Week' in heatmap
        assert 'By Hour of Day' in heatmap

    def test_get_recent_activity(self, git_repo_with_commits):
        """Test recent activity report"""
        stats = GitStats(repo_path=str(git_repo_with_commits), colors=False)
        stats.analyze()

        recent = stats.get_recent_activity(days=30)

        # Should contain recent activity info
        assert 'Recent Activity' in recent


class TestGitStatsExport:
    """Test export functionality"""

    @pytest.fixture
    def git_repo(self, temp_dir):
        """Create a minimal git repository for testing"""
        subprocess.run(['git', 'init'], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=temp_dir, check=True, capture_output=True)
        # Disable GPG signing for tests
        subprocess.run(['git', 'config', 'commit.gpgsign', 'false'], cwd=temp_dir, check=True, capture_output=True)

        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello World\n")
        subprocess.run(['git', 'add', 'test.txt'], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=temp_dir, check=True, capture_output=True)

        return temp_dir

    def test_export_json(self, git_repo, temp_dir):
        """Test JSON export functionality"""
        stats = GitStats(repo_path=str(git_repo), colors=False)
        stats.analyze()

        output_file = temp_dir / "stats.json"
        stats.export_json(str(output_file))

        # File should exist
        assert output_file.exists()

        # Should be valid JSON
        with open(output_file) as f:
            data = json.load(f)

        # Check structure
        assert 'repository' in data
        assert 'stats' in data
        assert 'contributors' in data
        assert 'files' in data
        assert 'activity' in data

    def test_export_json_structure(self, git_repo, temp_dir):
        """Test JSON export has correct structure"""
        stats = GitStats(repo_path=str(git_repo), colors=False)
        stats.analyze()

        output_file = temp_dir / "stats_structure.json"
        stats.export_json(str(output_file))

        with open(output_file) as f:
            data = json.load(f)

        # Verify stats section
        assert 'total_commits' in data['stats']
        assert 'total_files' in data['stats']
        assert 'total_contributors' in data['stats']

        # Verify activity section
        assert 'daily' in data['activity']
        assert 'hourly' in data['activity']
        assert 'day_of_week' in data['activity']
