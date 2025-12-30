#!/usr/bin/env python3
"""
Repository cleanup module for GitLab Cloner.

This module provides functionality to clean up unnecessary files from repositories
after cloning/pulling, including build artifacts, dependencies, and temporary files.
"""

import logging
import fnmatch
import subprocess
from pathlib import Path
from typing import List, Set, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class CleanupConfig:
    """Configuration for repository cleanup operations."""

    enabled: bool = False
    """Enable/disable cleanup feature"""

    dry_run: bool = False
    """Preview what would be removed without actually deleting"""

    auto_commit: bool = False
    """Automatically commit and push changes after cleanup"""

    cleanup_history: bool = False
    """Rewrite git history to remove files from past commits"""

    patterns_to_remove: List[str] = field(default_factory=lambda: [
        # Build artifacts
        'target/', 'build/', 'dist/', 'out/',
        # Dependency directories
        'node_modules/', 'vendor/', '.venv/', 'venv/',
        # Compiled files
        '*.jar', '*.war', '*.class', '*.pyc', '__pycache__/',
        # IDE/editor files
        '.vscode/', '.idea/', '*.swp', '*.swo', '.DS_Store', 'Thumbs.db',
        # Log files
        '*.log',
        # Temporary files
        '*.tmp', '*.temp', '*.bak', '*.zip', '*.rar'
    ])
    """Patterns of files/directories to remove"""

    patterns_to_keep: List[str] = field(default_factory=list)
    """Whitelist patterns to exclude from removal"""

    commit_message: str = "chore: cleanup unnecessary files"
    """Commit message for cleanup changes"""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'enabled': self.enabled,
            'dry_run': self.dry_run,
            'auto_commit': self.auto_commit,
            'cleanup_history': self.cleanup_history,
            'patterns_to_remove': self.patterns_to_remove,
            'patterns_to_keep': self.patterns_to_keep,
            'commit_message': self.commit_message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CleanupConfig':
        """Create config from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class RepositoryCleanup:
    """Handles cleanup operations for Git repositories."""
    
    def __init__(self, config: CleanupConfig, logger: Optional[logging.Logger] = None):
        """
        Initialize repository cleanup handler.

        Args:
            config: CleanupConfig instance with cleanup settings
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger('gitlab_cloner.cleanup')
        self.removed_files: Set[Path] = set()
        self.gitignore_modified: bool = False
        self.git_cache_modified: bool = False
    
    def should_remove(self, path: Path, repo_root: Path) -> bool:
        """
        Determine if a path should be removed based on patterns.

        Args:
            path: Path to check
            repo_root: Root directory of the repository

        Returns:
            True if path should be removed, False otherwise
        """
        # Get relative path from repo root
        try:
            rel_path = path.relative_to(repo_root)
        except ValueError:
            return False

        # Check whitelist first
        for keep_pattern in self.config.patterns_to_keep:
            if fnmatch.fnmatch(str(rel_path), keep_pattern):
                self.logger.debug(f"      [PATTERN] Whitelisted (keep): {rel_path} matches pattern '{keep_pattern}'")
                return False

        # Check removal patterns
        for remove_pattern in self.config.patterns_to_remove:
            if fnmatch.fnmatch(str(rel_path), remove_pattern):
                self.logger.debug(f"      [PATTERN] Match found: {rel_path} matches pattern '{remove_pattern}'")
                return True
            # Also check if directory name matches (for directories like node_modules/)
            if path.is_dir() and fnmatch.fnmatch(path.name + '/', remove_pattern):
                self.logger.debug(f"      [PATTERN] Match found: {rel_path}/ matches pattern '{remove_pattern}'")
                return True

        return False
    
    def cleanup_repository(self, repo_path: Path) -> bool:
        """
        Clean up unnecessary files from a repository.

        Args:
            repo_path: Path to the repository

        Returns:
            True if cleanup successful, False otherwise
        """
        if not self.config.enabled:
            return True

        try:
            self.removed_files.clear()
            self.logger.info(f"      [CLEANUP] Starting cleanup scan for repository: {repo_path}")
            self.logger.info(f"      [CLEANUP] Scanning for files matching patterns...")

            files_scanned = 0
            files_matched = 0

            # Find and remove files matching patterns
            for item in repo_path.rglob('*'):
                files_scanned += 1

                # Skip .git directory
                if '.git' in item.parts:
                    self.logger.debug(f"      [CLEANUP] Skipping .git directory: {item}")
                    continue

                if self.should_remove(item, repo_path):
                    files_matched += 1
                    self.logger.info(f"      [CLEANUP] Removing: {item}")
                    self._remove_item(item)

            self.logger.info(f"      [CLEANUP] Scan complete: {files_scanned} files scanned, {files_matched} matched patterns")

            if self.removed_files:
                self.logger.info(f"      [CLEANUP] Successfully removed {len(self.removed_files)} items")
                return True
            else:
                self.logger.info(f"      [CLEANUP] No files matched cleanup patterns")
                return True

        except Exception as e:
            self.logger.error(f"      [CLEANUP] Error during cleanup of {repo_path}: {e}")
            return False
    
    def _remove_item(self, path: Path) -> None:
        """Remove a file or directory."""
        try:
            if self.config.dry_run:
                item_type = "directory" if path.is_dir() else "file"
                self.logger.info(f"        [DRY-RUN] Would remove {item_type}: {path}")
            else:
                if path.is_dir():
                    import shutil
                    shutil.rmtree(path)
                    self.logger.info(f"        [REMOVED] Directory: {path}")
                else:
                    path.unlink()
                    self.logger.info(f"        [REMOVED] File: {path}")

            self.removed_files.add(path)
        except Exception as e:
            self.logger.warning(f"        [ERROR] Failed to remove {path}: {e}")

    def update_gitignore(self, repo_path: Path) -> bool:
        """
        Update .gitignore file to include cleanup patterns.

        Args:
            repo_path: Path to the repository

        Returns:
            True if successful, False otherwise
        """
        try:
            gitignore_path = repo_path / '.gitignore'

            # Patterns to add to .gitignore (extracted from cleanup patterns)
            gitignore_patterns = [
                '# Archive and Compressed Files',
                '*.zip',
                '*.rar',
                '*.tar',
                '*.tar.gz',
                '*.tar.bz2',
                '*.7z',
                '*.gz',
                '*.bz2',
                '*.xz',
                '',
                '# Build Artifacts and Compiled Files',
                '*.jar',
                '*.war',
                '*.class',
                '*.o',
                '*.so',
                '*.exe',
                '*.dll',
                '*.dylib',
                '',
                '# Temporary and Backup Files',
                '*.tmp',
                '*.temp',
                '*.bak',
                '*.backup',
            ]

            # Read existing .gitignore if it exists
            existing_content = ''
            if gitignore_path.exists():
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    existing_content = f.read()

            # Check which patterns are already in .gitignore
            patterns_to_add = []
            for pattern in gitignore_patterns:
                if pattern and pattern not in existing_content:
                    patterns_to_add.append(pattern)

            # If there are new patterns to add, update .gitignore
            if patterns_to_add:
                self.logger.info(f"      [GITIGNORE] Updating .gitignore with cleanup patterns")

                # Append new patterns to .gitignore
                with open(gitignore_path, 'a', encoding='utf-8') as f:
                    if existing_content and not existing_content.endswith('\n'):
                        f.write('\n')
                    f.write('\n# Cleanup patterns added by gitlab-cloner\n')
                    for pattern in patterns_to_add:
                        f.write(f"{pattern}\n")

                self.logger.info(f"      [GITIGNORE] Added {len(patterns_to_add)} patterns to .gitignore")
                self.gitignore_modified = True
                return True
            else:
                self.logger.info(f"      [GITIGNORE] All cleanup patterns already in .gitignore")
                return True

        except Exception as e:
            self.logger.warning(f"      [GITIGNORE] Failed to update .gitignore: {e}")
            return False

    def remove_from_git_cache(self, repo_path: Path) -> bool:
        """
        Remove files matching cleanup patterns from Git's cache.

        This removes files from Git's index without deleting them from disk,
        allowing .gitignore rules to take effect for existing files.

        Args:
            repo_path: Path to the repository

        Returns:
            True if successful, False otherwise
        """
        try:
            # Patterns to remove from Git cache
            cache_patterns = [
                '*.zip', '*.rar', '*.tar', '*.tar.gz', '*.tar.bz2', '*.7z', '*.gz', '*.bz2', '*.xz',
                '*.jar', '*.war', '*.class', '*.o', '*.so', '*.exe', '*.dll', '*.dylib',
                '*.tmp', '*.temp', '*.bak', '*.backup',
            ]

            self.logger.info(f"      [GIT-CACHE] Removing cleanup patterns from Git cache")

            removed_count = 0
            for pattern in cache_patterns:
                try:
                    # Use git rm --cached to remove from index without deleting files
                    result = subprocess.run(
                        ['git', 'rm', '--cached', '-r', '-f', pattern],
                        cwd=str(repo_path),
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    if result.returncode == 0:
                        # Count files removed (git output shows number of files)
                        if result.stdout:
                            self.logger.debug(f"      [GIT-CACHE] Removed pattern {pattern}: {result.stdout.strip()}")
                            removed_count += 1
                    else:
                        # Pattern might not match any files, which is fine
                        self.logger.debug(f"      [GIT-CACHE] No files matched pattern {pattern}")

                except subprocess.TimeoutExpired:
                    self.logger.warning(f"      [GIT-CACHE] Timeout removing pattern {pattern}")
                except Exception as e:
                    self.logger.debug(f"      [GIT-CACHE] Error removing pattern {pattern}: {e}")

            if removed_count > 0:
                self.logger.info(f"      [GIT-CACHE] Removed {removed_count} pattern(s) from Git cache")
                self.git_cache_modified = True
            else:
                self.logger.info(f"      [GIT-CACHE] No files to remove from Git cache")

            return True

        except Exception as e:
            self.logger.warning(f"      [GIT-CACHE] Failed to remove files from Git cache: {e}")
            return False

    def analyze_git_history(self, repo_path: Path) -> Dict[str, Any]:
        """
        Analyze git history to find files matching cleanup patterns across all branches.

        This method scans all branches without modifying anything, collecting statistics
        about which files would be removed and their impact.

        Args:
            repo_path: Path to the repository

        Returns:
            Dictionary with analysis results containing:
            - branches: Dict of branch analysis
            - total_files: Total unique files to remove
            - total_commits: Total commits affected
            - total_size: Estimated size in bytes
        """
        try:
            analysis = {
                'branches': {},
                'total_files': 0,
                'total_commits': 0,
                'total_size': 0,
                'file_patterns': []
            }

            # Extract file patterns (*.jar, *.war, etc.)
            file_patterns = [p for p in self.config.patterns_to_remove if p.startswith('*.')]
            analysis['file_patterns'] = file_patterns

            if not file_patterns:
                self.logger.info(f"      [HISTORY] No file patterns to analyze")
                return analysis

            # Get all branches
            try:
                result = subprocess.run(
                    ['git', 'branch', '-r'],
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode != 0:
                    self.logger.warning(f"      [HISTORY] Failed to get branches: {result.stderr}")
                    return analysis

                branches = [line.strip().replace('origin/', '').replace('HEAD -> ', '')
                           for line in result.stdout.strip().split('\n')
                           if line.strip() and not line.strip().endswith('/HEAD')]

            except Exception as e:
                self.logger.warning(f"      [HISTORY] Error getting branches: {e}")
                return analysis

            # Analyze each branch
            for branch_name in branches:
                try:
                    branch_analysis = self._analyze_branch_history(repo_path, branch_name, file_patterns)
                    if branch_analysis['files']:
                        analysis['branches'][branch_name] = branch_analysis
                        analysis['total_commits'] += branch_analysis['commit_count']
                        analysis['total_size'] += branch_analysis['total_size']

                except Exception as e:
                    self.logger.debug(f"      [HISTORY] Error analyzing branch {branch_name}: {e}")
                    continue

            # Count unique files across all branches
            all_files = set()
            for branch_data in analysis['branches'].values():
                all_files.update(branch_data['files'].keys())
            analysis['total_files'] = len(all_files)

            return analysis

        except Exception as e:
            self.logger.error(f"      [HISTORY] Error during history analysis: {e}")
            return {'branches': {}, 'total_files': 0, 'total_commits': 0, 'total_size': 0, 'file_patterns': []}

    def _analyze_branch_history(self, repo_path: Path, branch_name: str, file_patterns: List[str]) -> Dict[str, Any]:
        """
        Analyze a single branch's history for matching files.

        Args:
            repo_path: Path to the repository
            branch_name: Name of the branch to analyze
            file_patterns: List of file patterns to match

        Returns:
            Dictionary with branch analysis
        """
        branch_data = {
            'files': {},  # {filename: {'count': int, 'size': int}}
            'commit_count': 0,
            'total_size': 0
        }

        try:
            # Get all commits in this branch
            result = subprocess.run(
                ['git', 'rev-list', '--all', f'--remotes=origin/{branch_name}'],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                return branch_data

            commits = [c.strip() for c in result.stdout.strip().split('\n') if c.strip()]
            branch_data['commit_count'] = len(commits)

            # Find files matching patterns in this branch
            for pattern in file_patterns:
                try:
                    # Use git ls-tree to find files matching pattern
                    result = subprocess.run(
                        ['git', 'log', '--all', '--name-only', '--pretty=format:', f'--remotes=origin/{branch_name}'],
                        cwd=str(repo_path),
                        capture_output=True,
                        text=True,
                        timeout=60
                    )

                    if result.returncode == 0:
                        files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]

                        for file_path in files:
                            if fnmatch.fnmatch(file_path, pattern):
                                if file_path not in branch_data['files']:
                                    branch_data['files'][file_path] = {'count': 0, 'size': 0}
                                branch_data['files'][file_path]['count'] += 1

                except Exception as e:
                    self.logger.debug(f"      [HISTORY] Error analyzing pattern {pattern}: {e}")
                    continue

            # Estimate sizes
            for file_path in branch_data['files'].keys():
                try:
                    # Get file size from latest commit
                    result = subprocess.run(
                        ['git', 'cat-file', '-s', f'HEAD:{file_path}'],
                        cwd=str(repo_path),
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.returncode == 0:
                        size = int(result.stdout.strip())
                        branch_data['files'][file_path]['size'] = size
                        branch_data['total_size'] += size

                except Exception:
                    # If we can't get size, estimate it
                    branch_data['files'][file_path]['size'] = 0

            return branch_data

        except Exception as e:
            self.logger.debug(f"      [HISTORY] Error in branch analysis: {e}")
            return branch_data

    def cleanup_git_history(self, repo_path: Path) -> bool:
        """
        Remove files matching cleanup patterns from git history across all branches.

        This uses git-filter-repo to rewrite history and permanently remove files
        that match cleanup patterns from all commits. This is a destructive operation
        that rewrites commit hashes and requires force-pushing.

        Args:
            repo_path: Path to the repository

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"      [HISTORY] Starting git history cleanup...")
            self.logger.warning(f"      [HISTORY] This will rewrite git history and change all commit hashes!")

            # Build list of file patterns to remove from history
            # Convert patterns to git-filter-repo format
            file_patterns = []
            for pattern in self.config.patterns_to_remove:
                # Extract file patterns (*.jar, *.war, etc.)
                if pattern.startswith('*.'):
                    file_patterns.append(pattern)

            if not file_patterns:
                self.logger.info(f"      [HISTORY] No file patterns to remove from history")
                return True

            self.logger.info(f"      [HISTORY] Will remove {len(file_patterns)} file patterns from history:")
            for pattern in file_patterns:
                self.logger.info(f"      [HISTORY]   - {pattern}")

            if self.config.dry_run:
                self.logger.info(f"      [HISTORY] DRY-RUN: Analyzing git history across all branches...")
                self._report_history_analysis(repo_path)
                return True

            # Check if git-filter-repo is available before actual cleanup
            if not self._check_filter_repo_available():
                self.logger.error(f"      [HISTORY] git-filter-repo is not installed or not in PATH")
                self.logger.error(f"      [HISTORY] Install it with: pip install git-filter-repo")
                return False

            # Build git-filter-repo command
            cmd = ['git', 'filter-repo']

            # Add --invert-paths flag to remove (not keep) the patterns
            cmd.append('--invert-paths')

            # Add each file pattern
            for pattern in file_patterns:
                cmd.extend(['--path-glob', pattern])

            # Add --force flag to allow running in non-fresh clone
            cmd.append('--force')

            self.logger.info(f"      [HISTORY] Running: {' '.join(cmd)}")

            # Run git-filter-repo
            result = subprocess.run(
                cmd,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout for large repos
            )

            if result.returncode == 0:
                self.logger.info(f"      [HISTORY] Successfully rewrote git history")
                if result.stdout:
                    self.logger.debug(f"      [HISTORY] Output: {result.stdout}")
                return True
            else:
                self.logger.error(f"      [HISTORY] Failed to rewrite git history")
                self.logger.error(f"      [HISTORY] Error: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"      [HISTORY] Timeout while rewriting git history (>1 hour)")
            return False
        except Exception as e:
            self.logger.error(f"      [HISTORY] Error during git history cleanup: {e}")
            return False

    def _report_history_analysis(self, repo_path: Path) -> None:
        """
        Generate and log a detailed analysis report of git history.

        Args:
            repo_path: Path to the repository
        """
        try:
            analysis = self.analyze_git_history(repo_path)

            if not analysis['branches']:
                self.logger.info(f"      [HISTORY] No files matching patterns found in history")
                return

            # Report per-branch analysis
            self.logger.info(f"      [HISTORY] Analysis Results:")
            self.logger.info(f"      [HISTORY] {'='*60}")

            for branch_name, branch_data in sorted(analysis['branches'].items()):
                self.logger.info(f"      [HISTORY] Branch: {branch_name} ({branch_data['commit_count']} commits)")
                self.logger.info(f"      [HISTORY]   Files to remove from history:")

                for file_path in sorted(branch_data['files'].keys()):
                    file_info = branch_data['files'][file_path]
                    size_mb = file_info['size'] / (1024 * 1024)
                    self.logger.info(f"      [HISTORY]     - {file_path} (appears in {file_info['count']} commits, ~{size_mb:.1f} MB)")

                total_size_mb = branch_data['total_size'] / (1024 * 1024)
                self.logger.info(f"      [HISTORY]   Total: {len(branch_data['files'])} files, {branch_data['commit_count']} commits, ~{total_size_mb:.1f} MB")
                self.logger.info(f"      [HISTORY]")

            # Summary
            self.logger.info(f"      [HISTORY] {'='*60}")
            self.logger.info(f"      [HISTORY] SUMMARY - DRY-RUN REPORT")
            self.logger.info(f"      [HISTORY] {'='*60}")
            self.logger.info(f"      [HISTORY] Total branches analyzed: {len(analysis['branches'])}")
            self.logger.info(f"      [HISTORY] Total unique files to remove: {analysis['total_files']}")
            self.logger.info(f"      [HISTORY] Total commit references: {analysis['total_commits']}")

            total_size_mb = analysis['total_size'] / (1024 * 1024)
            self.logger.info(f"      [HISTORY] Estimated size reduction: ~{total_size_mb:.1f} MB")
            self.logger.info(f"      [HISTORY]")
            self.logger.warning(f"      [HISTORY] WARNING: This will rewrite ALL commit hashes!")
            self.logger.info(f"      [HISTORY]")
            self.logger.info(f"      [HISTORY] DRY-RUN: No changes made to repository")
            self.logger.info(f"      [HISTORY] To actually rewrite history, run with --cleanup-auto-commit")

        except Exception as e:
            self.logger.error(f"      [HISTORY] Error generating analysis report: {e}")

    def _check_filter_repo_available(self) -> bool:
        """
        Check if git-filter-repo is available.

        Returns:
            True if git-filter-repo is available, False otherwise
        """
        try:
            result = subprocess.run(
                ['git', 'filter-repo', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

