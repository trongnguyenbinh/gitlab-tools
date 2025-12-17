# Quick Start Guide

## Overview

This project provides two complementary tools for managing GitLab repositories:

1. **GitLab Cloner** - Download repositories from GitLab to local storage
2. **GitLab Publisher** - Upload local repositories to GitLab

## Installation

```bash
pip install -r requirements.txt
```

## GitLab Cloner

### Purpose
Clone all repositories from a GitLab group hierarchy to your local machine, maintaining the group/subgroup structure.

### Basic Usage

```bash
python gitlab_cloner.py \
  --gitlab-url https://gitlab.company.com \
  --token YOUR_READ_TOKEN \
  --group 123 \
  --destination ./my-repos
```

### What It Does

1. Connects to GitLab and authenticates
2. Scans the specified group and all subgroups
3. **First run**: Clones all repositories
4. **Subsequent runs**: Fetches and pulls all branches for existing repos, clones new repos

### Required Token Permissions
- `read_api`
- `read_repository`

---

## GitLab Publisher

### Purpose
Publish local Git repositories to a GitLab group hierarchy, creating groups and projects as needed.

### Basic Usage

```bash
# Default: Uses HTTPS with token authentication (recommended)
python gitlab_publisher.py \
  --gitlab-url https://gitlab.company.com \
  --token YOUR_WRITE_TOKEN \
  --group-id 456 \
  --source ./my-repos

# Alternative: Use SSH (requires SSH keys configured)
python gitlab_publisher.py \
  --gitlab-url https://gitlab.company.com \
  --token YOUR_WRITE_TOKEN \
  --group-id 456 \
  --source ./my-repos \
  --use-ssh
```

### What It Does

1. Connects to GitLab and authenticates
2. Scans the source directory for Git repositories
3. Creates groups/subgroups matching the directory structure
4. Creates projects for each repository
5. Pushes all branches to GitLab

### Required Token Permissions
- `api`
- `write_repository`

---

## Common Use Cases

### 1. Backup GitLab Repositories

```bash
# Clone everything to local backup
python gitlab_cloner.py \
  --gitlab-url https://gitlab.company.com \
  --token READ_TOKEN \
  --group 123 \
  --destination ./backup
```

### 2. Migrate Between GitLab Instances

```bash
# Step 1: Clone from source GitLab
python gitlab_cloner.py \
  --gitlab-url https://source.gitlab.com \
  --token SOURCE_TOKEN \
  --group 123 \
  --destination ./migration-temp

# Step 2: Publish to target GitLab
python gitlab_publisher.py \
  --gitlab-url https://target.gitlab.com \
  --token TARGET_TOKEN \
  --group-id 456 \
  --source ./migration-temp
```

### 3. Regular Sync/Updates

```bash
# Run periodically to keep local copies up-to-date
python gitlab_cloner.py \
  --gitlab-url https://gitlab.company.com \
  --token READ_TOKEN \
  --group 123 \
  --destination ./repos
```

### 4. Publish Local Projects

```bash
# Publish a directory of local projects to GitLab
python gitlab_publisher.py \
  --gitlab-url https://gitlab.company.com \
  --token WRITE_TOKEN \
  --group-id 789 \
  --source ./local-projects
```

---

## Directory Structure Mapping

### Cloner Output
```
destination/
├── repo1/                    # Direct repo in group
├── repo2/                    # Direct repo in group
├── subgroup1/               # Subgroup becomes directory
│   ├── repo3/
│   └── repo4/
└── subgroup2/
    └── repo5/
```

### Publisher Input
```
source/
├── project-a/               # Git repo → Creates project in target group
├── backend/                 # Directory → Creates subgroup
│   ├── api/                # Git repo → Creates project in "backend" group
│   └── worker/             # Git repo → Creates project in "backend" group
└── frontend/               # Directory → Creates subgroup
    └── app/                # Git repo → Creates project in "frontend" group
```

---

## Troubleshooting

### Cloner Issues

**Problem**: "Repository already exists, skipping"
- **Old behavior**: Repositories were skipped
- **New behavior**: Repositories are updated with all branches

**Problem**: Git clone error with trailing space
- **Solution**: Name sanitization is now automatic

### Publisher Issues

**Problem**: "fatal: Could not read from remote repository"
- **Cause**: Using SSH without SSH keys configured
- **Solution**: Use default HTTPS mode (don't use `--use-ssh` flag)
- **Alternative**: Configure SSH keys with GitLab if you need SSH

**Problem**: Authentication failed
- **Check**: Token has `api` scope, not just `read_api`

**Problem**: Failed to create group
- **Check**: You have permissions to create groups in the target
- **Check**: Group name doesn't already exist

**Problem**: Push failed (with HTTPS)
- **Check**: Token has `write_repository` scope
- **Check**: Token is valid and not expired

**Problem**: Push failed (with SSH)
- **Check**: SSH keys are configured in GitLab
- **Check**: SSH keys are loaded in ssh-agent
- **Tip**: Use HTTPS mode instead (default, no `--use-ssh` flag)

---

## Advanced Usage

### Programmatic Usage

Both tools can be used programmatically:

```python
from gitlab_cloner import GitLabCloner
from gitlab_publisher import GitLabPublisher

# Clone
cloner = GitLabCloner(gitlab_url, token, destination)
cloner.clone_group_recursively(group_id)

# Publish
publisher = GitLabPublisher(gitlab_url, token, source)
publisher.scan_and_publish(target_group_id)
```

See `example_usage.py` and `example_publisher_usage.py` for more examples.

---

## Statistics

Both tools provide detailed statistics:

### Cloner Stats
- Groups processed
- Repositories cloned (new)
- Repositories updated (existing)
- Errors encountered

### Publisher Stats
- Groups created
- Repositories created
- Repositories updated
- Branches pushed
- Errors encountered
