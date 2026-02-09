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
# Clone and install
git clone https://github.com/JulianDouma/Speckle.git /tmp/speckle
/tmp/speckle/install.sh /path/to/your/project

# Restart your AI agent to load commands
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
| `/speckle.status` | Show epic progress and health |
| `/speckle.progress` | Add manual progress note to current task |

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
