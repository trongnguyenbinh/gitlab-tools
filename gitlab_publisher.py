#!/usr/bin/env python3
"""
GitLab Repository Publisher

A tool to publish local Git repositories to a GitLab self-hosted server,
creating groups/subgroups and repositories as needed, and pushing all branches.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import time

import gitlab
from git import Repo, GitCommandError
import click


class GitLabPublisher:
    """Main class for publishing local repositories to GitLab."""
    
    def __init__(self, gitlab_url: str, access_token: str, source_path: str, use_ssh: bool = False):
        """
        Initialize the GitLab publisher.
        
        Args:
            gitlab_url: Base URL of the GitLab instance
            access_token: GitLab API access token
            source_path: Local path containing repositories to publish
            use_ssh: Use SSH URLs instead of HTTPS (requires SSH keys configured)
        """
        self.gitlab_url = gitlab_url.rstrip('/')
        self.access_token = access_token
        self.source_path = Path(source_path).resolve()
        self.use_ssh = use_ssh
        
        # Initialize GitLab connection
        self.gl = gitlab.Gitlab(self.gitlab_url, private_token=self.access_token)
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Statistics
        self.stats = {
            'groups_created': 0,
            'repositories_created': 0,
            'repositories_updated': 0,
            'branches_pushed': 0,
            'errors': 0
        }
        
        # Cache for created/existing groups
        self.group_cache: Dict[str, Any] = {}
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('gitlab_publisher')
        logger.setLevel(logging.INFO)
        
        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        
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
    
    def get_or_create_group(self, parent_id: int, group_name: str, group_path: str) -> Optional[Any]:
        """
        Get existing group or create a new one.
        
        Args:
            parent_id: Parent group ID (None for root level)
            group_name: Display name for the group
            group_path: URL path for the group
            
        Returns:
            GitLab group object or None if failed
        """
        cache_key = f"{parent_id}:{group_path}"
        
        # Check cache first
        if cache_key in self.group_cache:
            return self.group_cache[cache_key]
        
        try:
            # Try to find existing group
            if parent_id:
                parent_group = self.gl.groups.get(parent_id)
                # Search in subgroups
                for subgroup in parent_group.subgroups.list(all=True):
                    if subgroup.path == group_path:
                        full_subgroup = self.gl.groups.get(subgroup.id)
                        self.logger.info(f"Found existing group: {full_subgroup.full_path}")
                        self.group_cache[cache_key] = full_subgroup
                        return full_subgroup
            else:
                # Search in root level groups
                groups = self.gl.groups.list(search=group_path, all=True)
                for group in groups:
                    if group.path == group_path and not hasattr(group, 'parent_id'):
                        full_group = self.gl.groups.get(group.id)
                        self.logger.info(f"Found existing group: {full_group.full_path}")
                        self.group_cache[cache_key] = full_group
                        return full_group
            
            # Group doesn't exist, create it
            self.logger.info(f"Creating new group: {group_path} (parent: {parent_id})")
            
            group_data = {
                'name': group_name,
                'path': group_path,
                'visibility': 'private'
            }
            
            if parent_id:
                group_data['parent_id'] = parent_id
            
            new_group = self.gl.groups.create(group_data)
            self.stats['groups_created'] += 1
            self.logger.info(f"Created group: {new_group.full_path} (ID: {new_group.id})")
            
            self.group_cache[cache_key] = new_group
            return new_group
            
        except Exception as e:
            self.logger.error(f"Error getting/creating group '{group_path}': {e}")
            return None
    
    def get_or_create_project(self, group_id: int, project_name: str, project_path: str) -> Optional[Any]:
        """
        Get existing project or create a new one in the specified group.
        
        Args:
            group_id: Parent group ID
            project_name: Display name for the project
            project_path: URL path for the project
            
        Returns:
            GitLab project object or None if failed
        """
        try:
            # Try to find existing project in the group
            group = self.gl.groups.get(group_id)
            projects = group.projects.list(search=project_path, all=True)
            
            for project in projects:
                if project.path == project_path:
                    full_project = self.gl.projects.get(project.id)
                    self.logger.info(f"Found existing project: {full_project.path_with_namespace}")
                    return full_project
            
            # Project doesn't exist, create it
            self.logger.info(f"Creating new project: {project_path} in group {group_id}")
            
            project_data = {
                'name': project_name,
                'path': project_path,
                'namespace_id': group_id,
                'visibility': 'private',
                'initialize_with_readme': False
            }
            
            new_project = self.gl.projects.create(project_data)
            self.stats['repositories_created'] += 1
            self.logger.info(f"Created project: {new_project.path_with_namespace} (ID: {new_project.id})")
            
            return new_project
            
        except Exception as e:
            self.logger.error(f"Error getting/creating project '{project_path}': {e}")
            return None
    
    def push_all_branches(self, local_repo: Repo, remote_url: str, project_name: str) -> bool:
        """
        Push all local branches to the remote repository.
        
        Args:
            local_repo: GitPython Repo object
            remote_url: Remote repository URL
            project_name: Name of the project (for logging)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add or update the remote
            remote_name = 'gitlab_publisher'
            
            if remote_name in [r.name for r in local_repo.remotes]:
                # Update existing remote URL
                local_repo.delete_remote(remote_name)
            
            remote = local_repo.create_remote(remote_name, remote_url)
            self.logger.info(f"Added remote '{remote_name}' for {project_name}")
            
            # Get all local branches
            branches = [head.name for head in local_repo.heads]
            self.logger.info(f"Found {len(branches)} branches to push")
            
            if not branches:
                self.logger.warning(f"No branches found in {project_name}")
                return True
            
            # Push all branches
            for branch in branches:
                try:
                    self.logger.info(f"Pushing branch: {branch}")
                    push_info = remote.push(f"{branch}:{branch}", force=False)
                    
                    # Check push result
                    if push_info and push_info[0].flags & push_info[0].ERROR:
                        self.logger.error(f"Failed to push branch {branch}: {push_info[0].summary}")
                        self.stats['errors'] += 1
                    else:
                        self.logger.info(f"Successfully pushed branch: {branch}")
                        self.stats['branches_pushed'] += 1
                        
                except GitCommandError as e:
                    self.logger.error(f"Git error pushing branch {branch}: {e}")
                    self.stats['errors'] += 1
                    continue
            
            # Clean up remote
            local_repo.delete_remote(remote_name)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error pushing branches for {project_name}: {e}")
            return False
    
    def publish_repository(self, repo_path: Path, relative_path: Path, target_group_id: int) -> bool:
        """
        Publish a single repository to GitLab.
        
        Args:
            repo_path: Full path to the local repository
            relative_path: Relative path from source_path (for creating group structure)
            target_group_id: Target parent group ID in GitLab
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Open the local repository
            local_repo = Repo(repo_path)
            
            if local_repo.bare:
                self.logger.warning(f"Skipping bare repository: {repo_path}")
                return False
            
            # Build group hierarchy from relative path
            path_parts = relative_path.parent.parts if relative_path.parent != Path('.') else []
            current_parent_id = target_group_id
            
            # Create nested groups as needed
            for group_name in path_parts:
                # Use group name as both name and path (sanitized for URL)
                group_path = group_name.lower().replace(' ', '-')
                group = self.get_or_create_group(current_parent_id, group_name, group_path)
                
                if not group:
                    self.logger.error(f"Failed to create/get group: {group_name}")
                    self.stats['errors'] += 1
                    return False
                
                current_parent_id = group.id
            
            # Create or get the project
            project_name = repo_path.name
            project_path = project_name.lower().replace(' ', '-')
            
            project = self.get_or_create_project(current_parent_id, project_name, project_path)
            
            if not project:
                self.logger.error(f"Failed to create/get project: {project_name}")
                self.stats['errors'] += 1
                return False
            
            # Get remote URL
            if self.use_ssh:
                # Use SSH (requires SSH keys to be configured)
                if hasattr(project, 'ssh_url_to_repo'):
                    remote_url = project.ssh_url_to_repo
                    self.logger.info(f"Using SSH URL: {remote_url}")
                else:
                    self.logger.error(f"No SSH URL available for project: {project_name}")
                    self.stats['errors'] += 1
                    return False
            else:
                # Use HTTPS with token authentication (default)
                if hasattr(project, 'http_url_to_repo'):
                    http_url = project.http_url_to_repo
                    # Embed token in HTTPS URL for authentication
                    # Format: https://oauth2:TOKEN@gitlab.com/group/project.git
                    remote_url = http_url.replace('https://', f'https://oauth2:{self.access_token}@')
                    # Log URL without token
                    safe_url = http_url
                    self.logger.info(f"Using HTTPS URL with token authentication: {safe_url}")
                else:
                    self.logger.error(f"No HTTP URL available for project: {project_name}")
                    self.stats['errors'] += 1
                    return False
            
            # Push all branches
            if self.push_all_branches(local_repo, remote_url, project_name):
                self.stats['repositories_updated'] += 1
                return True
            else:
                self.stats['errors'] += 1
                return False
                
        except Exception as e:
            self.logger.error(f"Error publishing repository {repo_path}: {e}")
            self.stats['errors'] += 1
            return False
    
    def scan_and_publish(self, target_group_id: int) -> bool:
        """
        Scan source directory for Git repositories and publish them to GitLab.
        
        Args:
            target_group_id: Target parent group ID in GitLab
            
        Returns:
            True if successful, False otherwise
        """
        # Test authentication first
        if not self.authenticate():
            return False
        
        # Verify target group exists
        try:
            target_group = self.gl.groups.get(target_group_id)
            self.logger.info(f"Target group: {target_group.full_path} (ID: {target_group.id})")
        except Exception as e:
            self.logger.error(f"Failed to get target group {target_group_id}: {e}")
            return False
        
        if not self.source_path.exists():
            self.logger.error(f"Source path does not exist: {self.source_path}")
            return False
        
        self.logger.info(f"Scanning for repositories in: {self.source_path}")
        
        # Find all git repositories
        repositories = []
        for root, dirs, files in os.walk(self.source_path):
            # Check if current directory is a git repository
            if '.git' in dirs:
                repo_path = Path(root)
                relative_path = repo_path.relative_to(self.source_path)
                repositories.append((repo_path, relative_path))
                # Don't descend into git repositories
                dirs[:] = []
        
        self.logger.info(f"Found {len(repositories)} repositories to publish")
        
        # Publish each repository
        for repo_path, relative_path in repositories:
            self.logger.info(f"Processing: {relative_path}")
            self.publish_repository(repo_path, relative_path, target_group_id)
            # Small delay to be respectful to the server
            time.sleep(0.1)
        
        # Print final statistics
        self._print_statistics()
        return True
    
    def _print_statistics(self):
        """Print publishing statistics."""
        self.logger.info("=" * 50)
        self.logger.info("PUBLISHING STATISTICS")
        self.logger.info("=" * 50)
        self.logger.info(f"Groups created: {self.stats['groups_created']}")
        self.logger.info(f"Repositories created: {self.stats['repositories_created']}")
        self.logger.info(f"Repositories updated: {self.stats['repositories_updated']}")
        self.logger.info(f"Branches pushed: {self.stats['branches_pushed']}")
        self.logger.info(f"Errors encountered: {self.stats['errors']}")
        self.logger.info("=" * 50)


@click.command()
@click.option('--gitlab-url', required=True, help='GitLab base URL (e.g., https://gitlab.company.com)')
@click.option('--token', required=True, help='GitLab API access token')
@click.option('--group-id', required=True, type=int, help='Target group ID to publish repositories to')
@click.option('--source', required=True, help='Local source path containing repositories')
@click.option('--use-ssh', is_flag=True, help='Use SSH URLs instead of HTTPS (requires SSH keys)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def main(gitlab_url: str, token: str, group_id: int, source: str, use_ssh: bool, verbose: bool):
    """
    Publish local Git repositories to a GitLab group hierarchy.
    
    This tool will scan the specified local directory for Git repositories,
    create necessary groups/subgroups on GitLab, create projects, and push all branches.
    
    By default, uses HTTPS with token authentication. Use --use-ssh if you have SSH keys configured.
    """
    if verbose:
        logging.getLogger('gitlab_publisher').setLevel(logging.DEBUG)
    
    publisher = GitLabPublisher(gitlab_url, token, source, use_ssh=use_ssh)
    
    try:
        success = publisher.scan_and_publish(group_id)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        publisher.logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        publisher.logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
