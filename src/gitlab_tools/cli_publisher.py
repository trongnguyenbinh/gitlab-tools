#!/usr/bin/env python3
"""
Command-line interface for GitLab Publisher.
"""

import sys
import logging
import click
from .publisher import GitLabPublisher


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
