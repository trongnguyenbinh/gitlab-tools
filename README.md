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

## Requirements

- **Python 3.13+** (tested with Python 3.13.9)
- Git installed and accessible from command line
- Network access to the GitLab server
- Valid GitLab access token

## Installation

### Option 1: Install as Package (Recommended)

1. Ensure Python 3.13 or higher is installed:
   ```bash
   python --version
   # Should output: Python 3.13.x or higher
   ```

2. Clone this repository:
   ```bash
   git clone <repository-url>
   cd gitlab-cloner
   ```

3. Install the package:
   ```bash
   pip install -e .
   ```

4. Run using installed commands:
   ```bash
   gitlab-clone --help
   gitlab-publish --help
   ```

### Option 2: Run from Source

1. Ensure Python 3.13 or higher is installed

2. Clone this repository

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run directly:
   ```bash
   python -m gitlab_tools.cli_cloner --help
   python -m gitlab_tools.cli_publisher --help
   ```

## Usage

## Project Structure

```
gitlab-cloner/
├── src/
│   └── gitlab_tools/          # Main package
│       ├── __init__.py        # Package initialization
│       ├── cloner.py          # GitLab Cloner module
│       ├── publisher.py       # GitLab Publisher module
│       ├── config.py          # Configuration module
│       ├── cli_cloner.py      # CLI for cloner
│       └── cli_publisher.py   # CLI for publisher
├── tests/                     # Test suite
│   ├── __init__.py
│   └── test_cloner.py
├── docs/                      # Documentation
├── requirements.txt           # Dependencies
├── setup.py                   # Package setup
└── README.md                  # This file
```

## Usage

### GitLab Cloner - Clone Repositories from GitLab

#### Command Line Interface

**If installed as package:**
```bash
gitlab-clone --gitlab-url <GITLAB_URL> --token <ACCESS_TOKEN> --group <GROUP_ID_OR_PATH> --destination <LOCAL_PATH>
```

**If running from source:**
```bash
python -m gitlab_tools.cli_cloner --gitlab-url <GITLAB_URL> --token <ACCESS_TOKEN> --group <GROUP_ID_OR_PATH> --destination <LOCAL_PATH>
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
gitlab-clone --gitlab-url https://gitlab.company.com --token glpat-xxxxxxxxxxxxxxxxxxxx --group 123 --destination ./my-repos

# Clone using group path
gitlab-clone --gitlab-url https://gitlab.company.com --token glpat-xxxxxxxxxxxxxxxxxxxx --group "my-organization/development" --destination ./dev-repos

# Enable verbose logging
gitlab-clone --gitlab-url https://gitlab.company.com --token glpat-xxxxxxxxxxxxxxxxxxxx --group 123 --destination ./repos --verbose
```

### GitLab Publisher - Publish Repositories to GitLab

#### Command Line Interface

**If installed as package:**
```bash
gitlab-publish --gitlab-url <GITLAB_URL> --token <ACCESS_TOKEN> --group-id <TARGET_GROUP_ID> --source <LOCAL_PATH>
```

**If running from source:**
```bash
python -m gitlab_tools.cli_publisher --gitlab-url <GITLAB_URL> --token <ACCESS_TOKEN> --group-id <TARGET_GROUP_ID> --source <LOCAL_PATH>
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
gitlab-publish --gitlab-url https://gitlab.company.com --token glpat-xxxxxxxxxxxxxxxxxxxx --group-id 456 --source ./my-repos

# Migrate repositories from one GitLab to another
# Step 1: Clone from source
gitlab-clone --gitlab-url https://source.gitlab.com --token SOURCE_TOKEN --group 123 --destination ./temp-repos
# Step 2: Publish to target
gitlab-publish --gitlab-url https://target.gitlab.com --token TARGET_TOKEN --group-id 456 --source ./temp-repos
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

## Common Use Cases

### 1. Backup GitLab Repositories
```bash
gitlab-clone \
  --gitlab-url https://gitlab.company.com \
  --token YOUR_TOKEN \
  --group 123 \
  --destination ./backup
```

### 2. Migrate Between GitLab Instances
```bash
# Step 1: Clone from source
gitlab-clone \
  --gitlab-url https://source.gitlab.com \
  --token SOURCE_TOKEN \
  --group 123 \
  --destination ./migration-temp

# Step 2: Publish to target
gitlab-publish \
  --gitlab-url https://target.gitlab.com \
  --token TARGET_TOKEN \
  --group-id 456 \
  --source ./migration-temp
```

### 3. Regular Sync/Updates
```bash
# Run periodically to keep local copies up-to-date
gitlab-clone \
  --gitlab-url https://gitlab.company.com \
  --token YOUR_TOKEN \
  --group 123 \
  --destination ./repos
```

### 4. Publish Local Projects to GitLab
```bash
gitlab-publish \
  --gitlab-url https://gitlab.company.com \
  --token YOUR_TOKEN \
  --group-id 789 \
  --source ./local-projects
```

### 5. Programmatic Usage

```python
from gitlab_tools import GitLabCloner, GitLabPublisher

# Clone repositories
cloner = GitLabCloner(
    gitlab_url="https://gitlab.company.com",
    access_token="your-token",
    destination_path="./repos"
)
cloner.clone_group_recursively("123")

# Publish repositories
publisher = GitLabPublisher(
    gitlab_url="https://gitlab.company.com",
    access_token="your-token",
    source_path="./repos"
)
publisher.scan_and_publish(456)
```

## Troubleshooting

### Cloner Issues

**Problem**: Repository names with trailing spaces or invalid characters
- **Solution**: Automatic sanitization is built-in, names are cleaned automatically

**Problem**: "Repository already exists"
- **Behavior**: The tool now automatically updates existing repositories with all branches

### Publisher Issues

**Problem**: "fatal: Could not read from remote repository"
- **Cause**: Trying to use SSH without SSH keys configured
- **Solution**: Don't use `--use-ssh` flag (HTTPS is the default and recommended)

**Problem**: Authentication failed
- **Check**: Token has `api` scope for publisher (not just `read_api`)
- **Check**: Token is valid and not expired

**Problem**: Push failed
- **Check**: Token has `write_repository` scope
- **Check**: You have permission to create projects in the target group

## Dependencies

- `requests`: HTTP library for API calls
- `python-gitlab`: Official GitLab API client
- `gitpython`: Git operations in Python
- `click`: Command-line interface framework

All dependencies are listed in `requirements.txt` and installed automatically with `pip install -r requirements.txt`.
