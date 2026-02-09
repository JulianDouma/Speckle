<p align="center">
  <img src="cover.webp" alt="Speckle" width="600">
</p>

# 🔮 Speckle

**Spec-driven development with persistent memory.**

Speckle bridges [GitHub Spec Kit](https://github.com/github/spec-kit) specifications with 
[Beads](https://github.com/steveyegge/beads) issue tracking, providing workflow continuity 
and memory across AI agent sessions.

## Why Speckle?

| Without Speckle | With Speckle |
|-----------------|--------------|
| Tasks in markdown, no tracking | Tasks synced to beads with dependencies |
| "Where was I?" each session | `bd ready` shows exactly what's next |
| Lost implementation context | Comments preserve decisions and progress |
| Manual status updates | Bidirectional sync keeps everything aligned |

## Quick Start

### Prerequisites

```bash
# Install beads
curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash

# Install spec-kit  
pipx install "specify-cli @ git+https://github.com/github/spec-kit.git"

# Initialize in your project
specify init . --ai claude
bd init
```

### Install Speckle

```bash
# One-liner install (to current directory)
curl -fsSL https://raw.githubusercontent.com/JulianDouma/Speckle/main/install-remote.sh | bash

# Install to specific project
curl -fsSL https://raw.githubusercontent.com/JulianDouma/Speckle/main/install-remote.sh | bash -s -- /path/to/project

# Verify installation
curl -fsSL https://raw.githubusercontent.com/JulianDouma/Speckle/main/install-remote.sh | bash -s -- --check

# Restart your AI agent to load commands
```

### Speckle CLI

Speckle includes a unified CLI for common operations:

```bash
# Add to PATH (choose one):
export PATH="$PATH:/path/to/Speckle/bin"   # Add to shell config
# OR
ln -s /path/to/Speckle/bin/speckle /usr/local/bin/speckle  # Symlink

# Now use anywhere in your project:
speckle board                # Start kanban board
speckle doctor               # Run diagnostics
speckle doctor --fix         # Auto-fix issues
speckle status               # Show work status
speckle ready                # Show available work
speckle sync                 # Sync with git
speckle --help               # Show all commands
```

#### Installer Options

```bash
./install.sh [OPTIONS] [TARGET_DIR]

Options:
  --help, -h      Show help message
  --version, -v   Show version
  --check         Run health check only
  --uninstall     Remove Speckle from target
  --force         Skip prerequisite warnings
  --quiet, -q     Minimal output
```

### Workflow

```bash
# 1. Create specification (spec-kit)
/speckit.specify "Add user authentication"

# 2. Create plan (spec-kit)
/speckit.plan "Go, PostgreSQL, JWT"

# 3. Create tasks (spec-kit)
/speckit.tasks

# 4. Sync to beads (Speckle!)
/speckle.sync

# 5. Implement with tracking (Speckle!)
/speckle.implement

# 6. Check progress
/speckle.status
```

## Commands

| Command | Description |
|---------|-------------|
| `/speckle.sync` | Bidirectional sync between tasks.md and beads |
| `/speckle.implement` | Implement next ready task with progress tracking |
| `/speckle.loop` | Ralph-style iterative execution until all tasks complete |
| `/speckle.convoy` | Bundle related tasks for parallel execution |
| `/speckle.workers` | Manage ephemeral worker instances |
| `/speckle.mayor` | Autonomous coordinator mode (multi-agent orchestration) |
| `/speckle.status` | Show epic progress and health |
| `/speckle.progress` | Add manual progress note to current task |
| `/speckle.bugfix` | Start lightweight bugfix workflow |
| `/speckle.hotfix` | Start urgent hotfix workflow |
| `/speckle.issue` | Guided issue creation with GitHub + beads sync |
| `/speckle.triage` | Review and prioritize issues across GitHub and beads |
| `/speckle.doctor` | Diagnose installation and configuration issues |
| `/speckle.board` | Web-based kanban board for visualizing issues |

## Formulas

Speckle includes beads formulas for quickly starting new features or bugfixes:

### Create a Feature

```bash
bd formula speckle-feature "User Authentication"
```

This creates:
- A feature branch (e.g., `001-user-authentication`)
- Spec directory structure (`specs/001-user-authentication/`)
- Epic issue for tracking

**Example output:**
```
✅ Feature created: User Authentication

📁 Branch: 001-user-authentication
📂 Specs: specs/001-user-authentication/
🎫 Epic: speckle-abc

Next steps:
  /speckit.specify "Add user authentication"
```

### Create a Bugfix

```bash
bd formula speckle-bugfix "Login fails on mobile"
```

This creates:
- A bugfix branch (e.g., `fix-login-fails-on-mobile`)
- Bug issue with severity tracking

**Example output:**
```
✅ Bugfix created: Login fails on mobile

📁 Branch: fix-login-fails-on-mobile
🐛 Issue: speckle-xyz
⚠️  Severity: medium

Next steps:
  1. Reproduce the bug
  2. Write a failing test
  3. Fix and verify
  4. bd close speckle-xyz
```

## Bugfix Workflow

For quick bug fixes that don't require full spec-kit planning, use the bugfix commands:

### Standard Bugfix

```bash
/speckle.bugfix "Login fails on mobile Safari"
```

This creates a lightweight bugfix workflow:
- Creates a fix branch (e.g., `fix-login-fails-on-mobile-safari`)
- Creates a bug issue with severity tracking
- Skips spec-kit overhead for simple fixes

**Example output:**
```
✅ Bugfix branch created

📁 Branch: fix-login-fails-on-mobile-safari
🐛 Issue: speckle-abc
⚠️  Severity: medium

Workflow:
  1. Reproduce the bug
  2. Write a failing test
  3. Implement the fix
  4. Verify all tests pass
  5. bd close speckle-abc
```

### Urgent Hotfix

For critical production issues requiring immediate attention:

```bash
/speckle.hotfix "Payment processing timeout in checkout"
```

This creates an urgent hotfix workflow:
- Creates a hotfix branch (e.g., `hotfix-payment-processing-timeout`)
- Creates a critical-severity issue
- Prioritizes the fix in `bd ready`

**Example output:**
```
🚨 HOTFIX branch created

📁 Branch: hotfix-payment-processing-timeout
🐛 Issue: speckle-xyz
🔴 Severity: critical

Workflow:
  1. Reproduce the issue
  2. Implement minimal fix
  3. Verify fix works
  4. bd close speckle-xyz
  5. Merge immediately
```

### When to Use Each

| Scenario | Command |
|----------|---------|
| Feature development | `/speckit.specify` + `/speckle.sync` |
| Non-urgent bug | `/speckle.bugfix` |
| Production incident | `/speckle.hotfix` |

## Issue Creation Workflow

Create issues using a structured, guided approach that syncs with both GitHub Issues and beads:

### Guided Issue Creation

```bash
/speckle.issue "Add dark mode support"
```

This walks you through:
1. **Classify** - Select issue type (feature, bug, enhancement, chore, docs)
2. **Describe** - Add detailed description
3. **Prioritize** - Set severity (for bugs) or priority
4. **Link** - Optionally link to an existing spec or create a new one
5. **Create** - Generates GitHub issue with proper template
6. **Sync** - Automatically syncs to beads for unified tracking

**Example output:**
```
✅ Issue created successfully!

📋 Summary:
   Title: Add dark mode support
   Type: feature
   GitHub: https://github.com/user/repo/issues/42
   Beads: speckle-abc

🎯 Next steps:
   1. Create feature: bd formula speckle-feature "Add dark mode support"
   2. Develop spec: /speckit.specify
   3. Plan: /speckit.plan
   4. Tasks: /speckit.tasks
   5. Sync: /speckle.sync
```

### Issue Templates

Speckle includes GitHub Issue templates in `.github/ISSUE_TEMPLATE/`:

| Template | Use for |
|----------|---------|
| `feature.md` | New functionality requests |
| `bug.md` | Bug reports with severity tracking |
| `enhancement.md` | Improvements to existing features |
| `chore.md` | Maintenance and housekeeping tasks |
| `docs.md` | Documentation updates |

### Issue Triage

Review and prioritize issues across GitHub and beads:

```bash
/speckle.triage
```

**Dashboard view** shows issue counts and sync status:
```
📊 Speckle Issue Triage Dashboard
════════════════════════════════════════════════════════════

📌 GitHub Issues
   Open: 12
   Bugs: 3
   Features: 5

🔮 Beads Issues
   Open: 10
   In Progress: 2
   Blocked: 1

⚠️  Potential Issues:
   2 GitHub issue(s) not synced to beads
   Run: /speckle.triage --sync
```

**Options:**

```bash
/speckle.triage --sync    # Sync all open GitHub issues to beads
/speckle.triage --review  # Interactive review of issues
/speckle.triage --stale   # Find stale issues needing attention
```

### When to Use Each

| Scenario | Command |
|----------|---------|
| Quick bug report | `/speckle.bugfix` |
| Detailed issue (any type) | `/speckle.issue` |
| Review issue backlog | `/speckle.triage` |
| Complex feature | `/speckle.issue` → `/speckit.specify` |

## Kanban Board

Visualize your beads issues in a web-based kanban board:

```bash
# Using CLI (recommended)
speckle board

# Using Claude command
/speckle.board
```

This opens a browser with a 4-column kanban view:

| Column | Status | Description |
|--------|--------|-------------|
| BACKLOG | open | Ready to work on |
| IN PROGRESS | in_progress | Currently being worked |
| BLOCKED | blocked | Waiting on something |
| DONE | closed | Completed (last 15) |

**Options:**

```bash
# CLI usage
speckle board --port 3000         # Custom port
speckle board --no-browser        # Don't auto-open browser

# Claude command usage
/speckle.board --port 3000        # Custom port
/speckle.board --filter "v1.2.0"  # Filter by label
/speckle.board --no-browser       # Don't auto-open browser
/speckle.board --refresh 10       # 10 second refresh
```

**Features:**
- Priority color coding (P0-P4)
- Type badges (task, bug, feature, epic)
- Label filtering via dropdown
- Auto-refresh (default: 5 seconds)
- Responsive layout for tablet/mobile

## Ralph-Style Loop

Run autonomous implementation loops following the [Ralph pattern](https://github.com/snarktank/ralph) 
inspired by [Gastown](https://github.com/steveyegge/gastown):

```bash
# Run until all tasks complete (max 10 iterations)
/speckle.loop

# With options
/speckle.loop --max 20           # More iterations
/speckle.loop --verify           # Run DoD verifiers
/speckle.loop --dry-run          # Preview plan
/speckle.loop --continue         # Resume from progress
```

### How It Works

```
┌─────────────────────────────────────────────────────┐
│  SPECKLE LOOP (Ralph Pattern)                       │
├─────────────────────────────────────────────────────┤
│  1. Pick highest-priority ready task                │
│  2. Spawn fresh agent context (clean slate)         │
│  3. Implement single task                           │
│  4. Run quality checks (build, test)                │
│  5. Commit changes                                  │
│  6. Record learnings to progress.txt                │
│  7. Close task                                      │
│  8. Repeat until complete                           │
└─────────────────────────────────────────────────────┘
```

**Key principle:** Each iteration gets fresh context. Memory persists via:
- **Git history** - Commits from previous iterations
- **progress.txt** - Learnings and context
- **Bead status** - Which tasks are done

### Progress Persistence

Learnings are recorded in `.speckle/progress.txt`:

```markdown
---
## Iteration 1: Add user model
**Bead:** speckle-abc
**Completed:** 2026-02-09T19:30:00Z
**Result:** success

### Changes
- Commit: abc1234 feat(user): add user model
- Files changed: 3

### Learnings
- Used UUID for primary key (better for distributed systems)
- Added unique constraint on email
```

### DoD Verifiers

With `--verify`, the loop runs Definition of Done checks:

- Build passes (if Makefile exists)
- Tests pass (make test, npm test, composer test)
- No uncommitted changes

Only tasks passing all verifiers are closed.

### References

- [Gastown](https://github.com/steveyegge/gastown) - Multi-agent workspace manager (8.8k ⭐)
- [Ralph](https://github.com/snarktank/ralph) - Autonomous AI agent loop (9.8k ⭐)

## Multi-Agent Orchestration

Speckle implements the full [Gastown pattern](https://github.com/steveyegge/gastown) for coordinating 
multiple AI agents working in parallel on the same codebase.

### Convoy System

Bundle related tasks for assignment to workers:

```bash
# Create a convoy from filtered tasks
/speckle.convoy --create "auth-flow" --filter phase:auth

# View convoy status
/speckle.convoy --status

# List all convoys
/speckle.convoy --list
```

**Convoy principles:**
- Tasks that touch the same files go in the same convoy
- A convoy is the unit of work assigned to a worker
- Convoys prevent merge conflicts by grouping related changes

### Workers (Ephemeral Polecats)

Manage isolated worker instances via git worktrees:

```bash
# Spawn a new worker
/speckle.workers --spawn

# Assign a convoy to a worker
/speckle.workers --assign worker-01 convoy-auth

# Check worker status
/speckle.workers --status

# Destroy a worker (after convoy complete)
/speckle.workers --destroy worker-01
```

**Worker lifecycle:**
1. **Spawn** - Creates git worktree in `.speckle/workers/worker-XX`
2. **Assign** - Worker receives a convoy of tasks
3. **Execute** - Worker implements tasks in isolated checkout
4. **Complete** - Changes are committed and pushed
5. **Destroy** - Worktree is cleaned up

### Mayor Mode

Autonomous coordinator that orchestrates multiple workers:

```bash
# Start mayor mode (autonomous orchestration)
/speckle.mayor

# With limits
/speckle.mayor --max-workers 3 --dry-run
```

**Mayor responsibilities:**
- **Decomposition** - Breaks work into right-sized convoys
- **Spawning** - Creates workers as needed
- **Assignment** - Assigns convoys avoiding conflicts
- **Monitoring** - Tracks progress across all workers
- **Completion** - Knows when to stop

**Key principle:** The mayor never writes code directly. It only coordinates.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  MAYOR (Coordinator)                                        │
│  - Never writes code directly                               │
│  - Spawns workers, assigns convoys                          │
│  - Monitors progress, handles conflicts                     │
├─────────────────────────────────────────────────────────────┤
│  CONVOYS (Work Bundles)                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │ convoy-1│  │ convoy-2│  │ convoy-3│                     │
│  │ 3 tasks │  │ 2 tasks │  │ 5 tasks │                     │
│  └─────────┘  └─────────┘  └─────────┘                     │
├─────────────────────────────────────────────────────────────┤
│  WORKERS (Ephemeral Polecats)                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │worker-01│  │worker-02│  │worker-03│                     │
│  │worktree │  │worktree │  │worktree │                     │
│  │isolated │  │isolated │  │isolated │                     │
│  └─────────┘  └─────────┘  └─────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

### Gastown Terminology

| Gastown Term | Speckle Equivalent | Description |
|--------------|-------------------|-------------|
| Town | Repository | The workspace |
| Mayor | /speckle.mayor | Coordinator (never codes) |
| Convoy | /speckle.convoy | Work bundles |
| Polecat | /speckle.workers | Ephemeral workers |
| Hook | .speckle/workers/ | Git worktree persistence |
| Bead | beads | Same! |

## Troubleshooting

Use the doctor command to diagnose issues:

```bash
# Using CLI (recommended)
speckle doctor

# Using Claude command
/speckle.doctor
```

**Example output:**
```
🩺 Speckle Doctor
════════════════════════════════════════════════════════════

📦 Prerequisites

  ✅ git: 2.42.0
  ✅ gh: 2.40.0
     └─ Authenticated
  ✅ bd: installed
  ℹ️  specify: NOT FOUND (optional)

📁 Directory Structure

  ✅ .speckle/
     └─ scripts/ (4 files)
     └─ templates/ (2 files)
  ✅ .claude/commands/ (7 speckle commands)
  ✅ .beads/
     └─ config.toml exists

📊 Diagnosis Summary

  🎉 All checks passed! Speckle is healthy.
```

Use `--fix` to attempt automatic repairs:

```bash
# Using CLI
speckle doctor --fix

# Using Claude command
/speckle.doctor --fix
```

## How It Works

```
Spec-Kit                    Speckle                     Beads
─────────                   ───────                     ─────
spec.md    ─────────┐
plan.md    ─────────┼──→  /speckle.sync  ──────→  issues.jsonl
tasks.md   ─────────┘         ↕                      ↕
                         .speckle-mapping.json    bd ready
                              ↕                    bd close
                         /speckle.implement  ←──  bd comments
```

## Memory Across Sessions

Every implementation is automatically recorded as a bead comment:

```bash
# View implementation history for a task
bd comments <issue-id>

# Example output:
# ## Implementation Complete
# **Task:** T001
# **Actor:** claude
# **Time:** 2026-02-09T19:30:00Z
# 
# ### Changes
# - Lines added: +150
# - Lines removed: -20
# - Files changed: 3

# Add manual progress notes during implementation
/speckle.progress "Chose Redis over Memcached for caching"

# Check overall feature status
/speckle.status
```

This means every new session can pick up exactly where the last one left off.

### Filtering by Labels

When Speckle syncs tasks to beads, labels are applied automatically based on spec metadata.
Use `bd list --label` to filter tasks:

```bash
# Filter by phase (from spec headers)
bd list --label phase:foundation
bd list --label phase:mvp

# Filter by feature (from branch name)
bd list --label feature:auth

# Filter by story  
bd list --label story:us1

# Combine multiple labels (AND - must have ALL)
bd list --label phase:foundation --label docs

# OR filtering (must have AT LEAST ONE)
bd list --label-any phase:foundation,phase:mvp

# Short form
bd list -l docs
```

Common label patterns:
- `phase:<phase-name>` - Development phase from spec headers
- `story:<story-id>` - User story association
- `feature:<name>` - Feature from branch name
- `docs` - Documentation tasks
- `v0.3.0` - Version/milestone labels

## Self-Hosted Development

Speckle is developed using Speckle! From v0.2.0 onwards, each version is built 
using the previous version, validating the tool while improving it.

See [SELF-HOSTING.md](docs/SELF-HOSTING.md) for details.

## License

MIT License - See [LICENSE](LICENSE)

## Acknowledgments

- [GitHub Spec Kit](https://github.com/github/spec-kit) - Spec-driven development methodology
- [Beads](https://github.com/steveyegge/beads) - AI-native issue tracking

---

*Speckle: Where specifications meet memory* 🔮
