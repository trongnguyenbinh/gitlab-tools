#!/usr/bin/env python3
"""
GitLab Repository Cloner

A tool to recursively clone all Git repositories from a GitLab self-hosted server
within a specified group hierarchy.
"""

import os
import sys
import logging
from pathlib import Path
from collections import deque
from typing import List, Dict, Any, Optional
import time

import requests
import gitlab
from git import Repo, GitCommandError
import click

from .progress import ProgressManager, BranchProgressManager, ErrorRecord
from .cleanup import CleanupConfig, RepositoryCleanup


class GitLabCloner:
    """Main class for cloning GitLab repositories recursively."""
    
    def __init__(self, gitlab_url: str, access_token: str, destination_path: str, quiet: bool = False, cleanup_config: Optional[CleanupConfig] = None):
        """
        Initialize the GitLab cloner.

        Args:
            gitlab_url: Base URL of the GitLab instance
            access_token: GitLab API access token
            destination_path: Local path where repositories will be cloned
            quiet: If True, suppress detailed logging and show progress bar only
            cleanup_config: Optional CleanupConfig for repository cleanup operations
        """
        self.gitlab_url = gitlab_url.rstrip('/')
        self.access_token = access_token
        self.destination_path = Path(destination_path).resolve()
        self.quiet = quiet

        # Initialize GitLab connection
        self.gl = gitlab.Gitlab(self.gitlab_url, private_token=self.access_token)

        # Setup logging
        self.logger = self._setup_logging()

        # Cleanup configuration
        self.cleanup_config = cleanup_config or CleanupConfig(enabled=False)

        # Progress manager (set later in clone_group_recursively)
        self.progress_manager: Optional[ProgressManager] = None

        # Statistics
        self.stats = {
            'repositories_cloned': 0,
            'repositories_updated': 0,
            'groups_processed': 0,
            'errors': 0
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('gitlab_cloner')
        
        # In quiet mode, only show WARNING and ERROR level logs
        log_level = logging.WARNING if self.quiet else logging.INFO
        logger.setLevel(log_level)
        
        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        return logger
    
    def authenticate(self) -> bool:
        """
        Test GitLab authentication.

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            self.gl.auth()
            user = self.gl.user
            self.logger.info(f"Successfully authenticated as: {user.username}")
            return True
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False

    def _get_origin_remote(self, repo: Repo) -> Optional[Any]:
        """
        Safely get the 'origin' remote from a repository.

        Handles the case where repo.remotes is an IterableList and accessing
        it with dot notation may fail.

        Args:
            repo: GitPython Repo object

        Returns:
            The origin remote object, or None if not found
        """
        try:
            for remote in repo.remotes:
                if remote.name == 'origin':
                    return remote
            return None
        except Exception as e:
            self.logger.warning(f"Error getting origin remote: {e}")
            return None

    def get_group(self, group_identifier: str) -> Optional[Any]:
        """
        Get a GitLab group by ID or path.
        
        Args:
            group_identifier: Group ID (integer) or group path (string)
            
        Returns:
            GitLab group object or None if not found
        """
        try:
            # Try as integer ID first
            if group_identifier.isdigit():
                group = self.gl.groups.get(int(group_identifier))
            else:
                # Try as group path
                group = self.gl.groups.get(group_identifier)
            
            self.logger.info(f"Found group: {group.name} (ID: {group.id})")
            return group
        except Exception as e:
            self.logger.error(f"Failed to get group '{group_identifier}': {e}")
            return None
    
    def pull_all_branches(self, repo: Repo, project: Any) -> bool:
        """
        Fetch all remote branches and pull the latest code for existing repository.

        Args:
            repo: GitPython Repo object
            project: GitLab project object

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get origin remote safely
            origin = self._get_origin_remote(repo)
            if origin is None:
                self.logger.error(f"No 'origin' remote found for {project.name}")
                return False

            # Fetch all branches from remote
            self.logger.info(f"{'='*70}")
            self.logger.info(f"Starting branch processing for project: {project.name}")
            self.logger.info(f"{'='*70}")
            self.logger.info(f"Fetching all branches from remote for {project.name}")
            origin.fetch(prune=True)
            self.logger.info(f"Remote fetch completed successfully")

            # Get all remote branches
            remote_branches = [ref.name for ref in origin.refs if not ref.name.endswith('/HEAD')]
            self.logger.info(f"Found {len(remote_branches)} remote branches: {remote_branches}")

            # Store current branch
            current_branch = repo.active_branch.name if not repo.head.is_detached else None
            self.logger.info(f"Current branch before processing: {current_branch}")

            # Track cleanup statistics
            branches_processed = 0
            branches_with_cleanup = 0

            # Pull updates for each branch
            for idx, remote_ref in enumerate(remote_branches, 1):
                try:
                    # Extract branch name (remove 'origin/' prefix)
                    branch_name = remote_ref.replace('origin/', '')

                    self.logger.info(f"\n[{idx}/{len(remote_branches)}] Processing branch: {branch_name}")
                    self.logger.info(f"  Remote reference: {remote_ref}")

                    # Check if local branch exists
                    if branch_name in [b.name for b in repo.heads]:
                        # Checkout and pull existing branch
                        self.logger.info(f"  Local branch exists, pulling updates...")
                        repo.git.checkout(branch_name)
                        self.logger.info(f"  ✓ Checked out branch: {branch_name}")
                        origin.pull(branch_name)
                        self.logger.info(f"  ✓ Pulled latest updates for branch: {branch_name}")
                    else:
                        # Create new local branch tracking remote
                        self.logger.info(f"  Local branch does not exist, creating new tracking branch...")
                        repo.git.checkout('-b', branch_name, remote_ref)
                        self.logger.info(f"  ✓ Created new local branch: {branch_name} tracking {remote_ref}")

                    branches_processed += 1

                    # Run cleanup on this branch if enabled
                    if self.cleanup_config.enabled:
                        self.logger.info(f"  Cleanup is enabled, starting cleanup process...")
                        cleanup_success = self._cleanup_branch(repo, branch_name)
                        if cleanup_success:
                            branches_with_cleanup += 1
                            self.logger.info(f"  ✓ Cleanup completed successfully for branch: {branch_name}")
                        else:
                            self.logger.warning(f"  ✗ Cleanup failed for branch: {branch_name}")
                    else:
                        self.logger.debug(f"  Cleanup is disabled, skipping cleanup for this branch")

                except GitCommandError as e:
                    self.logger.warning(f"  ✗ Failed to process branch {branch_name}: {e}")
                    continue

            # Run history cleanup if enabled (after all branches are processed)
            if self.cleanup_config.enabled and self.cleanup_config.cleanup_history:
                self.logger.info(f"\n{'='*70}")
                self.logger.info(f"Starting git history cleanup for {project.name}...")
                self.logger.info(f"{'='*70}")
                history_cleanup_success = self._cleanup_repository_history(repo)
                if history_cleanup_success:
                    self.logger.info(f"✓ Git history cleanup completed successfully")
                else:
                    self.logger.warning(f"✗ Git history cleanup failed or was skipped")

            # Return to original branch if possible
            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"Branch processing complete. Returning to original branch...")
            self.logger.info(f"{'='*70}")

            if current_branch:
                try:
                    repo.git.checkout(current_branch)
                    self.logger.info(f"✓ Successfully returned to original branch: {current_branch}")
                except GitCommandError:
                    self.logger.warning(f"✗ Could not return to original branch: {current_branch}")
            else:
                self.logger.info(f"Repository was in detached HEAD state, no branch to return to")

            # Summary
            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"SUMMARY for {project.name}:")
            self.logger.info(f"  Total branches found: {len(remote_branches)}")
            self.logger.info(f"  Branches processed: {branches_processed}")
            if self.cleanup_config.enabled:
                self.logger.info(f"  Branches with cleanup: {branches_with_cleanup}")
            self.logger.info(f"  Status: Successfully updated all branches")
            self.logger.info(f"{'='*70}\n")

            return True

        except GitCommandError as e:
            self.logger.error(f"Git error pulling branches for {project.name}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error pulling branches for {project.name}: {e}")
            return False
    
    def _cleanup_branch(self, repo: Repo, branch_name: str) -> bool:
        """
        Run cleanup operations on a specific branch.

        Args:
            repo: GitPython Repo object
            branch_name: Name of the branch to clean up

        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            repo_path = Path(repo.working_dir)
            self.logger.info(f"    [CLEANUP] Starting cleanup for branch: {branch_name}")
            self.logger.info(f"    [CLEANUP] Repository path: {repo_path}")
            self.logger.info(f"    [CLEANUP] Cleanup mode: {'DRY-RUN' if self.cleanup_config.dry_run else 'ACTUAL'}")
            self.logger.info(f"    [CLEANUP] Auto-commit enabled: {self.cleanup_config.auto_commit}")
            self.logger.info(f"    [CLEANUP] Patterns to remove: {self.cleanup_config.patterns_to_remove}")
            if self.cleanup_config.patterns_to_keep:
                self.logger.info(f"    [CLEANUP] Whitelist patterns: {self.cleanup_config.patterns_to_keep}")

            cleanup = RepositoryCleanup(self.cleanup_config, self.logger)

            # Run cleanup
            if not cleanup.cleanup_repository(repo_path):
                self.logger.error(f"    [CLEANUP] Cleanup operation failed for branch: {branch_name}")
                return False

            # Report cleanup results
            if cleanup.removed_files:
                self.logger.info(f"    [CLEANUP] Files/directories removed: {len(cleanup.removed_files)}")
                for removed_path in sorted(cleanup.removed_files):
                    self.logger.info(f"    [CLEANUP]   - {removed_path}")
            else:
                self.logger.info(f"    [CLEANUP] No files matched cleanup patterns")

            # Update .gitignore to prevent future tracking of cleanup patterns
            self.logger.info(f"    [CLEANUP] Updating .gitignore with cleanup patterns...")
            cleanup.update_gitignore(repo_path)
            if cleanup.gitignore_modified:
                self.logger.info(f"    [CLEANUP] .gitignore updated successfully")
            else:
                self.logger.info(f"    [CLEANUP] .gitignore already contains all cleanup patterns")

            # Remove files from Git cache to apply .gitignore rules to existing files
            self.logger.info(f"    [CLEANUP] Removing cleanup patterns from Git cache...")
            cleanup.remove_from_git_cache(repo_path)
            if cleanup.git_cache_modified:
                self.logger.info(f"    [CLEANUP] Git cache cleaned successfully")
            else:
                self.logger.info(f"    [CLEANUP] No files to remove from Git cache")

            # Handle auto-commit: commit and push if enabled and there are changes
            has_changes = cleanup.removed_files or cleanup.gitignore_modified or cleanup.git_cache_modified

            if self.cleanup_config.auto_commit and has_changes:
                self._commit_and_push_cleanup(repo, branch_name)
            elif cleanup.removed_files and not self.cleanup_config.auto_commit:
                self.logger.info(f"    [CLEANUP] Files were removed but auto-commit is disabled")
                self.logger.info(f"    [CLEANUP] Changes are local only and not committed")
            elif cleanup.gitignore_modified and not self.cleanup_config.auto_commit:
                self.logger.info(f"    [CLEANUP] .gitignore was updated but auto-commit is disabled")
                self.logger.info(f"    [CLEANUP] Changes are local only and not committed")
            else:
                self.logger.info(f"    [CLEANUP] No changes to commit")

            return True

        except Exception as e:
            self.logger.error(f"    [CLEANUP] Error during cleanup of branch {branch_name}: {e}")
            return False

    def _commit_and_push_cleanup(self, repo: Repo, branch_name: str) -> bool:
        """
        Commit and push cleanup changes (.gitignore and git cache removals).

        This method stages all changes, commits them with the configured message,
        and pushes to the remote repository.

        Args:
            repo: GitPython Repo object
            branch_name: Name of the branch to commit/push

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get origin remote safely
            origin = self._get_origin_remote(repo)
            if origin is None:
                self.logger.error(f"    [CLEANUP] No 'origin' remote found")
                return False

            self.logger.info(f"    [CLEANUP] Auto-commit enabled, staging changes...")

            # Stage all changes (including .gitignore updates and git cache removals)
            repo.git.add('-A')
            self.logger.info(f"    [CLEANUP] Changes staged successfully")

            # Check if there are actually changes to commit
            status = repo.git.status('--porcelain')
            if not status:
                self.logger.info(f"    [CLEANUP] No staged changes to commit")
                return True

            # Commit changes
            self.logger.info(f"    [CLEANUP] Committing with message: '{self.cleanup_config.commit_message}'")
            repo.git.commit('-m', self.cleanup_config.commit_message)
            self.logger.info(f"    [CLEANUP] Committed cleanup changes on branch: {branch_name}")

            # Push changes to remote
            self.logger.info(f"    [CLEANUP] Pushing changes to remote...")
            origin.push(branch_name)
            self.logger.info(f"    [CLEANUP] Pushed cleanup changes on branch: {branch_name}")

            return True

        except GitCommandError as e:
            self.logger.warning(f"    [CLEANUP] Failed to commit/push cleanup on {branch_name}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"    [CLEANUP] Unexpected error during commit/push on {branch_name}: {e}")
            return False

    def _cleanup_repository_history(self, repo: Repo) -> bool:
        """
        Clean up git history by removing junk files from all commits across all branches.

        This method uses git-filter-repo to rewrite history and permanently remove files
        matching cleanup patterns from all commits. This is a destructive operation that
        rewrites commit hashes and requires force-pushing to all branches.

        Args:
            repo: GitPython Repo object

        Returns:
            True if successful, False otherwise
        """
        try:
            repo_path = Path(repo.working_dir)
            self.logger.info(f"    [HISTORY] Starting git history cleanup for repository: {repo_path}")

            cleanup = RepositoryCleanup(self.cleanup_config, self.logger)

            # Run history cleanup
            if not cleanup.cleanup_git_history(repo_path):
                self.logger.error(f"    [HISTORY] Git history cleanup failed")
                return False

            self.logger.info(f"    [HISTORY] Git history rewritten successfully")

            # Force push all branches to remote
            if not self.cleanup_config.dry_run:
                self.logger.info(f"    [HISTORY] Force pushing all branches to remote...")
                if self._force_push_all_branches(repo):
                    self.logger.info(f"    [HISTORY] Successfully force pushed all branches")
                    return True
                else:
                    self.logger.error(f"    [HISTORY] Failed to force push some branches")
                    return False
            else:
                self.logger.info(f"    [HISTORY] DRY-RUN: Would force push all branches to remote")
                return True

        except Exception as e:
            self.logger.error(f"    [HISTORY] Error during git history cleanup: {e}")
            return False

    def _force_push_all_branches(self, repo: Repo) -> bool:
        """
        Force push all local branches to remote after history rewrite.

        Args:
            repo: GitPython Repo object

        Returns:
            True if all branches pushed successfully, False otherwise
        """
        try:
            # Get the origin remote safely
            origin = self._get_origin_remote(repo)
            if origin is None:
                self.logger.error(f"    [HISTORY] No 'origin' remote found in repository")
                return False

            # Get all local branches
            local_branches = [branch.name for branch in repo.heads]
            self.logger.info(f"    [HISTORY] Force pushing {len(local_branches)} branches to remote...")

            success_count = 0
            fail_count = 0

            for branch_name in local_branches:
                try:
                    self.logger.info(f"    [HISTORY] Force pushing branch: {branch_name}")
                    origin.push(branch_name, force=True)
                    self.logger.info(f"    [HISTORY] ✓ Successfully force pushed: {branch_name}")
                    success_count += 1
                except GitCommandError as e:
                    self.logger.error(f"    [HISTORY] ✗ Failed to force push {branch_name}: {e}")
                    fail_count += 1

            self.logger.info(f"    [HISTORY] Force push summary: {success_count} succeeded, {fail_count} failed")

            return fail_count == 0

        except Exception as e:
            self.logger.error(f"    [HISTORY] Error during force push: {e}")
            return False

    def _fetch_all_remote_branches(self, repo: Repo, project: Any) -> bool:
        """
        Fetch all remote branches and create local tracking branches.

        Args:
            repo: GitPython Repo object
            project: GitLab project object (for logging)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get origin remote safely
            origin = self._get_origin_remote(repo)
            if origin is None:
                self.logger.error(f"No 'origin' remote found for {project.name}")
                return False

            # Fetch all branches from remote
            self.logger.info(f"Fetching all remote branches for {project.name}")
            origin.fetch(prune=True)

            # Get all remote branches
            remote_branches = [ref.name for ref in origin.refs if not ref.name.endswith('/HEAD')]
            self.logger.info(f"Found {len(remote_branches)} remote branches")
            
            if not remote_branches:
                self.logger.info(f"No remote branches found for {project.name}")
                return True
            
            # Create local tracking branches for each remote branch
            for remote_ref in remote_branches:
                try:
                    # Extract branch name (remove 'origin/' prefix)
                    branch_name = remote_ref.replace('origin/', '')
                    
                    # Check if local branch already exists
                    if branch_name in [b.name for b in repo.heads]:
                        self.logger.debug(f"Local branch already exists: {branch_name}")
                        continue
                    
                    # Create new local branch tracking remote
                    self.logger.info(f"Creating local branch: {branch_name}")
                    repo.git.checkout('-b', branch_name, remote_ref)
                    
                except GitCommandError as e:
                    self.logger.warning(f"Failed to create branch {branch_name}: {e}")
                    continue
            
            self.logger.info(f"Successfully fetched all branches for {project.name}")
            return True
            
        except GitCommandError as e:
            self.logger.error(f"Git error fetching branches for {project.name}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error fetching branches for {project.name}: {e}")
            return False
    
    def _count_total_repositories(self, group: Any) -> int:
        """
        Count total number of repositories in group and subgroups.
        
        Args:
            group: GitLab group object
            
        Returns:
            Total count of repositories
        """
        count = 0
        try:
            # Count projects in this group
            projects = group.projects.list(all=True, include_subgroups=False)
            count += len(projects)
            
            # Count projects in subgroups
            subgroups = group.subgroups.list(all=True)
            for subgroup in subgroups:
                full_subgroup = self.gl.groups.get(subgroup.id)
                count += self._count_total_repositories(full_subgroup)
        except Exception as e:
            self.logger.warning(f"Error counting repositories in group {group.name}: {e}")
        
        return count
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize project/group name for filesystem compatibility.
        
        Args:
            name: Original name from GitLab
            
        Returns:
            Sanitized name safe for filesystem use
        """
        # Strip leading/trailing whitespace
        sanitized = name.strip()
        
        # Replace or remove characters that are problematic on Windows
        invalid_chars = '<>:"|?*'
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove trailing dots and spaces (Windows restriction)
        sanitized = sanitized.rstrip('. ')
        
        return sanitized if sanitized else 'unnamed'
    
    def clone_repository(self, project: Any, local_path: Path) -> bool:
        """
        Clone a single repository or pull updates if it already exists.
        
        Args:
            project: GitLab project object
            local_path: Local directory path where repo should be cloned
            
        Returns:
            True if successful, False otherwise
        """
        # Sanitize the project name for filesystem compatibility
        sanitized_name = self._sanitize_name(project.name)
        repo_path = local_path / sanitized_name
        
        # If repository already exists, pull updates instead of skipping
        if repo_path.exists():
            self.logger.info(f"Repository already exists, pulling updates: {repo_path}")
            if self.cleanup_config.enabled:
                self.logger.info(f"Cleanup is ENABLED for this repository")
                self.logger.info(f"  - Mode: {'DRY-RUN' if self.cleanup_config.dry_run else 'ACTUAL'}")
                self.logger.info(f"  - Auto-commit: {self.cleanup_config.auto_commit}")
            else:
                self.logger.info(f"Cleanup is DISABLED for this repository")
            try:
                repo = Repo(repo_path)
                if self.pull_all_branches(repo, project):
                    self.stats['repositories_updated'] += 1
                    return True
                else:
                    self.stats['errors'] += 1
                    return False
            except Exception as e:
                self.logger.error(f"Error updating repository {project.name}: {e}")
                self.stats['errors'] += 1
                return False
        
        try:
            # Create parent directory if it doesn't exist
            local_path.mkdir(parents=True, exist_ok=True)
            
            # Clone the repository (prefer HTTPS over SSH)
            if hasattr(project, 'http_url_to_repo'):
                clone_url = project.http_url_to_repo
                self.logger.info(f"Cloning {project.name} using HTTPS")
            elif hasattr(project, 'ssh_url_to_repo'):
                clone_url = project.ssh_url_to_repo
                self.logger.info(f"Cloning {project.name} using SSH")
            else:
                self.logger.error(f"No clone URL available for {project.name}")
                self.stats['errors'] += 1
                return False
            
            self.logger.info(f"Clone URL: {clone_url}")
            
            # Clone the repository
            repo = Repo.clone_from(clone_url, repo_path)
            self.logger.info(f"Successfully cloned: {repo_path}")
            
            # Fetch all remote branches and create local tracking branches
            if self._fetch_all_remote_branches(repo, project):
                self.logger.info(f"All branches available locally for {project.name}")
            else:
                self.logger.warning(f"Some branches could not be fetched for {project.name}")
            
            self.stats['repositories_cloned'] += 1
            if self.progress_manager:
                self.progress_manager.update()
            return True
            
        except GitCommandError as e:
            error_msg = f"Git error: {str(e)[:100]}"
            self.logger.error(f"Git error cloning {project.name}: {e}")
            if self.progress_manager:
                self.progress_manager.record_error(project.name, "", error_msg)
            self.stats['errors'] += 1
            if self.progress_manager:
                self.progress_manager.update()
            return False
        except Exception as e:
            error_msg = f"{str(e)[:100]}"
            self.logger.error(f"Error cloning {project.name}: {e}")
            if self.progress_manager:
                self.progress_manager.record_error(project.name, "", error_msg)
            self.stats['errors'] += 1
            if self.progress_manager:
                self.progress_manager.update()
            return False
    
    def process_group_items(self, group: Any, local_path: Path) -> List[Any]:
        """
        Process all items (projects and subgroups) in a group.
        
        Args:
            group: GitLab group object
            local_path: Local directory path for this group
            
        Returns:
            List of subgroups to process recursively
        """
        subgroups_to_process = []
        
        try:
            # Get all projects in this group
            projects = group.projects.list(all=True, include_subgroups=False)
            self.logger.info(f"Found {len(projects)} projects in group '{group.name}'")
            
            # Clone each project
            for project in projects:
                self.clone_repository(project, local_path)
                # Small delay to be respectful to the server
                time.sleep(0.1)
            
            # Get all subgroups
            subgroups = group.subgroups.list(all=True)
            self.logger.info(f"Found {len(subgroups)} subgroups in group '{group.name}'")
            
            # Process each subgroup
            for subgroup in subgroups:
                # Sanitize subgroup name for filesystem compatibility
                sanitized_subgroup_name = self._sanitize_name(subgroup.name)
                subgroup_path = local_path / sanitized_subgroup_name
                subgroup_path.mkdir(parents=True, exist_ok=True)
                
                # Get full subgroup object for recursive processing
                full_subgroup = self.gl.groups.get(subgroup.id)
                subgroups_to_process.append((full_subgroup, subgroup_path))
                
        except Exception as e:
            self.logger.error(f"Error processing group '{group.name}': {e}")
            self.stats['errors'] += 1
        
        return subgroups_to_process
    
    def clone_group_recursively(self, group_identifier: str) -> bool:
        """
        Recursively clone all repositories from a GitLab group and its subgroups.
        
        Args:
            group_identifier: Group ID or path to start cloning from
            
        Returns:
            True if successful, False otherwise
        """
        # Test authentication first
        if not self.authenticate():
            return False
        
        # Get the starting group
        root_group = self.get_group(group_identifier)
        if not root_group:
            return False
        
        # Create destination directory
        self.destination_path.mkdir(parents=True, exist_ok=True)
        
        # Count total repositories first
        total_repos = self._count_total_repositories(root_group)
        
        # Initialize progress manager
        self.progress_manager = ProgressManager(total_repos, quiet=self.quiet)
        
        self.logger.info(f"Starting recursive clone of group '{root_group.name}' to {self.destination_path}")
        print(f"Cloning group '{root_group.name}' ({total_repos} repositories)...\n")
        
        # Initialize queue for breadth-first processing
        processing_queue = deque([(root_group, self.destination_path)])
        
        # Process groups in breadth-first manner
        while processing_queue:
            current_group, current_path = processing_queue.popleft()
            
            self.logger.info(f"Processing group: {current_group.name} (ID: {current_group.id})")
            self.stats['groups_processed'] += 1
            
            # Process all items in current group and get subgroups
            subgroups = self.process_group_items(current_group, current_path)
            
            # Add subgroups to processing queue
            processing_queue.extend(subgroups)
        
        # Close progress bar and print summary
        if self.progress_manager:
            self.progress_manager.close()
            self.progress_manager.print_summary()
        
        return True
    
    def _print_statistics(self):
        """Print cloning statistics."""
        self.logger.info("=" * 50)
        self.logger.info("CLONING STATISTICS")
        self.logger.info("=" * 50)
        self.logger.info(f"Groups processed: {self.stats['groups_processed']}")
        self.logger.info(f"Repositories cloned: {self.stats['repositories_cloned']}")
        self.logger.info(f"Repositories updated: {self.stats['repositories_updated']}")
        self.logger.info(f"Errors encountered: {self.stats['errors']}")
        self.logger.info("=" * 50)


@click.command()
@click.option('--gitlab-url', required=True, help='GitLab base URL (e.g., https://gitlab.company.com)')
@click.option('--token', required=True, help='GitLab API access token')
@click.option('--group', required=True, help='Group ID or group path to clone from')
@click.option('--destination', required=True, help='Local destination path for cloned repositories')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def main(gitlab_url: str, token: str, group: str, destination: str, verbose: bool):
    """
    Recursively clone all Git repositories from a GitLab group hierarchy.
    
    This tool will scan the specified GitLab group and all its subgroups,
    cloning repositories while maintaining the directory structure.
    """
    if verbose:
        logging.getLogger('gitlab_cloner').setLevel(logging.DEBUG)
    
    cloner = GitLabCloner(gitlab_url, token, destination)
    
    try:
        success = cloner.clone_group_recursively(group)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        cloner.logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        cloner.logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
