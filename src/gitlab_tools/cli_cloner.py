#!/usr/bin/env python3
"""
Command-line interface for GitLab Cloner.
"""

import sys
import logging
import click
from .cloner import GitLabCloner


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
