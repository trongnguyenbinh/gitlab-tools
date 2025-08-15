#!/usr/bin/env python3
"""
Example usage of GitLab Cloner.

This script demonstrates how to use the GitLab cloner programmatically.
"""

import os
import sys
from pathlib import Path

# Add current directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gitlab_cloner import GitLabCloner
from config import Config


def example_basic_usage():
    """Example of basic GitLab cloner usage."""
    print("=== Basic Usage Example ===")
    
    # Configuration
    gitlab_url = "https://gitlab.example.com"
    access_token = "your-access-token-here"
    group_identifier = "123"  # Can be group ID or path like "organization/team"
    destination_path = "./cloned-repos"
    
    # Create cloner instance
    cloner = GitLabCloner(gitlab_url, access_token, destination_path)
    
    # Start cloning process
    success = cloner.clone_group_recursively(group_identifier)
    
    if success:
        print("Cloning completed successfully!")
    else:
        print("Cloning failed!")
    
    return success


def example_with_config():
    """Example using configuration file."""
    print("=== Configuration File Example ===")
    
    # Load configuration
    config = Config()
    
    # Set default values if not already configured
    if not config.get("gitlab_url"):
        config.set("gitlab_url", "https://gitlab.example.com")
        config.set("access_token", "your-access-token-here")
        config.set("default_destination", "./repos")
        config.save_config()
        print("Configuration saved to file")
    
    # Use configuration values
    gitlab_url = config.get("gitlab_url")
    access_token = config.get("access_token")
    destination = config.get("default_destination", "./repos")
    
    print(f"Using GitLab URL: {gitlab_url}")
    print(f"Destination: {destination}")
    
    # Validate configuration
    if not config.validate_gitlab_url(gitlab_url):
        print("Error: Invalid GitLab URL")
        return False
    
    if not config.validate_access_token(access_token):
        print("Error: Invalid access token")
        return False
    
    if not config.validate_destination_path(destination):
        print("Error: Invalid destination path")
        return False
    
    print("Configuration validated successfully")
    return True


def example_error_handling():
    """Example with comprehensive error handling."""
    print("=== Error Handling Example ===")
    
    try:
        # Configuration
        gitlab_url = "https://gitlab.example.com"
        access_token = "invalid-token"  # Intentionally invalid
        group_identifier = "nonexistent-group"
        destination_path = "./test-clone"
        
        # Create cloner instance
        cloner = GitLabCloner(gitlab_url, access_token, destination_path)
        
        # Test authentication first
        if not cloner.authenticate():
            print("Authentication failed - check your access token")
            return False
        
        # Test group access
        group = cloner.get_group(group_identifier)
        if not group:
            print(f"Group '{group_identifier}' not found or not accessible")
            return False
        
        # Start cloning
        success = cloner.clone_group_recursively(group_identifier)
        return success
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def example_custom_destination_structure():
    """Example showing custom destination structure."""
    print("=== Custom Destination Structure Example ===")
    
    # Configuration
    gitlab_url = "https://gitlab.example.com"
    access_token = "your-access-token-here"
    
    # Different groups to different destinations
    groups_config = [
        {"group": "frontend-team", "destination": "./frontend-repos"},
        {"group": "backend-team", "destination": "./backend-repos"},
        {"group": "devops-team", "destination": "./devops-repos"},
    ]
    
    for group_config in groups_config:
        print(f"Cloning group '{group_config['group']}' to '{group_config['destination']}'")
        
        cloner = GitLabCloner(
            gitlab_url,
            access_token,
            group_config['destination']
        )
        
        success = cloner.clone_group_recursively(group_config['group'])
        
        if success:
            print(f"✓ Successfully cloned {group_config['group']}")
        else:
            print(f"✗ Failed to clone {group_config['group']}")
    
    print("All groups processed")


def example_statistics_monitoring():
    """Example showing how to monitor cloning statistics."""
    print("=== Statistics Monitoring Example ===")
    
    gitlab_url = "https://gitlab.example.com"
    access_token = "your-access-token-here"
    group_identifier = "123"
    destination_path = "./monitored-clone"
    
    cloner = GitLabCloner(gitlab_url, access_token, destination_path)
    
    # Monitor statistics during cloning
    print("Starting clone operation...")
    success = cloner.clone_group_recursively(group_identifier)
    
    # Access final statistics
    stats = cloner.stats
    print("\nFinal Statistics:")
    print(f"Groups processed: {stats['groups_processed']}")
    print(f"Repositories cloned: {stats['repositories_cloned']}")
    print(f"Repositories skipped: {stats['repositories_skipped']}")
    print(f"Errors encountered: {stats['errors']}")
    
    # Calculate success rate
    total_repos = stats['repositories_cloned'] + stats['repositories_skipped']
    if total_repos > 0:
        success_rate = (stats['repositories_cloned'] / total_repos) * 100
        print(f"Success rate: {success_rate:.1f}%")
    
    return success


def main():
    """Main function to run examples."""
    print("GitLab Cloner - Example Usage")
    print("=" * 40)
    
    examples = [
        ("Basic Usage", example_basic_usage),
        ("Configuration File", example_with_config),
        ("Error Handling", example_error_handling),
        ("Custom Destinations", example_custom_destination_structure),
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
