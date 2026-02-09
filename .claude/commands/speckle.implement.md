---
description: Implement the next ready task with progress tracking and compliance checks
---

# Speckle Implement

Implements the next available task from beads, with automatic progress tracking via comments.

## Arguments

```text
$ARGUMENTS
```

**Usage**: `/speckle.implement [task-id] [--auto] [--dry-run]`

| Argument | Description |
|----------|-------------|
| `<task-id>` | Optional: Specific task (e.g., `T005` or `speckle-abc`) |
| `--auto` | Auto-close on success (no confirmation) |
| `--dry-run` | Show what would be done without executing |

**Examples**:
```bash
# Auto-select first ready task
/speckle.implement

# Implement specific task
/speckle.implement T005

# Auto mode (closes automatically)
/speckle.implement --auto
```

## Startup Checks

```bash
# Source helpers
source ".speckle/scripts/common.sh"
source ".speckle/scripts/comments.sh"

# Parse arguments
AUTO_MODE=""
DRY_RUN=""
TASK_ARG=""

for arg in $ARGUMENTS; do
    case "$arg" in
        --auto) AUTO_MODE="true" ;;
        --dry-run) DRY_RUN="true" ;;
        T[0-9][0-9][0-9]) TASK_ARG="$arg" ;;
        speckle-*) TASK_ARG="$arg" ;;
    esac
done

# Verify beads is running and has issues
if ! bd ready &>/dev/null; then
    log_error "Beads not available or no issues synced"
    echo "   Run /speckle.sync first"
    exit 1
fi

# Find feature mapping
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
PREFIX="${BRANCH:0:3}"
FEATURE_DIR=$(find specs -maxdepth 1 -type d -name "${PREFIX}-*" 2>/dev/null | head -1)
MAPPING_FILE="$FEATURE_DIR/.speckle-mapping.json"

# Mapping is optional - can work with any bead
if [ -f "$MAPPING_FILE" ]; then
    echo "📁 Feature: $FEATURE_DIR"
fi

log_success "Speckle ready"
```

## Select Task

```bash
SELECTED_TASK=""
SELECTED_BEAD=""

if [ -n "$TASK_ARG" ]; then
    # Specific task requested
    if [[ "$TASK_ARG" =~ ^T[0-9]{3}$ ]]; then
        # Task ID like T005 - look up in mapping
        if [ -f "$MAPPING_FILE" ]; then
            SELECTED_BEAD=$(jq -r ".tasks[\"$TASK_ARG\"].beadId // empty" "$MAPPING_FILE" 2>/dev/null)
            if [ -n "$SELECTED_BEAD" ]; then
                SELECTED_TASK="$TASK_ARG"
            else
                log_error "Task $TASK_ARG not found in mapping"
                exit 1
            fi
        else
            log_error "No mapping file - cannot resolve task ID $TASK_ARG"
            exit 1
        fi
    else
        # Bead ID like speckle-abc - use directly
        SELECTED_BEAD="$TASK_ARG"
        # Try to find task ID from mapping
        if [ -f "$MAPPING_FILE" ]; then
            SELECTED_TASK=$(jq -r ".tasks | to_entries[] | select(.value.beadId == \"$SELECTED_BEAD\") | .key" "$MAPPING_FILE" 2>/dev/null | head -1)
        fi
        [ -z "$SELECTED_TASK" ] && SELECTED_TASK="$SELECTED_BEAD"
    fi
else
    # Auto-select from ready tasks
    READY_JSON=$(bd ready --json 2>/dev/null || echo "[]")
    
    if [ -f "$MAPPING_FILE" ]; then
        # Find first ready issue that's in our mapping
        for bead_id in $(echo "$READY_JSON" | jq -r '.[].id' 2>/dev/null); do
            TASK_ID=$(jq -r ".tasks | to_entries[] | select(.value.beadId == \"$bead_id\") | .key" "$MAPPING_FILE" 2>/dev/null | head -1)
            if [ -n "$TASK_ID" ]; then
                SELECTED_BEAD="$bead_id"
                SELECTED_TASK="$TASK_ID"
                break
            fi
        done
    fi
    
    # If no mapping match, just take first ready issue
    if [ -z "$SELECTED_BEAD" ]; then
        SELECTED_BEAD=$(echo "$READY_JSON" | jq -r '.[0].id // empty' 2>/dev/null)
        SELECTED_TASK="$SELECTED_BEAD"
    fi
fi

if [ -z "$SELECTED_BEAD" ]; then
    log_success "No ready tasks! All work complete or blocked."
    echo ""
    echo "Check status with: bd list --status open"
    echo "Check blockers with: bd blocked"
    exit 0
fi

echo ""
echo "🎯 Selected: $SELECTED_TASK ($SELECTED_BEAD)"
```

## Claim Task (Atomic)

Uses atomic claim to prevent race conditions:

```bash
echo ""
echo "🔒 Claiming task..."

if [ -n "$DRY_RUN" ]; then
    log_info "[DRY RUN] Would claim $SELECTED_BEAD"
else
    # Use atomic --claim flag (fails if already claimed by another agent)
    if ! bd update "$SELECTED_BEAD" --claim 2>/dev/null; then
        log_error "Failed to claim task - may already be claimed by another agent"
        echo ""
        echo "Check who claimed it: bd show $SELECTED_BEAD"
        echo "Find other ready work: bd ready"
        exit 1
    fi
    
    log_success "Task claimed"
fi
```

## Load Task Context

```bash
# Get full issue details
ISSUE_JSON=$(bd show "$SELECTED_BEAD" --json 2>/dev/null || echo '{}')
TITLE=$(echo "$ISSUE_JSON" | jq -r '.title // "Unknown"')
DESCRIPTION=$(echo "$ISSUE_JSON" | jq -r '.description // ""')
LABELS=$(echo "$ISSUE_JSON" | jq -r '.labels // [] | join(", ")')

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📋 $TITLE"
echo "═══════════════════════════════════════════════════════════"
echo ""
if [ -n "$DESCRIPTION" ]; then
    echo "$DESCRIPTION"
    echo ""
fi
if [ -n "$LABELS" ]; then
    echo "Labels: $LABELS"
fi
echo "═══════════════════════════════════════════════════════════"
echo ""
```

## Implementation Guidelines

Present implementation guidance to the agent:

```markdown
## Your Task

Implement the task described above following these principles:

### 1. Test First (TDD)
- Write failing test first
- Implement minimum code to pass
- Refactor if needed

### 2. Small Commits
- Target 300-600 lines changed
- One logical change per commit
- Clear commit messages: `type(scope): description`

### 3. Constitutional Compliance
- Functions < 50 lines
- SOLID principles
- Error handling with context
- No hardcoded secrets

### 4. Documentation
- Update relevant docs
- Add code comments for complex logic
- Update README if user-facing changes

## When Complete

After implementation, the workflow will:
1. Record implementation details as a bead comment
2. Run compliance checks
3. Close the task (with --auto) or prompt for confirmation
```

## Post-Implementation: Record Progress

After the agent completes implementation:

```bash
if [ -n "$DRY_RUN" ]; then
    log_info "[DRY RUN] Would record progress for $SELECTED_TASK"
else
    # Gather implementation details using helper function (returns JSON)
    DIFF_JSON=$(get_diff_stats HEAD~1)
    FILES_CHANGED=$(parse_diff_stats "$DIFF_JSON" "files")
    LINES_ADDED=$(parse_diff_stats "$DIFF_JSON" "added")
    LINES_REMOVED=$(parse_diff_stats "$DIFF_JSON" "removed")
    
    # Format completion comment using helper
    COMMENT=$(format_completion_comment "$SELECTED_TASK" "$SELECTED_BEAD" "$FILES_CHANGED" "$LINES_ADDED" "$LINES_REMOVED")
    
    # Add comment safely (won't fail the workflow if beads is unavailable)
    add_comment_safe "$SELECTED_BEAD" "$COMMENT"
fi
```

## Compliance Check

```bash
if [ -z "$DRY_RUN" ]; then
    # Check commit size
    TOTAL_LINES=$((LINES_ADDED + LINES_REMOVED))
    if [ "$TOTAL_LINES" -gt 600 ]; then
        log_warn "Commit size ($TOTAL_LINES lines) exceeds recommended 600"
    fi
    
    # Check for test files
    if [ -n "$FILES_CHANGED" ] && ! echo "$FILES_CHANGED" | grep -qE "_test\.|\.test\.|spec\."; then
        log_warn "No test files in commit - verify TDD compliance"
    fi
fi
```

## Close Task

```bash
if [ -n "$DRY_RUN" ]; then
    log_info "[DRY RUN] Would close $SELECTED_BEAD"
    exit 0
fi

# Auto mode skips confirmation
if [ -z "$AUTO_MODE" ]; then
    echo ""
    echo "Task $SELECTED_TASK is ready to close."
    echo ""
    echo "To close: bd close $SELECTED_BEAD"
    echo "To continue working: (task remains in_progress)"
    echo ""
    echo "Use --auto flag to close automatically."
else
    bd close "$SELECTED_BEAD" -r "Completed via speckle.implement"
    log_success "Task closed: $SELECTED_TASK"
    
    # Sync mapping if available
    if [ -f "$MAPPING_FILE" ]; then
        bd sync 2>/dev/null || true
    fi
    
    # Show next ready task
    echo ""
    echo "📋 Next ready tasks:"
    bd ready 2>/dev/null | head -5 || echo "   No more ready tasks"
fi
```
