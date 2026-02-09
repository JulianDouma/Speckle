# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Session Completion

Work is complete only after `git push` succeeds.

### Checklist

1. **File issues** for remaining work
2. **Run quality gates** (if code changed): tests, linters, builds
3. **Update issues**: close finished, update in-progress
4. **Push to remote**:
   ```bash
   git pull --rebase && bd sync && git push
   git status  # Should show "up to date with origin"
   ```
5. **Clean up**: `git stash clear`, `git remote prune origin`
6. **Hand off**: summarize progress and next steps

If push fails, resolve conflicts and retry until successful.
