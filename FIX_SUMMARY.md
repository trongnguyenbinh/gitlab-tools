# Fix Summary: SSH Authentication Error

## Problem

The publisher was failing with errors like:
```
fatal: Could not read from remote repository.
```

## Root Cause

The publisher was defaulting to **SSH URLs** for pushing code, which requires:
- SSH keys to be generated
- SSH keys to be added to your GitLab account
- SSH keys to be loaded in your SSH agent

Without these configured, all push operations fail.

## Solution

Changed the default authentication method to **HTTPS with embedded token authentication**.

### What Changed

1. **Default behavior**: Now uses HTTPS URLs with the access token embedded
   - Format: `https://oauth2:TOKEN@gitlab.com/group/project.git`
   - No SSH setup required
   - Works out of the box with your API token

2. **Optional SSH mode**: Added `--use-ssh` flag for users who have SSH configured

### Before (Old Code)
```python
# Always preferred SSH
remote_url = project.ssh_url_to_repo if hasattr(project, 'ssh_url_to_repo') else project.http_url_to_repo
```

### After (Fixed Code)
```python
if self.use_ssh:
    # Use SSH only if explicitly requested
    remote_url = project.ssh_url_to_repo
else:
    # Default: Use HTTPS with token (no SSH keys needed)
    http_url = project.http_url_to_repo
    remote_url = http_url.replace('https://', f'https://oauth2:{self.access_token}@')
```

## Usage

### Default (Recommended) - HTTPS Authentication
```bash
python gitlab_publisher.py \
  --gitlab-url https://gitlab.company.com \
  --token YOUR_TOKEN \
  --group-id 456 \
  --source ./my-repos
```
✅ No SSH keys required
✅ Works with API token only
✅ Recommended for most users

### Alternative - SSH Authentication
```bash
python gitlab_publisher.py \
  --gitlab-url https://gitlab.company.com \
  --token YOUR_TOKEN \
  --group-id 456 \
  --source ./my-repos \
  --use-ssh
```
⚠️ Requires SSH keys configured in GitLab
⚠️ Requires SSH keys loaded in ssh-agent
⚠️ Only use if you specifically need SSH

## Benefits of HTTPS (Default)

1. **No Setup Required**: Works immediately with just your API token
2. **Cross-Platform**: Works on Windows, Linux, macOS without additional config
3. **Firewall Friendly**: HTTPS (port 443) is rarely blocked
4. **Simpler Troubleshooting**: Token authentication is straightforward

## When to Use SSH

- You have existing SSH keys configured
- Corporate policy requires SSH
- You're already using SSH for other Git operations
- You prefer SSH for security reasons

## Migration Guide

If you were using the old version and getting SSH errors:

### Option 1: Use HTTPS (Recommended)
Simply re-run without `--use-ssh` flag - it will now work!

### Option 2: Configure SSH (Advanced)
1. Generate SSH key: `ssh-keygen -t ed25519 -C "your_email@example.com"`
2. Add key to GitLab: Settings → SSH Keys
3. Test: `ssh -T git@gitlab.company.com`
4. Use with `--use-ssh` flag
