---
description: Implement the next ready task with progress tracking and compliance checks
---

# Speckle Implement

Implements the next available task from beads, with automatic progress tracking via comments.

## Arguments

```text
$ARGUMENTS
```

Options:
- No args: Auto-select first ready task
- Task ID (e.g., `T005`): Implement specific task
- `--auto`: Auto-close on success and continue to next
- `--dry-run`: Show what would be done without executing

## Startup Checks

```bash
# Verify beads is running and has issues
if ! bd ready &>/dev/null; then
    echo "❌ Beads not available or no issues synced"
    echo "   Run /speckle.sync first"
    exit 1
fi

# Find feature mapping
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
PREFIX="${BRANCH:0:3}"
FEATURE_DIR=$(find specs -maxdepth 1 -type d -name "${PREFIX}-*" 2>/dev/null | head -1)
MAPPING_FILE="$FEATURE_DIR/.speckle-mapping.json"

if [ ! -f "$MAPPING_FILE" ]; then
    echo "❌ Speckle mapping not found"
    echo "   Run /speckle.sync first"
    exit 1
fi

echo "✅ Speckle ready"
echo "📁 Feature: $FEATURE_DIR"
```

## Select Task

```javascript
const mapping = JSON.parse(fs.readFileSync(MAPPING_FILE))
const args = $ARGUMENTS.trim()

let selectedTask = null
let selectedBead = null

if (args && args.match(/^T\d{3}$/)) {
    // Specific task requested
    const taskId = args
    if (!mapping.tasks[taskId]) {
        console.error(`❌ Task ${taskId} not found in mapping`)
        process.exit(1)
    }
    selectedBead = mapping.tasks[taskId].beadId
    selectedTask = taskId
} else {
    // Auto-select from ready tasks
    const readyOutput = exec('bd ready --json')
    const readyIssues = JSON.parse(readyOutput)
    
    // Find first ready issue that's in our mapping
    for (const issue of readyIssues) {
        for (const [taskId, info] of Object.entries(mapping.tasks)) {
            if (info.beadId === issue.id) {
                selectedBead = issue.id
                selectedTask = taskId
                break
            }
        }
        if (selectedTask) break
    }
}

if (!selectedTask) {
    console.log('✅ No ready tasks! All work complete or blocked.')
    console.log('')
    console.log('Check status with: bd list --status open')
    console.log('Check blockers with: bd blocked')
    process.exit(0)
}

console.log(`🎯 Selected: ${selectedTask} (${selectedBead})`)
```

## Claim Task

**Critical: Mark as in_progress immediately to prevent race conditions**

```bash
echo "🔒 Claiming task..."
bd update $SELECTED_BEAD --status in_progress

# Verify claim succeeded
STATUS=$(bd show $SELECTED_BEAD --json | jq -r '.status')
if [ "$STATUS" != "in_progress" ]; then
    echo "❌ Failed to claim task (may already be claimed)"
    exit 1
fi

echo "✅ Task claimed"
```

## Load Task Context

```bash
# Get full issue details
ISSUE_JSON=$(bd show $SELECTED_BEAD --json)
TITLE=$(echo "$ISSUE_JSON" | jq -r '.title')
DESCRIPTION=$(echo "$ISSUE_JSON" | jq -r '.description')
LABELS=$(echo "$ISSUE_JSON" | jq -r '.labels | join(", ")')

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📋 $TITLE"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "$DESCRIPTION"
echo ""
echo "Labels: $LABELS"
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

After implementation, I will:
1. Record implementation details as a bead comment
2. Run compliance checks
3. Close the task (or report issues)
```

## Post-Implementation: Record Progress

After the agent completes implementation:

```bash
# Source comment helpers
source ".speckle/scripts/comments.sh"

# Gather implementation details using helper function
DIFF_OUTPUT=$(get_diff_stats HEAD~1)
FILES_CHANGED=$(echo "$DIFF_OUTPUT" | head -n -2)
LINES_ADDED=$(echo "$DIFF_OUTPUT" | tail -2 | head -1)
LINES_REMOVED=$(echo "$DIFF_OUTPUT" | tail -1)

# Format completion comment using helper
COMMENT=$(format_completion_comment "$SELECTED_TASK" "$SELECTED_BEAD" "$FILES_CHANGED" "$LINES_ADDED" "$LINES_REMOVED")

# Add comment safely (won't fail the workflow if beads is unavailable)
add_comment_safe "$SELECTED_BEAD" "$COMMENT"
```

## Compliance Check

```bash
# Check commit size
TOTAL_LINES=$((LINES_ADDED + LINES_REMOVED))
if [ "$TOTAL_LINES" -gt 600 ]; then
    echo "⚠️  Commit size ($TOTAL_LINES lines) exceeds recommended 600"
fi

# Check for test files
if ! echo "$FILES_CHANGED" | grep -q "_test\.\|\.test\.\|spec\."; then
    echo "⚠️  No test files in commit - verify TDD compliance"
fi
```

## Close Task

```bash
# Ask for confirmation unless --auto
if [[ "$ARGUMENTS" != *"--auto"* ]]; then
    echo ""
    echo "Ready to close task $SELECTED_TASK?"
    echo "Press Enter to close, or Ctrl+C to cancel"
    read
fi

bd close $SELECTED_BEAD
echo "✅ Task closed: $SELECTED_TASK"

# Sync mapping
bd sync

# Show next ready task
echo ""
echo "📋 Next ready tasks:"
bd ready | head -5
```
