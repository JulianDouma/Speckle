# Speckle Hooks System - Deep Analysis

## Overview

A hooks system allows users to run custom scripts before or after Speckle commands, enabling:
- Automation of repetitive tasks
- Integration with external tools
- Enforcement of team workflows
- Custom validation and quality gates

## Inspiration: How Other Tools Handle Hooks

### Git Hooks
```
.git/hooks/
├── pre-commit      # Before commit
├── post-commit     # After commit
├── pre-push        # Before push
└── post-merge      # After merge
```
- Executable scripts in `.git/hooks/`
- Named by lifecycle event
- Exit code determines success/failure

### npm Scripts
```json
{
  "scripts": {
    "pretest": "npm run lint",
    "test": "jest",
    "posttest": "npm run coverage"
  }
}
```
- Convention: `pre<command>` and `post<command>`
- Defined in configuration file
- Automatic execution

### Husky (Modern Git Hooks)
```
.husky/
├── pre-commit
├── commit-msg
└── _/husky.sh
```
- Dedicated directory
- Shell scripts with shebang
- Easy to version control

### Beads Hooks
```bash
bd hooks install  # Installs git hooks
bd hooks list     # Shows status
```
- Integrates with git hooks
- Handles sync lifecycle
- Automatic JSONL management

## Proposed Speckle Hooks

### Hook Points

| Command | Pre-Hook | Post-Hook | Use Cases |
|---------|----------|-----------|-----------|
| `sync` | `pre-sync` | `post-sync` | Validate specs, notify team |
| `implement` | `pre-implement` | `post-implement` | Run tests, format code |
| `status` | - | `post-status` | Export metrics |
| `progress` | - | `post-progress` | Log to external system |
| `bugfix` | `pre-bugfix` | `post-bugfix` | Validate bug ID, run regression |
| `hotfix` | `pre-hotfix` | `post-hotfix` | Alert on-call, verify tests |
| `board` | `pre-board` | - | Check dependencies |
| `doctor` | - | `post-doctor` | Report health metrics |

### Most Valuable Hooks

**Tier 1 (High Value):**
1. `pre-implement` - Quality gates before work starts
2. `post-implement` - Tests, formatting, notifications
3. `post-sync` - External integrations

**Tier 2 (Medium Value):**
4. `pre-sync` - Spec validation
5. `pre-bugfix` / `pre-hotfix` - Workflow enforcement

**Tier 3 (Nice to Have):**
6. `post-status` - Metrics export
7. `post-progress` - Activity logging

## Directory Structure

### Option A: Dedicated Hooks Directory
```
.speckle/
├── hooks/
│   ├── pre-sync.sh
│   ├── post-sync.sh
│   ├── pre-implement.sh
│   ├── post-implement.py
│   └── post-bugfix.sh
├── scripts/
│   └── board.py
└── config.toml
```

### Option B: Configuration-Based
```toml
# .speckle/config.toml
[hooks]
pre-sync = "npm run lint:specs"
post-sync = "./scripts/notify-slack.sh"
pre-implement = ["npm test", "npm run typecheck"]
post-implement = "npm run format"
```

### Option C: Hybrid (Recommended)
```
.speckle/
├── hooks/
│   ├── pre-implement.sh    # Complex logic
│   └── post-sync.py        # Python script
├── config.toml             # Simple commands
└── scripts/
```

```toml
# .speckle/config.toml
[hooks]
# Simple commands inline
pre-sync = "npm run validate:specs"

# Reference external scripts
post-implement = ".speckle/hooks/post-implement.sh"

# Multiple commands (run in sequence)
pre-bugfix = [
  "git fetch origin",
  "npm test"
]
```

## Hook Execution Model

### Lifecycle

```
┌──────────────────────────────────────────────────────────┐
│                    /speckle.implement                     │
├──────────────────────────────────────────────────────────┤
│  1. Load config.toml                                      │
│  2. Check for pre-implement hook                          │
│  3. Execute pre-implement hook                            │
│     └─ If exit code != 0: ABORT                          │
│  4. Run main implement logic                              │
│  5. Check for post-implement hook                         │
│  6. Execute post-implement hook                           │
│     └─ If exit code != 0: WARN (don't abort)             │
│  7. Complete                                              │
└──────────────────────────────────────────────────────────┘
```

### Exit Code Behavior

| Hook Type | Exit 0 | Exit Non-0 |
|-----------|--------|------------|
| `pre-*` | Continue | **Abort command** |
| `post-*` | Continue | Warn but continue |

### Environment Variables

Hooks receive context via environment:

```bash
# Available in all hooks
SPECKLE_COMMAND="implement"    # Current command
SPECKLE_HOOK="pre-implement"   # Hook being run
SPECKLE_DIR=".speckle"         # Speckle directory
SPECKLE_ROOT="/path/to/repo"   # Repository root

# Command-specific
SPECKLE_TASK_ID="speckle-abc"  # For implement
SPECKLE_TASK_TITLE="T001: ..." # For implement
SPECKLE_FEATURE="008-kanban"   # Current feature
SPECKLE_BRANCH="008-kanban"    # Current branch

# For sync
SPECKLE_TASKS_FILE="specs/008/tasks.md"
SPECKLE_SYNC_DIRECTION="to-beads"  # or "from-beads"

# For bugfix/hotfix
SPECKLE_BUG_ID="BUG-123"
SPECKLE_SEVERITY="critical"
```

## Use Case Examples

### 1. Run Tests Before Implementation
```bash
#!/bin/bash
# .speckle/hooks/pre-implement.sh

echo "🧪 Running tests before implementation..."
npm test --silent

if [ $? -ne 0 ]; then
    echo "❌ Tests failed! Fix before implementing."
    exit 1
fi

echo "✅ Tests passed"
```

### 2. Format Code After Implementation
```bash
#!/bin/bash
# .speckle/hooks/post-implement.sh

echo "🎨 Formatting code..."
npm run format

echo "📝 Running linter..."
npm run lint --fix

# Stage formatted files
git add -u
```

### 3. Notify Slack After Sync
```python
#!/usr/bin/env python3
# .speckle/hooks/post-sync.py

import os
import requests

webhook = os.environ.get('SLACK_WEBHOOK')
feature = os.environ.get('SPECKLE_FEATURE')
branch = os.environ.get('SPECKLE_BRANCH')

if webhook:
    requests.post(webhook, json={
        "text": f"📋 Speckle synced: {feature} on {branch}"
    })
```

### 4. Validate Spec Format Before Sync
```bash
#!/bin/bash
# .speckle/hooks/pre-sync.sh

TASKS_FILE="$SPECKLE_TASKS_FILE"

# Check tasks.md exists
if [ ! -f "$TASKS_FILE" ]; then
    echo "❌ tasks.md not found"
    exit 1
fi

# Validate task format
if ! grep -qE '^\- \[[ x]\] T[0-9]{3}' "$TASKS_FILE"; then
    echo "❌ Invalid task format in tasks.md"
    echo "   Expected: - [ ] T001 Description"
    exit 1
fi

echo "✅ Spec format valid"
```

### 5. Enforce Branch Naming for Bugfix
```bash
#!/bin/bash
# .speckle/hooks/pre-bugfix.sh

BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [[ ! "$BRANCH" =~ ^fix- ]] && [[ ! "$BRANCH" =~ ^bugfix- ]]; then
    echo "❌ Must be on a fix/* or bugfix/* branch"
    echo "   Current: $BRANCH"
    exit 1
fi
```

### 6. Update Metrics Dashboard
```toml
# .speckle/config.toml
[hooks]
post-status = "curl -X POST https://metrics.example.com/speckle -d @-"
```

## CLI Interface

### Managing Hooks

```bash
# List configured hooks
speckle hooks list

# Output:
# Hook             Source                    Status
# ─────────────────────────────────────────────────
# pre-sync         config.toml               ✓ enabled
# post-sync        .speckle/hooks/post.sh    ✓ enabled
# pre-implement    (not configured)          ○ disabled
# post-implement   config.toml               ✓ enabled

# Run a hook manually (for testing)
speckle hooks run pre-implement

# Enable/disable hooks temporarily
speckle hooks disable post-sync
speckle hooks enable post-sync

# Create hook from template
speckle hooks init pre-implement
# Creates .speckle/hooks/pre-implement.sh with template
```

### Hook Templates

```bash
speckle hooks init pre-implement
```

Creates:
```bash
#!/bin/bash
# Speckle Hook: pre-implement
# Runs before /speckle.implement
#
# Available environment variables:
#   SPECKLE_TASK_ID    - Issue ID being implemented
#   SPECKLE_TASK_TITLE - Task title
#   SPECKLE_FEATURE    - Current feature name
#   SPECKLE_BRANCH     - Current git branch
#
# Exit 0 to continue, non-zero to abort.

set -e

echo "🪝 Running pre-implement hook..."

# Add your commands here:
# npm test
# npm run lint

echo "✅ Hook completed"
```

## Configuration Schema

```toml
# .speckle/config.toml

[hooks]
# String: single command
pre-sync = "npm run validate"

# Array: multiple commands (sequential)
post-implement = [
    "npm run format",
    "npm run lint --fix",
    "git add -u"
]

# Object: advanced configuration
[hooks.pre-bugfix]
command = ".speckle/hooks/pre-bugfix.sh"
timeout = 30  # seconds
continue_on_error = false

[hooks.post-sync]
command = "python3 .speckle/hooks/notify.py"
env = { SLACK_CHANNEL = "#dev" }
async = true  # Don't wait for completion
```

## Implementation Phases

### Phase 1: Core Infrastructure
- [ ] Hook discovery (config.toml + hooks/ directory)
- [ ] Hook execution engine
- [ ] Environment variable injection
- [ ] Exit code handling

### Phase 2: CLI Integration
- [ ] `speckle hooks list`
- [ ] `speckle hooks run <hook>`
- [ ] `speckle hooks init <hook>`

### Phase 3: Command Integration
- [ ] Integrate hooks into sync command
- [ ] Integrate hooks into implement command
- [ ] Integrate hooks into bugfix/hotfix commands

### Phase 4: Advanced Features
- [ ] Async hooks (post-* only)
- [ ] Hook timeouts
- [ ] Conditional hooks (run only if condition met)
- [ ] Hook chaining (one hook triggers another)

## Security Considerations

1. **Script execution** - Only run scripts from `.speckle/` directory
2. **Environment leakage** - Don't pass sensitive env vars to hooks
3. **Timeout enforcement** - Prevent runaway hooks
4. **Audit logging** - Log hook executions for debugging

## Comparison with Alternatives

| Approach | Pros | Cons |
|----------|------|------|
| Speckle Hooks | Native integration, context-aware | Another system to learn |
| Git Hooks | Already familiar | No Speckle context |
| npm scripts | Simple, well-known | Requires npm/package.json |
| Makefile | Universal | Less integration |
| CI/CD only | Centralized | Not local, slower feedback |

**Recommendation:** Speckle hooks complement (not replace) other approaches. Use git hooks for git operations, Speckle hooks for Speckle-specific workflows.

## Summary

A hooks system would make Speckle significantly more extensible and allow teams to:
- Enforce quality gates before implementation
- Automate post-task cleanup (formatting, testing)
- Integrate with external tools (Slack, metrics, CI)
- Customize workflows without modifying core commands

The recommended approach is a **hybrid system** with:
1. `.speckle/hooks/` directory for complex scripts
2. `.speckle/config.toml` for simple inline commands
3. Rich environment variables for context
4. Clear exit code semantics (pre-hooks can abort)
