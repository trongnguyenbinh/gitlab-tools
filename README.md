# GitLab Repository Tools

A suite of Python tools for managing GitLab repositories:
- **GitLab Cloner**: Recursively clone all Git repositories from a GitLab group hierarchy
- **GitLab Publisher**: Publish local Git repositories to a GitLab group hierarchy

## Features

- **Recursive Group Scanning**: Automatically discovers and processes all subgroups within a GitLab group hierarchy
- **Maintains Directory Structure**: Creates local directories that mirror the GitLab group structure
- **Breadth-First Processing**: Uses a queue-based approach for efficient traversal
- **Error Handling**: Robust error handling for API calls and git operations
- **Progress Tracking**: Detailed logging and statistics reporting
- **Smart Repository Management**: 
  - Clones new repositories that don't exist locally
  - Automatically updates existing repositories by fetching and pulling all remote branches
  - Creates local tracking branches for any new remote branches
- **Filesystem-Safe Naming**: Automatically sanitizes repository and group names to handle:
  - Trailing/leading whitespace
  - Invalid Windows characters (`<>:"|?*`)
  - Trailing dots and spaces (Windows restrictions)

## Installation

1. Clone or download this project
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### GitLab Cloner - Clone Repositories from GitLab

#### Command Line Interface

```bash
python gitlab_cloner.py --gitlab-url <GITLAB_URL> --token <ACCESS_TOKEN> --group <GROUP_ID_OR_PATH> --destination <LOCAL_PATH>
```

#### Parameters

- `--gitlab-url`: GitLab base URL (e.g., "https://gitlab.company.com")
- `--token`: GitLab API access token for authentication
- `--group`: Group ID (numeric) or group path (string) to start cloning from
- `--destination`: Local destination path where repositories should be cloned
- `--verbose`, `-v`: Enable verbose logging (optional)

#### Examples

```bash
# Clone using group ID
python gitlab_cloner.py --gitlab-url https://gitlab.company.com --token glpat-xxxxxxxxxxxxxxxxxxxx --group 123 --destination ./my-repos

# Clone using group path
python gitlab_cloner.py --gitlab-url https://gitlab.company.com --token glpat-xxxxxxxxxxxxxxxxxxxx --group "my-organization/development" --destination ./dev-repos

# Enable verbose logging
python gitlab_cloner.py --gitlab-url https://gitlab.company.com --token glpat-xxxxxxxxxxxxxxxxxxxx --group 123 --destination ./repos --verbose
```

### GitLab Publisher - Publish Repositories to GitLab

#### Command Line Interface

```bash
python gitlab_publisher.py --gitlab-url <GITLAB_URL> --token <ACCESS_TOKEN> --group-id <TARGET_GROUP_ID> --source <LOCAL_PATH>
```

#### Parameters

- `--gitlab-url`: GitLab base URL (e.g., "https://gitlab.company.com")
- `--token`: GitLab API access token with write permissions
- `--group-id`: Target parent group ID in GitLab where repositories will be created
- `--source`: Local source path containing repositories to publish
- `--use-ssh`: Use SSH URLs instead of HTTPS (requires SSH keys configured)
- `--verbose`, `-v`: Enable verbose logging (optional)

**Note**: By default, the publisher uses HTTPS with token authentication (recommended). Only use `--use-ssh` if you have SSH keys configured with GitLab.

#### Examples

```bash
# Publish all repositories from a directory
python gitlab_publisher.py --gitlab-url https://gitlab.company.com --token glpat-xxxxxxxxxxxxxxxxxxxx --group-id 456 --source ./my-repos

# Migrate repositories from one GitLab to another
# Step 1: Clone from source
python gitlab_cloner.py --gitlab-url https://source.gitlab.com --token SOURCE_TOKEN --group 123 --destination ./temp-repos
# Step 2: Publish to target
python gitlab_publisher.py --gitlab-url https://target.gitlab.com --token TARGET_TOKEN --group-id 456 --source ./temp-repos
```

## How It Works

### Cloner

1. **Authentication**: Connects to the GitLab API using the provided access token
2. **Initial Group Scan**: Scans the specified group to identify repositories and subgroups
3. **Repository Management**:
   - For new repositories: Clones them to the appropriate directory
   - For existing repositories: 
     - Fetches all remote branches
     - Creates local tracking branches for new remote branches
     - Pulls the latest changes for all branches
     - Returns to the original branch after updating
4. **Subgroup Processing**: Creates local directories for subgroups and queues them for processing
5. **Recursive Processing**: Continues processing subgroups until all levels are complete

### Publisher

1. **Authentication**: Connects to the GitLab API using the provided access token
2. **Repository Scanning**: Recursively scans the source directory for Git repositories
3. **Group/Subgroup Creation**: Creates groups and subgroups matching the local directory structure
4. **Project Creation**: Creates projects in GitLab for each repository found
5. **Branch Pushing**: Pushes all local branches to the remote GitLab repository using HTTPS with embedded token authentication (default) or SSH (if `--use-ssh` is specified)

## Directory Structure

The tool creates a directory structure that mirrors your GitLab group hierarchy:

```
destination_path/
├── repo1/                    # Direct repository in main group
├── repo2/                    # Direct repository in main group
├── subgroup1/               # Directory for subgroup1
│   ├── repo3/               # Repository from subgroup1
│   └── nested_subgroup/     # Nested subgroup directory
│       └── repo4/           # Repository from nested subgroup
└── subgroup2/               # Directory for subgroup2
    └── repo5/               # Repository from subgroup2
```

## GitLab Access Token

### For Cloner

You need a GitLab access token with read permissions:

1. Go to your GitLab instance
2. Navigate to User Settings → Access Tokens
3. Create a new token with the following scopes:
   - `read_api` (to read group and project information)
   - `read_repository` (to clone repositories)

### For Publisher

You need a GitLab access token with write permissions:

1. Go to your GitLab instance
2. Navigate to User Settings → Access Tokens
3. Create a new token with the following scopes:
   - `api` (to create groups and projects)
   - `write_repository` (to push code)

## Error Handling

The tool includes comprehensive error handling for:
- Network connectivity issues
- Authentication failures
- Git cloning errors
- File system permissions
- API rate limiting

## Logging

The tool provides detailed logging including:
- Authentication status
- Group and repository discovery
- Cloning progress
- Error messages
- Final statistics

## Requirements

- Python 3.7+
- Git installed and accessible from command line
- Network access to the GitLab server
- Valid GitLab access token

## Dependencies

- `requests`: HTTP library for API calls
- `python-gitlab`: Official GitLab API client
- `gitpython`: Git operations in Python
- `click`: Command-line interface framework
