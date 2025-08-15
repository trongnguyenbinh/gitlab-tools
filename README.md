# GitLab Repository Cloner

A Python tool to recursively clone all Git repositories from a GitLab self-hosted server within a specified group hierarchy.

## Features

- **Recursive Group Scanning**: Automatically discovers and processes all subgroups within a GitLab group hierarchy
- **Maintains Directory Structure**: Creates local directories that mirror the GitLab group structure
- **Breadth-First Processing**: Uses a queue-based approach for efficient traversal
- **Error Handling**: Robust error handling for API calls and git operations
- **Progress Tracking**: Detailed logging and statistics reporting
- **Skip Existing**: Automatically skips repositories that are already cloned locally

## Installation

1. Clone or download this project
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

```bash
python gitlab_cloner.py --gitlab-url <GITLAB_URL> --token <ACCESS_TOKEN> --group <GROUP_ID_OR_PATH> --destination <LOCAL_PATH>
```

### Parameters

- `--gitlab-url`: GitLab base URL (e.g., "https://gitlab.company.com")
- `--token`: GitLab API access token for authentication
- `--group`: Group ID (numeric) or group path (string) to start cloning from
- `--destination`: Local destination path where repositories should be cloned
- `--verbose`, `-v`: Enable verbose logging (optional)

### Examples

```bash
# Clone using group ID
python gitlab_cloner.py --gitlab-url https://gitlab.company.com --token glpat-xxxxxxxxxxxxxxxxxxxx --group 123 --destination ./my-repos

# Clone using group path
python gitlab_cloner.py --gitlab-url https://gitlab.company.com --token glpat-xxxxxxxxxxxxxxxxxxxx --group "my-organization/development" --destination ./dev-repos

# Enable verbose logging
python gitlab_cloner.py --gitlab-url https://gitlab.company.com --token glpat-xxxxxxxxxxxxxxxxxxxx --group 123 --destination ./repos --verbose
```

## How It Works

1. **Authentication**: Connects to the GitLab API using the provided access token
2. **Initial Group Scan**: Scans the specified group to identify repositories and subgroups
3. **Repository Cloning**: Clones repositories directly to the current directory level
4. **Subgroup Processing**: Creates local directories for subgroups and queues them for processing
5. **Recursive Processing**: Continues processing subgroups until all levels are complete

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

To use this tool, you need a GitLab access token with appropriate permissions:

1. Go to your GitLab instance
2. Navigate to User Settings → Access Tokens
3. Create a new token with the following scopes:
   - `read_api` (to read group and project information)
   - `read_repository` (to clone repositories)

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
