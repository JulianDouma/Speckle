# GitHub Authentication Status

Show the current GitHub authentication status for Speckle.

## Usage

```
/speckle.github.auth
```

## What It Does

Checks and displays authentication status from:
1. Environment variables (GITHUB_TOKEN, GH_TOKEN)
2. GitHub CLI (gh auth token)
3. Config file (~/.speckle/config.toml)

## Command

```bash
python3 .speckle/scripts/github.py auth
```

## Setup Instructions

To authenticate with GitHub, use one of these methods:

### Option 1: Environment Variable (Recommended for CI)
```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
```

### Option 2: GitHub CLI (Recommended for local dev)
```bash
gh auth login
```

### Option 3: Config File
Create `~/.speckle/config.toml`:
```toml
[github]
token = "ghp_xxxxxxxxxxxxxxxxxxxx"
```

## Security Notes

- Never commit tokens to source control
- Use fine-grained tokens with minimal scopes
- Prefer gh CLI for local development (secure credential storage)
