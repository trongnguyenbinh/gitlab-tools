#!/usr/bin/env python3
"""
Command-line interface for GitLab Cloner.
"""

import sys
import logging
import click
from .cloner import GitLabCloner
from .cleanup import CleanupConfig


@click.command()
@click.option('--gitlab-url', required=True, help='GitLab base URL (e.g., https://gitlab.company.com)')
@click.option('--token', required=True, help='GitLab API access token')
@click.option('--group', required=True, help='Group ID or group path to clone from')
@click.option('--destination', required=True, help='Local destination path for cloned repositories')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--quiet', '-q', is_flag=True, help='Quiet mode - show only progress bar and errors')
@click.option('--cleanup', is_flag=True, help='Enable cleanup of unnecessary files after pulling')
@click.option('--cleanup-dry-run', is_flag=True, help='Preview cleanup without actually deleting files')
@click.option('--cleanup-auto-commit', is_flag=True, help='Automatically commit and push cleanup changes')
@click.option('--cleanup-history', is_flag=True, help='Rewrite git history to remove files from all commits (requires git-filter-repo)')
@click.option('--cleanup-patterns', multiple=True, help='Additional file patterns to remove (can be used multiple times)')
@click.option('--cleanup-keep-patterns', multiple=True, help='Whitelist patterns to exclude from removal (can be used multiple times)')
def main(gitlab_url: str, token: str, group: str, destination: str, verbose: bool, quiet: bool,
         cleanup: bool, cleanup_dry_run: bool, cleanup_auto_commit: bool, cleanup_history: bool,
         cleanup_patterns: tuple, cleanup_keep_patterns: tuple):
    """
    Recursively clone all Git repositories from a GitLab group hierarchy.

    This tool will scan the specified GitLab group and all its subgroups,
    cloning repositories while maintaining the directory structure.

    Cleanup options:
    - Use --cleanup to enable cleanup of unnecessary files
    - Use --cleanup-dry-run to preview what would be removed
    - Use --cleanup-auto-commit to automatically commit and push changes
    - Use --cleanup-history to rewrite git history and remove files from all commits
    - Use --cleanup-patterns to add custom patterns to remove
    - Use --cleanup-keep-patterns to whitelist patterns to keep
    """
    if verbose:
        logging.getLogger('gitlab_cloner').setLevel(logging.DEBUG)

    # Setup cleanup configuration if enabled
    cleanup_config = None
    if cleanup:
        cleanup_config = CleanupConfig(
            enabled=True,
            dry_run=cleanup_dry_run,
            auto_commit=cleanup_auto_commit,
            cleanup_history=cleanup_history,
        )

        # Add custom patterns if provided
        if cleanup_patterns:
            cleanup_config.patterns_to_remove.extend(cleanup_patterns)

        # Set whitelist patterns if provided
        if cleanup_keep_patterns:
            cleanup_config.patterns_to_keep = list(cleanup_keep_patterns)

    cloner = GitLabCloner(gitlab_url, token, destination, quiet=quiet, cleanup_config=cleanup_config)

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
