#!/usr/bin/env python3
"""
Example usage of GitLab Publisher.

This script demonstrates how to use the GitLab publisher programmatically.
"""

import os
import sys
from pathlib import Path

# Add current directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gitlab_publisher import GitLabPublisher
from config import Config


def example_basic_usage():
    """Example of basic GitLab publisher usage."""
    print("=== Basic Usage Example ===")
    
    # Configuration
    gitlab_url = "https://gitlab.example.com"
    access_token = "your-access-token-here"
    target_group_id = 123  # The target parent group ID in GitLab
    source_path = "./my-repos"  # Local directory containing repositories
    
    # Create publisher instance
    publisher = GitLabPublisher(gitlab_url, access_token, source_path)
    
    # Start publishing process
    # - Scans source_path for Git repositories
    # - Creates groups/subgroups matching directory structure
    # - Creates projects for each repository
    # - Pushes all branches to the remote
    success = publisher.scan_and_publish(target_group_id)
    
    if success:
        print("Publishing completed successfully!")
    else:
        print("Publishing failed!")
    
    return success


def example_publish_single_repo():
    """Example of publishing a single repository."""
    print("=== Single Repository Example ===")
    
    # Configuration
    gitlab_url = "https://gitlab.example.com"
    access_token = "your-access-token-here"
    target_group_id = 123
    
    # Specific repository to publish
    repo_path = Path("./my-repos/backend/api-service")
    source_base = Path("./my-repos")
    relative_path = repo_path.relative_to(source_base)
    
    # Create publisher instance
    publisher = GitLabPublisher(gitlab_url, access_token, str(source_base))
    
    # Authenticate first
    if not publisher.authenticate():
        print("Authentication failed!")
        return False
    
    # Publish single repository
    # This will:
    # 1. Create/get group "backend" under target group
    # 2. Create/get project "api-service" in the backend group
    # 3. Push all branches
    success = publisher.publish_repository(repo_path, relative_path, target_group_id)
    
    if success:
        print(f"Successfully published: {relative_path}")
    else:
        print(f"Failed to publish: {relative_path}")
    
    return success


def example_with_config():
    """Example using configuration file."""
    print("=== Configuration File Example ===")
    
    # Load configuration
    config = Config()
    
    # Set default values if not already configured
    if not config.get("target_gitlab_url"):
        config.set("target_gitlab_url", "https://gitlab-target.example.com")
        config.set("target_access_token", "your-target-token-here")
        config.set("target_group_id", 456)
        config.save_config()
        print("Configuration saved to file")
    
    # Use configuration values
    gitlab_url = config.get("target_gitlab_url")
    access_token = config.get("target_access_token")
    target_group_id = config.get("target_group_id")
    source_path = "./cloned-repos"
    
    print(f"Target GitLab URL: {gitlab_url}")
    print(f"Target Group ID: {target_group_id}")
    print(f"Source Path: {source_path}")
    
    # Validate configuration
    if not config.validate_gitlab_url(gitlab_url):
        print("Error: Invalid GitLab URL")
        return False
    
    if not config.validate_access_token(access_token):
        print("Error: Invalid access token")
        return False
    
    print("Configuration validated successfully")
    return True


def example_clone_and_publish():
    """Example of cloning from one GitLab and publishing to another."""
    print("=== Clone and Publish Pipeline Example ===")
    
    from gitlab_cloner import GitLabCloner
    
    # Source GitLab (where we clone from)
    source_gitlab_url = "https://gitlab-source.example.com"
    source_token = "source-token"
    source_group = "123"
    clone_destination = "./temp-repos"
    
    # Target GitLab (where we publish to)
    target_gitlab_url = "https://gitlab-target.example.com"
    target_token = "target-token"
    target_group_id = 456
    
    # Step 1: Clone from source
    print("\n--- Step 1: Cloning from source GitLab ---")
    cloner = GitLabCloner(source_gitlab_url, source_token, clone_destination)
    if not cloner.clone_group_recursively(source_group):
        print("Failed to clone repositories")
        return False
    
    print("\n--- Step 2: Publishing to target GitLab ---")
    # Step 2: Publish to target
    publisher = GitLabPublisher(target_gitlab_url, target_token, clone_destination)
    if not publisher.scan_and_publish(target_group_id):
        print("Failed to publish repositories")
        return False
    
    print("\n✓ Successfully migrated repositories!")
    return True


def example_directory_structure():
    """Example showing how directory structure maps to groups."""
    print("=== Directory Structure Mapping Example ===")
    
    print("""
Local directory structure:
    source/
    ├── repo1/              -> Creates project 'repo1' in target group
    ├── backend/            -> Creates subgroup 'backend'
    │   ├── api-service/    -> Creates project 'api-service' in 'backend' group
    │   └── worker/         -> Creates project 'worker' in 'backend' group
    └── frontend/           -> Creates subgroup 'frontend'
        └── web-app/        -> Creates project 'web-app' in 'frontend' group

GitLab structure (target group ID: 123):
    Target Group (123)
    ├── repo1 (project)
    ├── backend/ (subgroup)
    │   ├── api-service (project)
    │   └── worker (project)
    └── frontend/ (subgroup)
        └── web-app (project)
    """)
    
    return True


def example_statistics_monitoring():
    """Example showing how to monitor publishing statistics."""
    print("=== Statistics Monitoring Example ===")
    
    gitlab_url = "https://gitlab.example.com"
    access_token = "your-access-token-here"
    target_group_id = 123
    source_path = "./repos-to-publish"
    
    publisher = GitLabPublisher(gitlab_url, access_token, source_path)
    
    # Monitor statistics during publishing
    print("Starting publish operation...")
    success = publisher.scan_and_publish(target_group_id)
    
    # Access final statistics
    stats = publisher.stats
    print("\nFinal Statistics:")
    print(f"Groups created: {stats['groups_created']}")
    print(f"Repositories created: {stats['repositories_created']}")
    print(f"Repositories updated: {stats['repositories_updated']}")
    print(f"Branches pushed: {stats['branches_pushed']}")
    print(f"Errors encountered: {stats['errors']}")
    
    return success


def main():
    """Main function to run examples."""
    print("GitLab Publisher - Example Usage")
    print("=" * 40)
    
    examples = [
        ("Basic Usage", example_basic_usage),
        ("Single Repository", example_publish_single_repo),
        ("Configuration File", example_with_config),
        ("Clone and Publish Pipeline", example_clone_and_publish),
        ("Directory Structure Mapping", example_directory_structure),
        ("Statistics Monitoring", example_statistics_monitoring),
    ]
    
    for name, example_func in examples:
        print(f"\n{name}:")
        print("-" * len(name))
        try:
            example_func()
        except Exception as e:
            print(f"Example failed: {e}")
        print()


if __name__ == '__main__':
    main()
