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
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

# Initialize in your project
specify init . --ai claude
bd init
```

### Install Speckle

```bash
# Clone and install
git clone https://github.com/YOUR-USERNAME/Speckle.git /tmp/speckle
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

Every implementation is recorded:

```bash
# View implementation history
bd comments <issue-id>

# See what was done
bd show <issue-id>  # Description includes spec context
```

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
