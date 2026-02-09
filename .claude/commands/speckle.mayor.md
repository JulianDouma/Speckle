---
description: Mayor mode - autonomous coordinator for multi-agent orchestration
---

# Speckle Mayor

The Mayor is an autonomous coordinator that orchestrates work across multiple workers.
Inspired by Gastown's MEOW (Mayor-Enhanced Orchestration Workflow) pattern.

**Key Principle:** The Mayor delegates but never implements directly.

## Arguments

```text
$ARGUMENTS
```

Options:
- No args: Enter interactive mayor mode
- `--plan <goal>` - Create execution plan for a goal
- `--execute` - Execute the current plan
- `--status` - Show orchestration status
- `--auto` - Fully autonomous mode (requires confirmation)

## The MEOW Pattern

```
┌─────────────────────────────────────────────────────────────┐
│  MEOW: Mayor-Enhanced Orchestration Workflow                │
├─────────────────────────────────────────────────────────────┤
│  1. Analyze goal → Break into tasks                         │
│  2. Create convoy → Bundle related work                     │
│  3. Spawn workers → Isolated git worktrees                  │
│  4. Assign tasks → Distribute to workers                    │
│  5. Monitor → Track progress, handle issues                 │
│  6. Merge → Integrate completed work                        │
│  7. Report → Summary for human review                       │
└─────────────────────────────────────────────────────────────┘
```

## Startup

```bash
source ".speckle/scripts/common.sh"
source ".speckle/scripts/convoy.sh"
source ".speckle/scripts/workers.sh"
source ".speckle/scripts/loop.sh"

# State file
MAYOR_STATE=".speckle/mayor-state.json"

ARGS="$ARGUMENTS"
```

## Interactive Mayor Mode

```markdown
## 🎩 Mayor Mode Activated

I am now in **Mayor Mode** - an autonomous coordinator following the MEOW pattern.

**My responsibilities:**
1. Analyze goals and create execution plans
2. Create convoys to bundle related work
3. Spawn workers for parallel execution
4. Delegate tasks (I never implement directly)
5. Monitor progress and handle issues
6. Report summaries for human review

**What I will NOT do:**
- Write code directly
- Make implementation decisions
- Commit changes myself

### Current State

Let me check the current workspace state:

```bash
# Check ready tasks
bd ready | head -10

# Check existing convoys
ls -la .speckle/convoys/*.json 2>/dev/null | wc -l || echo "0"

# Check active workers
ls -la .speckle/workers/*.json 2>/dev/null | wc -l || echo "0"
```

### What would you like me to orchestrate?

Options:
1. **Plan** - "Plan how to implement [goal]"
2. **Execute** - "Execute the pending tasks"
3. **Status** - "Show current orchestration status"
4. **Delegate** - "Assign [task] to a worker"

Tell me your goal, and I'll create an execution plan.
```

## Planning Mode

When given a goal, create an execution plan:

```markdown
## 📋 Execution Plan

**Goal:** {USER_GOAL}

### Analysis

I've analyzed this goal and identified the following work breakdown:

1. **Prerequisites** - What needs to exist first
2. **Core Tasks** - The main implementation work
3. **Verification** - Testing and validation
4. **Documentation** - Updates needed

### Proposed Convoy Structure

```
Convoy: {GOAL_NAME}
├── Phase 1: Foundation
│   ├── Task A (prerequisite)
│   └── Task B (prerequisite)
├── Phase 2: Implementation
│   ├── Task C (can parallelize)
│   ├── Task D (can parallelize)
│   └── Task E (depends on C, D)
└── Phase 3: Verification
    ├── Task F (testing)
    └── Task G (documentation)
```

### Worker Allocation

| Worker | Tasks | Status |
|--------|-------|--------|
| polecat-1 | A, B | Spawn when ready |
| polecat-2 | C | After Phase 1 |
| polecat-3 | D | After Phase 1 |
| polecat-4 | E, F, G | After C, D complete |

### Estimated Effort

- Total tasks: X
- Parallelizable: Y
- Sequential: Z
- Estimated time: ~N iterations

### Approval Required

Do you approve this execution plan?

- **Yes** - I'll create the convoy and begin orchestration
- **Modify** - Tell me what to change
- **No** - I'll discard this plan
```

## Execution Mode

```bash
if [[ "$ARGS" == *"--execute"* ]]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "🎩 Mayor Execution Mode"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    # Load or create state
    if [ ! -f "$MAYOR_STATE" ]; then
        cat > "$MAYOR_STATE" <<EOF
{
    "mode": "executing",
    "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "iteration": 0,
    "convoys": [],
    "workers_spawned": 0,
    "tasks_completed": 0,
    "tasks_failed": 0
}
EOF
    fi
    
    # Get ready tasks
    READY_COUNT=$(bd ready 2>/dev/null | grep -c "^" || echo "0")
    
    if [ "$READY_COUNT" -eq 0 ]; then
        log_success "No tasks ready - work may be complete!"
        echo ""
        echo "Check status: bd list --status open"
        exit 0
    fi
    
    echo "📋 Ready tasks: $READY_COUNT"
    echo ""
    
    # Mayor execution loop message
    echo "I will now orchestrate work across workers."
    echo ""
    echo "For each ready task, I will:"
    echo "  1. Spawn a worker (isolated worktree)"
    echo "  2. Assign the task to the worker"
    echo "  3. The worker implements (not me)"
    echo "  4. Verify completion"
    echo "  5. Merge results"
    echo ""
    echo "Continue? (Ctrl+C to abort)"
fi
```

## Status Dashboard

```bash
if [[ "$ARGS" == *"--status"* ]]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "🎩 Mayor Status Dashboard"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    # Beads summary
    echo "📋 Tasks"
    echo "   Ready:       $(bd ready 2>/dev/null | grep -c '^' || echo '0')"
    echo "   In Progress: $(bd list --status in_progress 2>/dev/null | grep -c '^' || echo '0')"
    echo "   Blocked:     $(bd list --status blocked 2>/dev/null | grep -c '^' || echo '0')"
    echo "   Closed:      $(bd list --status closed 2>/dev/null | grep -c '^' || echo '0')"
    echo ""
    
    # Convoys
    echo "📦 Convoys"
    CONVOY_COUNT=0
    for f in .speckle/convoys/*.json; do
        [ -f "$f" ] && ((CONVOY_COUNT++))
    done
    echo "   Total: $CONVOY_COUNT"
    echo ""
    
    # Workers
    echo "🦨 Workers"
    ACTIVE_WORKERS=$(worker_count "active" 2>/dev/null || echo "0")
    WORKING_WORKERS=$(worker_count "working" 2>/dev/null || echo "0")
    TERMINATED_WORKERS=$(worker_count "terminated" 2>/dev/null || echo "0")
    echo "   Active:     $ACTIVE_WORKERS"
    echo "   Working:    $WORKING_WORKERS"
    echo "   Terminated: $TERMINATED_WORKERS"
    echo ""
    
    # Git state
    echo "📂 Git"
    echo "   Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
    echo "   Worktrees: $(git worktree list 2>/dev/null | wc -l | tr -d ' ')"
    echo ""
    
    # Progress file
    if [ -f ".speckle/progress.txt" ]; then
        ITERATIONS=$(grep -c "^## Iteration" .speckle/progress.txt 2>/dev/null || echo "0")
        echo "📝 Progress"
        echo "   Iterations logged: $ITERATIONS"
    fi
    
    echo ""
    echo "═══════════════════════════════════════════════════════════"
fi
```

## Delegation Workflow

```markdown
## Delegation Process

When I delegate a task to a worker:

### 1. Spawn Worker
```bash
worker_spawn "polecat-N" "$BEAD_ID"
```

### 2. Prepare Context
I create a detailed prompt for the worker including:
- Task description from bead
- Relevant code context
- Previous learnings from progress.txt
- Definition of Done criteria

### 3. Assign Task
The worker receives:
```markdown
## Worker Assignment: {TASK_TITLE}

**Bead ID:** {BEAD_ID}
**Worktree:** {WORKTREE_PATH}

### Your Mission
{TASK_DESCRIPTION}

### Context
{RELEVANT_CONTEXT}

### Previous Learnings
{FROM_PROGRESS_TXT}

### Definition of Done
- [ ] Implementation complete
- [ ] Tests pass
- [ ] Code committed
- [ ] No secrets exposed

### When Complete
Report back with:
1. What you changed
2. Any issues encountered
3. Learnings for future tasks
```

### 4. Monitor Progress
I check worker status periodically and handle:
- Completion → Merge and close
- Failure → Log error, potentially reassign
- Blocked → Investigate and unblock

### 5. Integrate Results
```bash
worker_terminate "polecat-N" --merge
```
```

## Auto Mode (Requires Explicit Approval)

```markdown
## ⚠️ Autonomous Mode

You've requested fully autonomous execution with `--auto`.

**This means I will:**
1. Spawn workers automatically
2. Assign tasks without confirmation
3. Merge completed work automatically
4. Continue until all tasks complete or max iterations

**Safety limits:**
- Max workers: 3 concurrent
- Max iterations: 20
- Timeout per task: 30 minutes
- Human checkpoint every 10 tasks

**To proceed, confirm by saying:**
"Yes, proceed with autonomous orchestration"

I will then begin the MEOW workflow autonomously.
```

## Human Checkpoints

The Mayor always pauses for human input at:
1. **Plan approval** - Before creating convoys
2. **Major milestones** - Every N tasks completed
3. **Errors** - When workers fail
4. **Completion** - Final summary for review

This ensures humans remain in control of the overall direction.
