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


class GitLabCloner:
    """Main class for cloning GitLab repositories recursively."""
    
    def __init__(self, gitlab_url: str, access_token: str, destination_path: str,
                 quiet: bool = False, use_short_paths: bool = False,
                 max_path_length: int = 240):
        """
        Initialize the GitLab cloner.

        Args:
            gitlab_url: Base URL of the GitLab instance
            access_token: GitLab API access token
            destination_path: Local path where repositories will be cloned
            quiet: If True, suppress detailed logging and show progress bar only
            use_short_paths: If True, use shortened directory names to avoid Windows path length limits
            max_path_length: Maximum path length before warning (default 240 for Windows compatibility)
        """
        self.gitlab_url = gitlab_url.rstrip('/')
        self.access_token = access_token
        self.destination_path = Path(destination_path).resolve()
        self.quiet = quiet
        self.use_short_paths = use_short_paths
        self.max_path_length = max_path_length

        # Initialize GitLab connection
        self.gl = gitlab.Gitlab(self.gitlab_url, private_token=self.access_token)

        # Setup logging
        self.logger = self._setup_logging()

        # Progress manager (set later in clone_group_recursively)
        self.progress_manager: Optional[ProgressManager] = None

        # Statistics
        self.stats = {
            'repositories_cloned': 0,
            'repositories_updated': 0,
            'groups_processed': 0,
            'errors': 0,
            'path_warnings': 0
        }

        # Configure git for long paths on Windows
        self._configure_git_for_long_paths()
    
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

    def _configure_git_for_long_paths(self):
        """Configure git to support long paths on Windows."""
        try:
            import platform
            if platform.system() == 'Windows':
                # Enable long path support in git
                from git import Git
                g = Git()
                try:
                    # Set core.longpaths to true for this git instance
                    g.config('--global', 'core.longpaths', 'true')
                    self.logger.info("Enabled git long path support (core.longpaths=true)")
                except Exception as e:
                    self.logger.warning(
                        f"Could not enable git long path support: {e}. "
                        "You may encounter 'Filename too long' errors. "
                        "Run 'git config --global core.longpaths true' manually."
                    )
        except Exception as e:
            self.logger.debug(f"Error configuring git for long paths: {e}")
    
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
            # Fetch all branches from remote
            self.logger.info(f"Fetching all branches for {project.name}")
            repo.remotes.origin.fetch(prune=True)
            
            # Get all remote branches
            remote_branches = [ref.name for ref in repo.remotes.origin.refs if not ref.name.endswith('/HEAD')]
            self.logger.info(f"Found {len(remote_branches)} remote branches")
            
            # Store current branch
            current_branch = repo.active_branch.name if not repo.head.is_detached else None
            
            # Pull updates for each branch
            for remote_ref in remote_branches:
                try:
                    # Extract branch name (remove 'origin/' prefix)
                    branch_name = remote_ref.replace('origin/', '')
                    
                    # Check if local branch exists
                    if branch_name in [b.name for b in repo.heads]:
                        # Checkout and pull existing branch
                        self.logger.info(f"Pulling updates for branch: {branch_name}")
                        repo.git.checkout(branch_name)
                        repo.remotes.origin.pull(branch_name)
                    else:
                        # Create new local branch tracking remote
                        self.logger.info(f"Creating local branch: {branch_name}")
                        repo.git.checkout('-b', branch_name, remote_ref)
                        
                except GitCommandError as e:
                    self.logger.warning(f"Failed to pull branch {branch_name}: {e}")
                    continue
            
            # Return to original branch if possible
            if current_branch:
                try:
                    repo.git.checkout(current_branch)
                    self.logger.info(f"Returned to original branch: {current_branch}")
                except GitCommandError:
                    self.logger.warning(f"Could not return to original branch: {current_branch}")
            
            self.logger.info(f"Successfully updated all branches for: {project.name}")
            return True
            
        except GitCommandError as e:
            self.logger.error(f"Git error pulling branches for {project.name}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error pulling branches for {project.name}: {e}")
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
            # Fetch all branches from remote
            self.logger.info(f"Fetching all remote branches for {project.name}")
            repo.remotes.origin.fetch(prune=True)
            
            # Get all remote branches
            remote_branches = [ref.name for ref in repo.remotes.origin.refs if not ref.name.endswith('/HEAD')]
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

        # If using short paths mode, truncate long names
        if self.use_short_paths and len(sanitized) > 50:
            # Keep first 45 chars and add hash of full name for uniqueness
            import hashlib
            name_hash = hashlib.md5(sanitized.encode()).hexdigest()[:5]
            sanitized = f"{sanitized[:45]}_{name_hash}"
            self.logger.debug(f"Shortened name: {name} -> {sanitized}")

        return sanitized if sanitized else 'unnamed'

    def _check_path_length(self, path: Path, project_name: str) -> bool:
        """
        Check if path length exceeds Windows limits and log warnings.

        Args:
            path: Path to check
            project_name: Name of the project (for logging)

        Returns:
            True if path is acceptable, False if it exceeds limits
        """
        path_str = str(path)
        path_length = len(path_str)

        # Windows MAX_PATH is 260, but we use a lower threshold for safety
        # to account for files within the repository
        if path_length > self.max_path_length:
            self.logger.warning(
                f"Path length ({path_length}) exceeds recommended limit ({self.max_path_length}) "
                f"for project '{project_name}': {path_str}"
            )
            self.logger.warning(
                "This may cause 'Filename too long' errors on Windows. "
                "Consider using --use-short-paths option or a shorter destination path."
            )
            self.stats['path_warnings'] += 1
            return False
        elif path_length > 200:
            # Soft warning for paths approaching the limit
            self.logger.info(
                f"Path length ({path_length}) is approaching Windows limits "
                f"for project '{project_name}'"
            )

        return True
    
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

        # Check path length before proceeding
        self._check_path_length(repo_path, project.name)

        # If repository already exists, pull updates instead of skipping
        if repo_path.exists():
            self.logger.info(f"Repository already exists, pulling updates: {repo_path}")
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
            # Long path support is already configured globally in _configure_git_for_long_paths
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
            error_str = str(e)

            # Provide specific guidance for path length errors
            if 'Filename too long' in error_str or 'unable to create file' in error_str:
                self.logger.error(
                    f"Path length error cloning {project.name}. "
                    f"Try using --use-short-paths option or a shorter destination path. "
                    f"Path: {repo_path}"
                )
                self.logger.error(
                    "Windows path length solutions:\n"
                    "  1. Use --use-short-paths flag\n"
                    "  2. Use a shorter destination path (e.g., C:\\repos)\n"
                    "  3. Enable Windows long path support: "
                    "https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation"
                )
            else:
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
        if self.stats['path_warnings'] > 0:
            self.logger.warning(f"Path length warnings: {self.stats['path_warnings']}")
            self.logger.warning(
                "Consider using --use-short-paths option or a shorter destination path "
                "to avoid Windows path length issues."
            )
        self.logger.info("=" * 50)


@click.command()
@click.option('--gitlab-url', required=True, help='GitLab base URL (e.g., https://gitlab.company.com)')
@click.option('--token', required=True, help='GitLab API access token')
@click.option('--group', required=True, help='Group ID or group path to clone from')
@click.option('--destination', required=True, help='Local destination path for cloned repositories')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--use-short-paths', is_flag=True,
              help='Use shortened directory names to avoid Windows path length limits (260 chars)')
@click.option('--max-path-length', type=int, default=240,
              help='Maximum path length before warning (default: 240 for Windows compatibility)')
def main(gitlab_url: str, token: str, group: str, destination: str, verbose: bool,
         use_short_paths: bool, max_path_length: int):
    """
    Recursively clone all Git repositories from a GitLab group hierarchy.

    This tool will scan the specified GitLab group and all its subgroups,
    cloning repositories while maintaining the directory structure.

    \b
    Windows Long Path Support:
    - Use --use-short-paths to automatically shorten directory names
    - Use a short destination path (e.g., C:\\repos instead of C:\\Users\\...\\Documents\\...)
    - Enable Windows long path support in registry (see README for instructions)
    - Git will be automatically configured with core.longpaths=true
    """
    if verbose:
        logging.getLogger('gitlab_cloner').setLevel(logging.DEBUG)

    cloner = GitLabCloner(
        gitlab_url,
        token,
        destination,
        use_short_paths=use_short_paths,
        max_path_length=max_path_length
    )

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
