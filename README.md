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
  - Clones new repositories using HTTPS (no SSH setup required)
  - Automatically fetches and creates local tracking branches for all remote branches during clone
  - Automatically updates existing repositories by fetching and pulling all remote branches
  - Creates local tracking branches for any new remote branches discovered during updates
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
- `--verbose`, `-v`: Enable verbose logging (shows all details)
- `--quiet`, `-q`: Quiet mode (shows only progress bar and errors at the end)

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
- `--verbose`, `-v`: Enable verbose logging (shows all details)
- `--quiet`, `-q`: Quiet mode (shows only progress bar and errors at the end)

**Note**: By default, the publisher uses HTTPS with token authentication (recommended). Only use `--use-ssh` if you have SSH keys configured with GitLab.

#### Examples

```bash
# Publish all repositories from a directory
gitlab-publish --gitlab-url https://gitlab.company.com --token glpat-xxxxxxxxxxxxxxxxxxxx --group-id 456 --source ./my-repos

# Publish with quiet mode (progress bar only)
gitlab-publish --gitlab-url https://gitlab.company.com --token glpat-xxxxxxxxxxxxxxxxxxxx --group-id 456 --source ./my-repos --quiet

# Migrate repositories from one GitLab to another
# Step 1: Clone from source
gitlab-clone --gitlab-url https://source.gitlab.com --token SOURCE_TOKEN --group 123 --destination ./temp-repos --quiet
# Step 2: Publish to target
gitlab-publish --gitlab-url https://target.gitlab.com --token TARGET_TOKEN --group-id 456 --source ./temp-repos --quiet
```

## How It Works

### Cloner

1. **Authentication**: Connects to the GitLab API using the provided access token
2. **Initial Group Scan**: Scans the specified group to identify repositories and subgroups
3. **Repository Management**:
   - For new repositories (clone): 
     - Clones them to the appropriate directory
     - Prefers HTTPS URLs over SSH (no SSH setup required)
     - Automatically fetches all remote branches and creates local tracking branches
   - For existing repositories (pull): 
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

## Output Modes

### Default Mode (Normal Output)
Shows all operations being performed:
```
INFO - Cloning my-project using HTTPS
INFO - Fetching all remote branches for my-project
INFO - Successfully cloned: /path/to/my-project
```

### Verbose Mode (`--verbose`)
Shows even more detailed information including debug messages:
```bash
gitlab-clone --gitlab-url URL --token TOKEN --group 123 --destination ./repos --verbose
```

### Quiet Mode (`--quiet`)
Shows only a progress bar and final error summary:
```bash
gitlab-clone --gitlab-url URL --token TOKEN --group 123 --destination ./repos --quiet
```

Output:
```
Cloning group 'my-group' (45 repositories)...

Processing repositories |████████████████████████| 45/45 [100%]

================================================================================
PROCESSING COMPLETE: 45/45 repositories processed
================================================================================

✓ No errors encountered!
```

If errors occur:
```
✗ 3 ERROR(S) ENCOUNTERED:

Repository: repo-name
  • Git error: failed to fetch branch develop
  • Failed to create branch hotfix/bug-123

Repository: another-repo
  • Connection timeout
```

## Detailed Behavior

### When Cloning Repositories

The cloner performs the following steps for each repository:

1. Clone: Creates a local clone of the repository using HTTPS
2. Fetch All Branches: Automatically fetches all remote branches from GitLab
3. Create Local Branches: Creates local tracking branches for each remote branch found
4. Status: Logs the number of branches created

Example output:
```
2025-12-17 12:00:00,000 - gitlab_cloner - INFO - Cloning my-project using HTTPS
2025-12-17 12:00:05,000 - gitlab_cloner - INFO - Fetching all remote branches for my-project
2025-12-17 12:00:06,000 - gitlab_cloner - INFO - Found 8 remote branches
2025-12-17 12:00:06,100 - gitlab_cloner - INFO - Creating local branch: develop
2025-12-17 12:00:06,200 - gitlab_cloner - INFO - Creating local branch: feature/auth
2025-12-17 12:00:06,300 - gitlab_cloner - INFO - Creating local branch: hotfix/bug-123
2025-12-17 12:00:06,500 - gitlab_cloner - INFO - Successfully fetched all branches for my-project
2025-12-17 12:00:06,500 - gitlab_cloner - INFO - All branches available locally for my-project
```

### When Updating Existing Repositories

If a repository already exists locally, the cloner:

1. Fetch: Fetches all updates from remote
2. Update Branches: Pulls the latest changes for each existing local branch
3. Create New Branches: Creates local tracking branches for any new remote branches
4. Restore Position: Returns to the original branch after updating

### Result

After running the cloner, you have:
- All repositories from the GitLab group hierarchy
- All branches from each repository as local branches
- No need for SSH key setup (HTTPS is used)
- Complete access to all project history and branches

## Troubleshooting

### Cloner Issues

**Problem**: Repository names with trailing spaces or invalid characters
- **Solution**: Automatic sanitization is built-in, names are cleaned automatically

**Problem**: "Repository already exists"
- **Behavior**: The tool now automatically updates existing repositories with all branches

**Problem**: "No 'origin' remote found"
- **Cause**: Repository doesn't have an 'origin' remote configured
- **Solution**: Ensure the repository was cloned properly with a valid remote URL

**Problem**: "'IterableList' object has no attribute 'origin'"
- **Cause**: Internal error when accessing git remotes
- **Solution**: This is automatically handled by the tool. If you see this error, update to the latest version
- **Details**: The tool safely iterates through remotes instead of using dot notation

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

## Cleanup Feature

The cleanup feature allows you to automatically remove build artifacts, dependencies, and temporary files from repositories across all branches. This is useful for reducing repository size before backup or migration.

### Overview

The cleanup feature:
- Removes files matching configurable patterns (build artifacts, dependencies, logs, etc.)
- Operates on all branches in a repository
- Supports dry-run mode to preview changes before applying them
- Optionally auto-commits and pushes changes
- Provides detailed logging at every step

### Quick Start

**Preview cleanup (dry-run with detailed logs):**
```bash
python -m gitlab_tools.cli_cloner \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxxxxxxxxxxxxxxxxxx \
  --group my-group \
  --destination /repos \
  --cleanup \
  --cleanup-dry-run \
  --verbose
```

**Run actual cleanup with auto-commit:**
```bash
python -m gitlab_tools.cli_cloner \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxxxxxxxxxxxxxxxxxx \
  --group my-group \
  --destination /repos \
  --cleanup \
  --cleanup-auto-commit \
  --verbose
```

### Cleanup Parameters

- `--cleanup`: Enable cleanup feature
- `--cleanup-dry-run`: Preview changes without modifying files (recommended first step)
- `--cleanup-auto-commit`: Automatically commit and push cleanup changes
- `--cleanup-patterns`: Comma-separated patterns to remove (default: `target/,build/,dist/,out/,node_modules/,vendor/,*.log,*.tmp,*.class,*.jar`)
- `--cleanup-keep-patterns`: Comma-separated patterns to protect from removal (whitelist)

### Detailed Logging

The cleanup feature provides comprehensive logging at every step to verify it's working correctly:

#### What to Look For in Logs

**✅ Success Indicators:**

| Log Message | Meaning |
|-------------|---------|
| `Found N remote branches` | All branches discovered |
| `[1/N] Processing branch` | Each branch being processed |
| `✓ Checked out branch` | Branch checkout succeeded |
| `[CLEANUP] Starting cleanup` | Cleanup started on branch |
| `[PATTERN] Match found` | File matched cleanup pattern |
| `[DRY-RUN] Would remove` | File would be removed (dry-run mode) |
| `[REMOVED]` | File was actually removed |
| `Scan complete: X scanned, Y matched` | Scan finished with results |
| `✓ Cleanup completed successfully` | Cleanup succeeded on branch |
| `✓ Successfully returned to original branch` | Returned to starting branch |
| `Branches processed: N` | All branches were processed |

**⚠️ Warning Signs:**

| Log Message | Issue |
|-------------|-------|
| `Found 0 remote branches` | No branches found |
| No `[CLEANUP]` logs | Cleanup not running |
| `No files matched cleanup patterns` | No files to remove |
| `Could not return to original branch` | Git state issue |
| `Failed to commit/push` | Auto-commit failed |

#### Example Log Output

```
======================================================================
Starting branch processing for project: my-project
======================================================================
Found 3 remote branches: ['origin/main', 'origin/develop', 'origin/feature']
Current branch before processing: main

[1/3] Processing branch: main
  ✓ Checked out branch: main
  ✓ Pulled latest updates for branch: main
  [CLEANUP] Starting cleanup for branch: main
  [CLEANUP] Patterns to remove: ['target/', 'build/', 'dist/', ...]
  [PATTERN] Match found: build/ matches pattern 'build/'
  [CLEANUP] Removing: /repos/my-project/build
    [DRY-RUN] Would remove directory: /repos/my-project/build
  [PATTERN] Match found: app.log matches pattern '*.log'
  [CLEANUP] Removing: /repos/my-project/app.log
    [DRY-RUN] Would remove file: /repos/my-project/app.log
  [CLEANUP] Scan complete: 1250 files scanned, 2 matched patterns
  [CLEANUP] Successfully removed 2 items
  ✓ Cleanup completed successfully for branch: main

[2/3] Processing branch: develop
  ✓ Checked out branch: develop
  ✓ Pulled latest updates for branch: develop
  [CLEANUP] Starting cleanup for branch: develop
  [CLEANUP] Scan complete: 1250 files scanned, 0 matched patterns
  ✓ Cleanup completed successfully for branch: develop

======================================================================
SUMMARY for my-project:
  Total branches found: 3
  Branches processed: 3
  Branches with cleanup: 1
  Status: Successfully updated all branches
======================================================================
```

### Cleanup Workflow

**Recommended workflow:**

1. **Preview with dry-run:**
   ```bash
   python -m gitlab_tools.cli_cloner \
     --gitlab-url https://gitlab.example.com \
     --token glpat-xxxxxxxxxxxxxxxxxxxx \
     --group my-group \
     --destination /repos \
     --cleanup \
     --cleanup-dry-run \
     --verbose
   ```
   - Review logs to verify all branches are being processed
   - Check pattern matching logs to confirm correct files are identified
   - Verify no important files are being removed

2. **Run actual cleanup:**
   ```bash
   python -m gitlab_tools.cli_cloner \
     --gitlab-url https://gitlab.example.com \
     --token glpat-xxxxxxxxxxxxxxxxxxxx \
     --group my-group \
     --destination /repos \
     --cleanup \
     --cleanup-auto-commit \
     --verbose
   ```
   - Cleanup runs on all branches
   - .gitignore is automatically updated with cleanup patterns
   - Files matching cleanup patterns are removed from Git's cache
   - Changes are automatically committed and pushed
   - Review final summary to confirm all branches processed

### Preventing Future Tracking

The cleanup feature automatically prevents cleaned-up files from being tracked by Git in the future through three steps:

1. **Removes Files**: Deletes files matching cleanup patterns from the working directory
2. **Updates .gitignore**: Adds cleanup patterns to .gitignore to prevent future commits
3. **Cleans Git Cache**: Removes existing files from Git's index using `git rm --cached`

This ensures that:
- ✓ Cleaned files won't reappear in future commits
- ✓ .gitignore rules apply to existing files in the repository
- ✓ Future developers won't accidentally commit these files
- ✓ Repository size stays reduced over time

#### Auto-Commit and Push

When `--cleanup-auto-commit` is enabled, the cleanup feature automatically:

1. **Stages Changes**: All modifications (.gitignore updates and git cache removals) are staged
2. **Commits Changes**: Creates a commit with the message "chore: cleanup unnecessary files"
3. **Pushes to Remote**: Pushes the commit to the remote repository for all team members

**What happens during cleanup with auto-commit:**
```
1. Files matching patterns are removed from disk
   └─ [CLEANUP] Removing: /repos/my-project/build/

2. .gitignore is updated with cleanup patterns
   └─ [GITIGNORE] Added 15 patterns to .gitignore

3. Files are removed from Git's cache (index)
   └─ [GIT-CACHE] Removed 3 pattern(s) from Git cache

4. All changes are staged
   └─ git add -A

5. Changes are committed
   └─ git commit -m "chore: cleanup unnecessary files"

6. Commit is pushed to remote
   └─ git push origin branch-name
```

#### Commit Details

The cleanup commit includes:
- **Modified .gitignore**: Contains new cleanup patterns to prevent future tracking
- **Removed files from Git cache**: Files are no longer tracked by Git but remain on disk
- **Commit message**: "chore: cleanup unnecessary files" (configurable)

This ensures that:
- ✓ All team members receive the .gitignore updates
- ✓ Cleaned files won't be re-added in future commits
- ✓ Repository history shows cleanup was performed
- ✓ Changes are shared across all branches and developers

### Verification Checklist

Before running actual cleanup, verify these in the dry-run logs:

- [ ] "Found N remote branches" - All branches discovered
- [ ] "[1/N] Processing branch" - Each branch processed
- [ ] "✓ Checked out branch" - Branch checkout succeeded
- [ ] "[CLEANUP] Starting cleanup" - Cleanup ran
- [ ] "[PATTERN] Match found" - Files matched patterns
- [ ] "[DRY-RUN] Would remove" - Files identified for removal
- [ ] "Scan complete: X files scanned, Y matched" - Scan finished
- [ ] "✓ Cleanup completed successfully" - Cleanup succeeded
- [ ] "✓ Successfully returned to original branch" - Returned to start
- [ ] "Branches processed: N" - All branches processed

### Protecting Important Files

Use `--cleanup-keep-patterns` to protect important files from removal:

```bash
python -m gitlab_tools.cli_cloner \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxxxxxxxxxxxxxxxxxx \
  --group my-group \
  --destination /repos \
  --cleanup \
  --cleanup-dry-run \
  --cleanup-keep-patterns "important.log,config.log,README.md" \
  --verbose
```

### Troubleshooting Cleanup

**Q: Only some branches show cleanup**
- Check logs for error messages in failed branches
- Verify branch checkout and pull operations succeeded

**Q: No files are being removed**
- Check for "No files matched cleanup patterns" in logs
- Verify patterns are correct and files actually exist
- Use `--verbose` to see detailed pattern matching

**Q: Important files were removed**
- Use `--cleanup-keep-patterns` to whitelist them
- Always use `--cleanup-dry-run` first to preview changes

**Q: Can't see individual file removals**
- Use `--verbose` flag for debug-level logs
- Check for `[PATTERN]` and `[CLEANUP]` prefixed messages

**Q: .gitignore update failed**
- Check file permissions on .gitignore
- Verify the repository is writable
- Check logs for "[GITIGNORE]" messages

**Q: Git cache removal failed**
- Ensure Git is installed and accessible from command line
- Check that you have permission to modify the repository
- Look for "[GIT-CACHE]" messages in logs
- The cleanup will still succeed even if cache removal fails

**Q: Files still appear in Git history**
- Use the `--cleanup-history` flag to remove files from git history
- See the "Git History Cleanup" section below for details
- The .gitignore update prevents future commits with these files

**Q: Cleanup committed but .gitignore wasn't updated**
- Check if .gitignore already contained the patterns
- Look for "[GITIGNORE] All cleanup patterns already in .gitignore" in logs
- Verify .gitignore has proper permissions

**Q: Auto-commit failed**
- Check logs for "[CLEANUP] Failed to commit/push cleanup" messages
- Verify you have push permissions to the remote repository
- Check that the branch exists on the remote
- Ensure Git is properly configured with user.name and user.email
- Try running without auto-commit first to verify cleanup works

**Q: .gitignore changes not pushed to remote**
- Check logs for "[CLEANUP] Pushed cleanup changes" message
- Verify network connectivity to the remote repository
- Check that you have push permissions
- Ensure the branch is properly tracked on the remote
- Look for Git error messages in the logs

**Q: Commit message is wrong**
- Use `--cleanup-commit-message` to customize the message
- Default message is "chore: cleanup unnecessary files"
- Verify the message in git log after cleanup completes

**Q: Changes committed but not all files removed**
- This is expected - cleanup only removes files matching patterns
- Check the cleanup patterns with `--cleanup-patterns`
- Use `--cleanup-dry-run` to preview what would be removed
- Verify patterns are correct for your file types

### Default Cleanup Patterns

By default, the following patterns are removed:

- **Build artifacts**: `target/`, `build/`, `dist/`, `out/`
- **Dependencies**: `node_modules/`, `vendor/`
- **Compiled files**: `*.class`, `*.jar`
- **Temporary files**: `*.log`, `*.tmp`

Override with `--cleanup-patterns` if needed.

### Git History Cleanup

The `--cleanup-history` flag enables rewriting git history to permanently remove junk files from all commits across all branches. This is useful for significantly reducing repository size when large build artifacts or dependencies were accidentally committed in the past.

**⚠️ WARNING**: This is a destructive operation that:
- Rewrites all commit hashes in the repository
- Requires force-pushing to all branches
- Cannot be undone once pushed to remote
- May cause issues for other developers who have cloned the repository

**Prerequisites:**
```bash
pip install git-filter-repo
```

**Usage:**
```bash
# Preview what would be removed from history (dry-run with detailed analysis)
python -m gitlab_tools.cli_cloner \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxxxxxxxxxxxxxxxxxx \
  --group my-group \
  --destination /repos \
  --cleanup \
  --cleanup-history \
  --cleanup-dry-run \
  --verbose

# Actually rewrite history and force push
python -m gitlab_tools.cli_cloner \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxxxxxxxxxxxxxxxxxx \
  --group my-group \
  --destination /repos \
  --cleanup \
  --cleanup-history \
  --cleanup-auto-commit \
  --verbose
```

**How it works:**
1. Processes all branches normally (checkout, pull, cleanup)
2. After all branches are processed, runs history analysis or `git-filter-repo`
3. In dry-run: Analyzes all branches and generates detailed report
4. In auto-commit: Removes all files matching cleanup patterns from all commits
5. Force pushes all branches to remote with rewritten history

**What gets removed from history:**
- Only file patterns (e.g., `*.jar`, `*.war`, `*.class`, `*.zip`)
- Directory patterns are NOT removed from history (only from current state)
- Patterns are taken from `--cleanup-patterns`

**Example dry-run output:**
```
======================================================================
Starting git history cleanup for my-project...
======================================================================
    [HISTORY] Starting git history cleanup...
    [HISTORY] This will rewrite git history and change all commit hashes!
    [HISTORY] Will remove 3 file patterns from history:
    [HISTORY]   - *.jar
    [HISTORY]   - *.war
    [HISTORY]   - *.zip
    [HISTORY] DRY-RUN: Analyzing git history across all branches...
    [HISTORY] Analysis Results:
    [HISTORY] ============================================================
    [HISTORY] Branch: feature/x (45 commits)
    [HISTORY]   Files to remove from history:
    [HISTORY]     - lib/commons.jar (appears in 8 commits, ~0.2 MB)
    [HISTORY]     - lib/servlet.war (appears in 5 commits, ~0.1 MB)
    [HISTORY]   Total: 2 files, 45 commits, ~0.3 MB
    [HISTORY]
    [HISTORY] Branch: feature/y (38 commits)
    [HISTORY]   Files to remove from history:
    [HISTORY]     - build/app.jar (appears in 12 commits, ~0.3 MB)
    [HISTORY]   Total: 1 file, 38 commits, ~0.3 MB
    [HISTORY]
    [HISTORY] Branch: main (120 commits)
    [HISTORY]   Files to remove from history:
    [HISTORY]     - dist/app.zip (appears in 3 commits, ~0.4 MB)
    [HISTORY]   Total: 1 file, 120 commits, ~0.4 MB
    [HISTORY]
    [HISTORY] ============================================================
    [HISTORY] SUMMARY - DRY-RUN REPORT
    [HISTORY] ============================================================
    [HISTORY] Total branches analyzed: 3
    [HISTORY] Total unique files to remove: 4
    [HISTORY] Total commit references: 203
    [HISTORY] Estimated size reduction: ~1.0 MB
    [HISTORY]
    [HISTORY] WARNING: This will rewrite ALL commit hashes!
    [HISTORY]
    [HISTORY] DRY-RUN: No changes made to repository
    [HISTORY] To actually rewrite history, run with --cleanup-auto-commit
```

**Example auto-commit output:**
```
======================================================================
Starting git history cleanup for my-project...
======================================================================
    [HISTORY] Starting git history cleanup...
    [HISTORY] This will rewrite git history and change all commit hashes!
    [HISTORY] Will remove 3 file patterns from history:
    [HISTORY]   - *.jar
    [HISTORY]   - *.war
    [HISTORY]   - *.zip
    [HISTORY] Running: git filter-repo --invert-paths --path-glob *.jar ...
    [HISTORY] Successfully rewrote git history
    [HISTORY] Force pushing 3 branches to remote...
    [HISTORY] Force pushing branch: main
    [HISTORY] ✓ Successfully force pushed: main
    [HISTORY] Force pushing branch: feature/x
    [HISTORY] ✓ Successfully force pushed: feature/x
    [HISTORY] Force pushing branch: feature/y
    [HISTORY] ✓ Successfully force pushed: feature/y
    [HISTORY] Force push summary: 3 succeeded, 0 failed
✓ Git history cleanup completed successfully
```

**Best practices:**
1. **Always use dry-run first** to preview what will be removed
   - Shows detailed per-branch analysis
   - Lists all files that would be removed
   - Estimates size reduction
   - No changes made to repository
2. **Review the dry-run report** carefully
   - Check which branches are affected
   - Verify no important files will be removed
   - Note the estimated size reduction
3. **Coordinate with your team** before rewriting history
4. **Backup the repository** before running history cleanup
5. **Notify team members** to re-clone after history rewrite
6. **Use with auto-commit** to ensure changes are pushed

**Troubleshooting:**

**Q: git-filter-repo not found**
- Install it: `pip install git-filter-repo`
- Verify installation: `git filter-repo --version`

**Q: Force push failed**
- Check that you have push permissions to all branches
- Verify network connectivity to remote repository
- Check for branch protection rules that prevent force push

**Q: Repository size didn't decrease**
- Git keeps old objects for ~2 weeks by default
- Run `git gc --aggressive --prune=now` to clean up immediately
- On GitLab, go to Settings > Repository > Repository cleanup to recalculate size

**Q: Other developers can't pull after history rewrite**
- This is expected - they need to re-clone the repository
- Or they can run: `git fetch origin && git reset --hard origin/branch-name`
- Coordinate with team before running history cleanup

**Q: Some files still in history**
- Only file patterns (*.jar, *.zip) are removed from history
- Directory patterns (build/, dist/) are only removed from current state
- Check the log to see which patterns were processed

### Cleanup and History Cleanup Issues

**Q: Only some branches show cleanup**
- Check logs for error messages in failed branches
- Verify branch checkout and pull operations succeeded

**Q: No files are being removed**
- Check for "No files matched cleanup patterns" in logs
- Verify patterns are correct and files actually exist
- Use `--verbose` to see detailed pattern matching

**Q: Important files were removed**
- Use `--cleanup-keep-patterns` to whitelist them
- Always use `--cleanup-dry-run` first to preview changes

**Q: .gitignore update failed**
- Check file permissions on .gitignore
- Verify the repository is writable
- Check logs for "[GITIGNORE]" messages

**Q: Auto-commit failed**
- Check logs for "[CLEANUP] Failed to commit/push cleanup" messages
- Verify you have push permissions to the remote repository
- Ensure Git is properly configured with user.name and user.email

**Q: Files still appear in Git history**
- Use the `--cleanup-history` flag to remove files from git history
- Always use `--cleanup-dry-run` first to preview what will be removed
- The .gitignore update prevents future commits with these files

**Q: git-filter-repo not found**
- Install it: `pip install git-filter-repo`
- Verify installation: `git filter-repo --version`

**Q: Force push failed during history cleanup**
- Check that you have push permissions to all branches
- Verify network connectivity to remote repository
- Check for branch protection rules that prevent force push

**Q: Repository size didn't decrease after history cleanup**
- Git keeps old objects for ~2 weeks by default
- Run `git gc --aggressive --prune=now` to clean up immediately
- On GitLab, go to Settings > Repository > Repository cleanup to recalculate size

**Q: Other developers can't pull after history rewrite**
- This is expected - they need to re-clone the repository
- Or they can run: `git fetch origin && git reset --hard origin/branch-name`
- Coordinate with team before running history cleanup

## Dependencies

- `requests`: HTTP library for API calls
- `python-gitlab`: Official GitLab API client
- `gitpython`: Git operations in Python
- `click`: Command-line interface framework
- `tqdm`: Progress bar library
- `git-filter-repo`: (Optional) Required for `--cleanup-history` feature

All dependencies are listed in `requirements.txt` and installed automatically with `pip install -r requirements.txt`.

To use the git history cleanup feature, install git-filter-repo separately:
```bash
pip install git-filter-repo
```
