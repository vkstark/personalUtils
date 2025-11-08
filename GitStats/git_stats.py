#!/usr/bin/env python3
"""
GitStats - Repository Statistics Analyzer
Analyze git repositories and generate comprehensive statistics.

Author: Vishal Kumar
License: MIT
"""

import os
import sys
import argparse
import subprocess
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import calendar

# Color codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'

    # Text colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    # Bright colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_BLUE = '\033[44m'

class GitStats:
    """Git repository statistics analyzer"""

    def __init__(self, repo_path: str = '.', colors: bool = True, verbose: bool = False):
        self.repo_path = Path(repo_path).resolve()
        self.colors = colors and self._supports_color()
        self.verbose = verbose

        # Verify it's a git repository
        if not self._is_git_repo():
            raise ValueError(f"Not a git repository: {self.repo_path}")

        # Statistics data
        self.stats = {
            'total_commits': 0,
            'total_files': 0,
            'total_contributors': 0,
            'lines_added': 0,
            'lines_deleted': 0,
            'first_commit': None,
            'last_commit': None,
            'active_days': 0
        }

        self.contributors = {}
        self.file_stats = {}
        self.commit_history = []
        self.daily_commits = defaultdict(int)
        self.hourly_commits = defaultdict(int)
        self.day_of_week_commits = defaultdict(int)

    def _supports_color(self) -> bool:
        """Check if terminal supports color output"""
        return (hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
                os.getenv('TERM') != 'dumb')

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled"""
        if not self.colors:
            return text
        return f"{color}{text}{Colors.RESET}"

    def _is_git_repo(self) -> bool:
        """Check if directory is a git repository"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def _run_git_command(self, args: List[str]) -> str:
        """Run a git command and return output"""
        try:
            result = subprocess.run(
                ['git'] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            if self.verbose:
                print(f"Git command failed: {' '.join(args)}", file=sys.stderr)
                print(f"Error: {e.stderr}", file=sys.stderr)
            return ""

    def analyze(self):
        """Perform complete repository analysis"""
        print(self._colorize("Analyzing repository...", Colors.BRIGHT_CYAN))

        self._analyze_commits()
        self._analyze_contributors()
        self._analyze_files()
        self._calculate_stats()

        print(self._colorize("✓ Analysis complete", Colors.BRIGHT_GREEN))

    def _analyze_commits(self):
        """Analyze commit history"""
        # Get all commits with details
        log_output = self._run_git_command([
            'log',
            '--all',
            '--pretty=format:%H|%an|%ae|%at|%s',
            '--numstat'
        ])

        if not log_output:
            return

        current_commit = None
        for line in log_output.split('\n'):
            if '|' in line and len(line.split('|')) == 5:
                # Commit line
                hash_val, author, email, timestamp, message = line.split('|')
                current_commit = {
                    'hash': hash_val,
                    'author': author,
                    'email': email,
                    'timestamp': int(timestamp),
                    'message': message,
                    'files_changed': 0,
                    'insertions': 0,
                    'deletions': 0
                }
                self.commit_history.append(current_commit)

                # Track time-based statistics
                dt = datetime.fromtimestamp(int(timestamp))
                self.daily_commits[dt.date()] += 1
                self.hourly_commits[dt.hour] += 1
                self.day_of_week_commits[dt.strftime('%A')] += 1

            elif current_commit and '\t' in line:
                # File change line
                parts = line.split('\t')
                if len(parts) >= 3:
                    try:
                        added = int(parts[0]) if parts[0] != '-' else 0
                        deleted = int(parts[1]) if parts[1] != '-' else 0
                        current_commit['insertions'] += added
                        current_commit['deletions'] += deleted
                        current_commit['files_changed'] += 1
                    except ValueError:
                        pass

        self.stats['total_commits'] = len(self.commit_history)

        if self.commit_history:
            # Commits are in reverse chronological order
            self.stats['last_commit'] = datetime.fromtimestamp(self.commit_history[0]['timestamp'])
            self.stats['first_commit'] = datetime.fromtimestamp(self.commit_history[-1]['timestamp'])
            self.stats['active_days'] = len(self.daily_commits)

    def _analyze_contributors(self):
        """Analyze contributor statistics"""
        for commit in self.commit_history:
            author = commit['author']
            email = commit['email']

            if author not in self.contributors:
                self.contributors[author] = {
                    'email': email,
                    'commits': 0,
                    'insertions': 0,
                    'deletions': 0,
                    'files_changed': 0,
                    'first_commit': datetime.fromtimestamp(commit['timestamp']),
                    'last_commit': datetime.fromtimestamp(commit['timestamp'])
                }

            contributor = self.contributors[author]
            contributor['commits'] += 1
            contributor['insertions'] += commit['insertions']
            contributor['deletions'] += commit['deletions']
            contributor['files_changed'] += commit['files_changed']

            commit_date = datetime.fromtimestamp(commit['timestamp'])
            if commit_date < contributor['first_commit']:
                contributor['first_commit'] = commit_date
            if commit_date > contributor['last_commit']:
                contributor['last_commit'] = commit_date

        self.stats['total_contributors'] = len(self.contributors)

        # Calculate total lines
        for contributor in self.contributors.values():
            self.stats['lines_added'] += contributor['insertions']
            self.stats['lines_deleted'] += contributor['deletions']

    def _analyze_files(self):
        """Analyze file statistics"""
        # Get all files in the repository
        files_output = self._run_git_command(['ls-files'])
        if files_output:
            all_files = files_output.split('\n')
            self.stats['total_files'] = len(all_files)

            # Get most changed files
            for filepath in all_files[:100]:  # Limit to first 100 for performance
                log_output = self._run_git_command([
                    'log',
                    '--follow',
                    '--pretty=format:',
                    '--numstat',
                    '--',
                    filepath
                ])

                if log_output:
                    changes = 0
                    additions = 0
                    deletions = 0

                    for line in log_output.split('\n'):
                        if '\t' in line:
                            parts = line.split('\t')
                            if len(parts) >= 2:
                                try:
                                    added = int(parts[0]) if parts[0] != '-' else 0
                                    deleted = int(parts[1]) if parts[1] != '-' else 0
                                    additions += added
                                    deletions += deleted
                                    changes += 1
                                except ValueError:
                                    pass

                    if changes > 0:
                        self.file_stats[filepath] = {
                            'changes': changes,
                            'additions': additions,
                            'deletions': deletions
                        }

    def _calculate_stats(self):
        """Calculate additional statistics"""
        pass

    def get_summary(self) -> str:
        """Get summary statistics"""
        output = []

        # Header
        repo_name = self.repo_path.name
        output.append(self._colorize(f"\n{'=' * 60}", Colors.BRIGHT_CYAN))
        output.append(self._colorize(f"Git Repository Statistics: {repo_name}", Colors.BRIGHT_CYAN + Colors.BOLD))
        output.append(self._colorize(f"{'=' * 60}\n", Colors.BRIGHT_CYAN))

        # Basic stats
        output.append(self._colorize("📊 Overview", Colors.BRIGHT_YELLOW + Colors.BOLD))
        output.append(f"  Repository: {self.repo_path}")
        output.append(f"  Total Commits: {self._colorize(str(self.stats['total_commits']), Colors.GREEN)}")
        output.append(f"  Total Contributors: {self._colorize(str(self.stats['total_contributors']), Colors.GREEN)}")
        output.append(f"  Total Files: {self._colorize(str(self.stats['total_files']), Colors.GREEN)}")
        output.append(f"  Active Days: {self._colorize(str(self.stats['active_days']), Colors.GREEN)}")

        if self.stats['first_commit']:
            output.append(f"  First Commit: {self.stats['first_commit'].strftime('%Y-%m-%d')}")
        if self.stats['last_commit']:
            output.append(f"  Last Commit: {self.stats['last_commit'].strftime('%Y-%m-%d')}")

        if self.stats['first_commit'] and self.stats['last_commit']:
            age = (self.stats['last_commit'] - self.stats['first_commit']).days
            output.append(f"  Repository Age: {age} days")

        lines_added_str = self._colorize(f"+{self.stats['lines_added']}", Colors.GREEN)
        output.append(f"  Lines Added: {lines_added_str}")
        lines_deleted_str = self._colorize(f"-{self.stats['lines_deleted']}", Colors.RED)
        output.append(f"  Lines Deleted: {lines_deleted_str}")
        net_lines = self.stats['lines_added'] - self.stats['lines_deleted']
        net_lines_str = self._colorize(str(net_lines), Colors.CYAN)
        output.append(f"  Net Lines: {net_lines_str}")

        return '\n'.join(output)

    def get_contributors_report(self, top_n: int = 10) -> str:
        """Get contributors report"""
        output = []

        output.append(f"\n{self._colorize('👥 Top Contributors', Colors.BRIGHT_MAGENTA + Colors.BOLD)}")
        output.append(self._colorize("-" * 60, Colors.BRIGHT_MAGENTA))

        # Sort by commits
        sorted_contributors = sorted(
            self.contributors.items(),
            key=lambda x: x[1]['commits'],
            reverse=True
        )

        for i, (name, stats) in enumerate(sorted_contributors[:top_n], 1):
            commits = stats['commits']
            insertions = stats['insertions']
            deletions = stats['deletions']
            net = insertions - deletions

            output.append(f"\n{i}. {self._colorize(name, Colors.BRIGHT_CYAN + Colors.BOLD)} <{stats['email']}>")
            output.append(f"   Commits: {self._colorize(str(commits), Colors.GREEN)}")
            output.append(f"   Lines: {self._colorize(f'+{insertions}', Colors.GREEN)} / {self._colorize(f'-{deletions}', Colors.RED)} ({net:+d})")
            output.append(f"   Active: {stats['first_commit'].strftime('%Y-%m-%d')} to {stats['last_commit'].strftime('%Y-%m-%d')}")

        return '\n'.join(output)

    def get_file_report(self, top_n: int = 10) -> str:
        """Get most changed files report"""
        output = []

        output.append(f"\n{self._colorize('📁 Most Changed Files', Colors.BRIGHT_BLUE + Colors.BOLD)}")
        output.append(self._colorize("-" * 60, Colors.BRIGHT_BLUE))

        # Sort by changes
        sorted_files = sorted(
            self.file_stats.items(),
            key=lambda x: x[1]['changes'],
            reverse=True
        )

        for i, (filepath, stats) in enumerate(sorted_files[:top_n], 1):
            changes = stats['changes']
            additions = stats['additions']
            deletions = stats['deletions']

            output.append(f"\n{i}. {self._colorize(filepath, Colors.CYAN)}")
            output.append(f"   Changes: {self._colorize(str(changes), Colors.YELLOW)}")
            output.append(f"   Lines: {self._colorize(f'+{additions}', Colors.GREEN)} / {self._colorize(f'-{deletions}', Colors.RED)}")

        return '\n'.join(output)

    def get_activity_heatmap(self) -> str:
        """Get commit activity heatmap"""
        output = []

        output.append(f"\n{self._colorize('📅 Commit Activity Heatmap', Colors.BRIGHT_GREEN + Colors.BOLD)}")
        output.append(self._colorize("-" * 60, Colors.BRIGHT_GREEN))

        # Day of week distribution
        output.append(f"\n{self._colorize('By Day of Week:', Colors.YELLOW)}")
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        max_commits = max(self.day_of_week_commits.values()) if self.day_of_week_commits else 1

        for day in days_order:
            count = self.day_of_week_commits.get(day, 0)
            bar_length = int((count / max_commits) * 30) if max_commits > 0 else 0
            bar = '█' * bar_length
            output.append(f"  {day:10} {self._colorize(bar, Colors.GREEN)} {count}")

        # Hour of day distribution
        output.append(f"\n{self._colorize('By Hour of Day:', Colors.YELLOW)}")
        max_hourly = max(self.hourly_commits.values()) if self.hourly_commits else 1

        for hour in range(24):
            count = self.hourly_commits.get(hour, 0)
            bar_length = int((count / max_hourly) * 30) if max_hourly > 0 else 0
            bar = '█' * bar_length
            output.append(f"  {hour:02d}:00 {self._colorize(bar, Colors.BLUE)} {count}")

        return '\n'.join(output)

    def get_recent_activity(self, days: int = 30) -> str:
        """Get recent activity report"""
        output = []

        output.append(f"\n{self._colorize(f'🕒 Recent Activity (Last {days} Days)', Colors.BRIGHT_YELLOW + Colors.BOLD)}")
        output.append(self._colorize("-" * 60, Colors.BRIGHT_YELLOW))

        # Filter recent commits
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_commits = [
            c for c in self.commit_history
            if datetime.fromtimestamp(c['timestamp']) >= cutoff_date
        ]

        if not recent_commits:
            output.append(f"  {self._colorize('No commits in the last ' + str(days) + ' days', Colors.DIM)}")
            return '\n'.join(output)

        output.append(f"  Total Commits: {self._colorize(str(len(recent_commits)), Colors.GREEN)}")

        # Recent contributors
        recent_authors = Counter(c['author'] for c in recent_commits)
        output.append(f"\n  {self._colorize('Active Contributors:', Colors.CYAN)}")
        for author, count in recent_authors.most_common(5):
            output.append(f"    {author}: {self._colorize(str(count), Colors.GREEN)} commits")

        # Show last 5 commits
        output.append(f"\n  {self._colorize('Latest Commits:', Colors.CYAN)}")
        for commit in recent_commits[:5]:
            dt = datetime.fromtimestamp(commit['timestamp'])
            short_hash = commit['hash'][:7]
            message = commit['message'][:50]
            output.append(f"    {self._colorize(short_hash, Colors.YELLOW)} {dt.strftime('%Y-%m-%d')} {message}")

        return '\n'.join(output)

    def export_json(self, filepath: str):
        """Export statistics to JSON"""
        data = {
            'repository': str(self.repo_path),
            'stats': {
                **self.stats,
                'first_commit': self.stats['first_commit'].isoformat() if self.stats['first_commit'] else None,
                'last_commit': self.stats['last_commit'].isoformat() if self.stats['last_commit'] else None
            },
            'contributors': {
                name: {
                    **stats,
                    'first_commit': stats['first_commit'].isoformat(),
                    'last_commit': stats['last_commit'].isoformat()
                }
                for name, stats in self.contributors.items()
            },
            'files': self.file_stats,
            'activity': {
                'daily': {str(k): v for k, v in self.daily_commits.items()},
                'hourly': dict(self.hourly_commits),
                'day_of_week': dict(self.day_of_week_commits)
            }
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        print(f"\n{self._colorize('✓', Colors.GREEN)} Statistics exported to: {filepath}")

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="GitStats - Repository Statistics Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Analyze current directory
  %(prog)s /path/to/repo            # Analyze specific repository
  %(prog)s --contributors 20        # Show top 20 contributors
  %(prog)s --files 15               # Show top 15 most changed files
  %(prog)s --recent 60              # Show activity in last 60 days
  %(prog)s --export stats.json      # Export to JSON
  %(prog)s --full                   # Full report with all sections
        """)

    parser.add_argument('repo', nargs='?', default='.',
                       help='Path to git repository (default: current directory)')

    # Report sections
    parser.add_argument('--contributors', type=int, metavar='N',
                       help='Show top N contributors (default: 10 with --full)')
    parser.add_argument('--files', type=int, metavar='N',
                       help='Show top N most changed files (default: 10 with --full)')
    parser.add_argument('--activity', action='store_true',
                       help='Show activity heatmap')
    parser.add_argument('--recent', type=int, metavar='DAYS',
                       help='Show activity in recent N days (default: 30 with --full)')
    parser.add_argument('--full', action='store_true',
                       help='Show full report with all sections')

    # Output options
    parser.add_argument('--export', metavar='FILE',
                       help='Export statistics to JSON file')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')

    # Version
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')

    args = parser.parse_args()

    try:
        # Create analyzer
        stats = GitStats(
            repo_path=args.repo,
            colors=not args.no_color,
            verbose=args.verbose
        )

        # Analyze repository
        stats.analyze()

        # Show summary (always)
        print(stats.get_summary())

        # Show requested sections
        if args.full or args.contributors is not None:
            top_n = args.contributors if args.contributors else 10
            print(stats.get_contributors_report(top_n))

        if args.full or args.files is not None:
            top_n = args.files if args.files else 10
            print(stats.get_file_report(top_n))

        if args.full or args.activity:
            print(stats.get_activity_heatmap())

        if args.full or args.recent is not None:
            days = args.recent if args.recent else 30
            print(stats.get_recent_activity(days))

        # Export if requested
        if args.export:
            stats.export_json(args.export)

        print()  # Final newline

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
