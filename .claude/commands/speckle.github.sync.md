# GitHub Sync

Bidirectional sync between beads issues and GitHub Issues.

## Usage

```
/speckle.github.sync
```

## What It Does

1. **Push**: Syncs all beads issues to GitHub Issues
   - Creates new issues if not linked
   - Updates existing linked issues
   - Maps priority/type to GitHub labels

2. **Pull**: Syncs GitHub Issues to beads
   - Creates new beads for unlinked GitHub issues
   - Skips pull requests
   - Preserves linkage for future syncs

## Command

```bash
python3 .speckle/scripts/github.py sync
```

## Related Commands

- `/speckle.github.auth` - Check authentication status
- `/speckle.github.push` - Push only (no pull)
- `/speckle.github.pull` - Pull only (no push)

## Label Mapping

| Beads Field | GitHub Label |
|-------------|--------------|
| Priority 0 | priority: critical |
| Priority 1 | priority: high |
| Priority 2 | priority: medium |
| Priority 3 | priority: low |
| Type: bug | type: bug |
| Type: feature | type: feature |
| Type: epic | type: epic |

## Linkage Storage

Links are stored in `.speckle/github-links.jsonl` for tracking which beads issues correspond to which GitHub issues.
