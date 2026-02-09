# Agent Instructions

## ⚠️ CRITICAL: Self-Hosted Development

**This is the Speckle project itself. Tasks MUST be Speckle tasks.**

We develop **Speckle using Speckle** - this is our core dogfooding principle:

| Rule | Description |
|------|-------------|
| **Issue prefix** | All issues use `speckle-` prefix (configured) |
| **Workflow** | Use `/speckle.*` commands for all work |
| **Tracking** | Track progress via beads (`bd ready`, `bd close`) |
| **Memory** | Implementation context persists in bead comments |

```bash
# CORRECT: Use Speckle workflows
/speckle.sync              # Sync tasks to beads
/speckle.implement         # Implement with tracking
/speckle.bugfix "issue"    # Start bugfix workflow

# CORRECT: Use bd for issue tracking
bd ready                   # Find next task
bd close speckle-abc       # Complete task

# WRONG: Do NOT use external issue trackers
# WRONG: Do NOT skip beads tracking
# WRONG: Do NOT work without speckle- prefixed issues
```

This ensures every improvement to Speckle validates the tool itself.
See [docs/SELF-HOSTING.md](docs/SELF-HOSTING.md) for the complete dogfooding philosophy.

---

## Issue Tracking

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
