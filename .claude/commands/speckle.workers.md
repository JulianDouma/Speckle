---
description: Manage ephemeral workers with isolated git worktrees
---

# Speckle Workers

Manage ephemeral workers (polecats in Gastown terminology) - isolated git worktrees
where agents can work without conflicting with each other or the main workspace.

## Arguments

```text
$ARGUMENTS
```

Subcommands:
- `spawn <name> [--task <bead-id>]` - Create a new worker
- `list` - List all workers
- `show <worker-name>` - Show worker details
- `terminate <worker-name>` - Remove worker and merge changes
- `clean` - Remove all terminated workers
- `status` - Worker status dashboard

## Concept: Ephemeral Workers

Each worker is:
1. **Isolated** - Own git worktree (no conflicts)
2. **Ephemeral** - Created for a task, removed when done
3. **Tracked** - State persisted in `.speckle/workers/`
4. **Independent** - Can run in parallel with others

```
Main Repo (./)
├── .speckle/workers/
│   ├── polecat-1.json     # Worker metadata
│   └── polecat-2.json
└── .speckle/worktrees/
    ├── polecat-1/         # Git worktree
    │   └── ... (repo files)
    └── polecat-2/
        └── ... (repo files)
```

## Startup

```bash
source ".speckle/scripts/common.sh"
source ".speckle/scripts/workers.sh"

# Ensure directories exist
mkdir -p ".speckle/workers"
mkdir -p ".speckle/worktrees"

ARGS="$ARGUMENTS"
SUBCOMMAND=$(echo "$ARGS" | awk '{print $1}')
WORKER_ARGS=$(echo "$ARGS" | cut -d' ' -f2-)
```

## Spawn Worker

```bash
if [ "$SUBCOMMAND" = "spawn" ]; then
    NAME=$(echo "$WORKER_ARGS" | awk '{print $1}')
    TASK_ID=$(echo "$WORKER_ARGS" | grep -oP '(?<=--task\s)\S+' || echo "")
    
    if [ -z "$NAME" ]; then
        # Auto-generate name
        NAME="polecat-$(date +%s | tail -c 5)"
    fi
    
    # Check if worker already exists
    if [ -f ".speckle/workers/${NAME}.json" ]; then
        log_error "Worker already exists: $NAME"
        exit 1
    fi
    
    # Create branch for worker
    BRANCH="worker/${NAME}"
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    
    log_info "Creating worker: $NAME"
    
    # Create worktree
    WORKTREE_PATH=".speckle/worktrees/$NAME"
    if ! git worktree add "$WORKTREE_PATH" -b "$BRANCH" 2>/dev/null; then
        # Branch might exist, try without -b
        git worktree add "$WORKTREE_PATH" "$BRANCH" 2>/dev/null || {
            log_error "Failed to create worktree"
            exit 1
        }
    fi
    
    # Create worker metadata
    cat > ".speckle/workers/${NAME}.json" <<EOF
{
    "name": "$NAME",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "status": "active",
    "branch": "$BRANCH",
    "base_branch": "$CURRENT_BRANCH",
    "worktree": "$WORKTREE_PATH",
    "task": ${TASK_ID:+\"$TASK_ID\"}${TASK_ID:-null},
    "pid": null,
    "commits": []
}
EOF
    
    log_success "Worker spawned: $NAME"
    echo ""
    echo "🦨 Worker: $NAME"
    echo "   Branch: $BRANCH"
    echo "   Worktree: $WORKTREE_PATH"
    echo "   Task: ${TASK_ID:-none}"
    echo ""
    echo "To work in this context:"
    echo "   cd $WORKTREE_PATH"
    echo ""
    echo "When done:"
    echo "   /speckle.workers terminate $NAME"
fi
```

## List Workers

```bash
if [ "$SUBCOMMAND" = "list" ] || [ -z "$SUBCOMMAND" ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "🦨 Speckle Workers"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    WORKER_COUNT=0
    for worker_file in .speckle/workers/*.json; do
        [ -f "$worker_file" ] || continue
        
        NAME=$(jq -r '.name' "$worker_file")
        STATUS=$(jq -r '.status' "$worker_file")
        TASK=$(jq -r '.task // "none"' "$worker_file")
        BRANCH=$(jq -r '.branch' "$worker_file")
        CREATED=$(jq -r '.created_at' "$worker_file")
        
        # Status emoji
        case "$STATUS" in
            active) EMOJI="🟢" ;;
            working) EMOJI="🔄" ;;
            done) EMOJI="✅" ;;
            error) EMOJI="🔴" ;;
            *) EMOJI="❓" ;;
        esac
        
        printf "%s %-15s %-12s %-15s %s\n" "$EMOJI" "$NAME" "$STATUS" "$TASK" "$BRANCH"
        ((WORKER_COUNT++))
    done
    
    if [ "$WORKER_COUNT" -eq 0 ]; then
        echo "   No workers active"
        echo ""
        echo "   Spawn one: /speckle.workers spawn polecat-1 --task bead-xyz"
    fi
    
    echo ""
    echo "═══════════════════════════════════════════════════════════"
fi
```

## Show Worker Details

```bash
if [ "$SUBCOMMAND" = "show" ]; then
    NAME="$WORKER_ARGS"
    WORKER_FILE=".speckle/workers/${NAME}.json"
    
    if [ ! -f "$WORKER_FILE" ]; then
        log_error "Worker not found: $NAME"
        exit 1
    fi
    
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "🦨 Worker: $NAME"
    echo "═══════════════════════════════════════════════════════════"
    
    jq -r '"
Status:    \(.status)
Created:   \(.created_at)
Branch:    \(.branch)
Base:      \(.base_branch)
Worktree:  \(.worktree)
Task:      \(.task // \"none\")
"' "$WORKER_FILE"
    
    # Show commits made by worker
    BRANCH=$(jq -r '.branch' "$WORKER_FILE")
    BASE=$(jq -r '.base_branch' "$WORKER_FILE")
    
    echo "Commits:"
    git log --oneline "$BASE..$BRANCH" 2>/dev/null | head -10 || echo "  (none)"
    
    # Show uncommitted changes
    WORKTREE=$(jq -r '.worktree' "$WORKER_FILE")
    if [ -d "$WORKTREE" ]; then
        echo ""
        echo "Working tree status:"
        (cd "$WORKTREE" && git status --short) || echo "  (clean)"
    fi
    
    echo ""
    echo "═══════════════════════════════════════════════════════════"
fi
```

## Terminate Worker

```bash
if [ "$SUBCOMMAND" = "terminate" ]; then
    NAME=$(echo "$WORKER_ARGS" | awk '{print $1}')
    MERGE=$(echo "$WORKER_ARGS" | grep -q -- '--merge' && echo "true" || echo "false")
    FORCE=$(echo "$WORKER_ARGS" | grep -q -- '--force' && echo "true" || echo "false")
    
    WORKER_FILE=".speckle/workers/${NAME}.json"
    
    if [ ! -f "$WORKER_FILE" ]; then
        log_error "Worker not found: $NAME"
        exit 1
    fi
    
    BRANCH=$(jq -r '.branch' "$WORKER_FILE")
    BASE=$(jq -r '.base_branch' "$WORKER_FILE")
    WORKTREE=$(jq -r '.worktree' "$WORKER_FILE")
    
    log_info "Terminating worker: $NAME"
    
    # Check for uncommitted changes
    if [ -d "$WORKTREE" ]; then
        CHANGES=$(cd "$WORKTREE" && git status --porcelain)
        if [ -n "$CHANGES" ] && [ "$FORCE" != "true" ]; then
            log_warn "Worker has uncommitted changes:"
            echo "$CHANGES"
            echo ""
            echo "Options:"
            echo "  --merge  Merge committed changes to base"
            echo "  --force  Discard all changes"
            exit 1
        fi
    fi
    
    # Merge if requested
    if [ "$MERGE" = "true" ]; then
        log_info "Merging $BRANCH into $BASE"
        git checkout "$BASE"
        if git merge "$BRANCH" --no-edit; then
            log_success "Merged successfully"
        else
            log_error "Merge conflicts detected"
            echo "Resolve conflicts and run terminate again"
            exit 1
        fi
    fi
    
    # Remove worktree
    if [ -d "$WORKTREE" ]; then
        git worktree remove "$WORKTREE" --force 2>/dev/null || rm -rf "$WORKTREE"
        log_info "Removed worktree: $WORKTREE"
    fi
    
    # Delete branch (if not merged)
    if [ "$MERGE" != "true" ]; then
        git branch -D "$BRANCH" 2>/dev/null || true
    fi
    
    # Update worker status
    jq '.status = "terminated" | .terminated_at = "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"' "$WORKER_FILE" > "${WORKER_FILE}.tmp"
    mv "${WORKER_FILE}.tmp" "$WORKER_FILE"
    
    log_success "Worker terminated: $NAME"
fi
```

## Clean Workers

```bash
if [ "$SUBCOMMAND" = "clean" ]; then
    log_info "Cleaning terminated workers..."
    
    CLEANED=0
    for worker_file in .speckle/workers/*.json; do
        [ -f "$worker_file" ] || continue
        
        STATUS=$(jq -r '.status' "$worker_file")
        if [ "$STATUS" = "terminated" ]; then
            NAME=$(jq -r '.name' "$worker_file")
            rm "$worker_file"
            log_info "Removed: $NAME"
            ((CLEANED++))
        fi
    done
    
    # Clean orphaned worktrees
    git worktree prune 2>/dev/null || true
    
    log_success "Cleaned $CLEANED terminated workers"
fi
```

## Status Dashboard

```bash
if [ "$SUBCOMMAND" = "status" ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "🦨 Worker Status Dashboard"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    TOTAL=0
    ACTIVE=0
    WORKING=0
    DONE=0
    TERMINATED=0
    
    for worker_file in .speckle/workers/*.json; do
        [ -f "$worker_file" ] || continue
        ((TOTAL++))
        
        STATUS=$(jq -r '.status' "$worker_file")
        case "$STATUS" in
            active) ((ACTIVE++)) ;;
            working) ((WORKING++)) ;;
            done) ((DONE++)) ;;
            terminated) ((TERMINATED++)) ;;
        esac
    done
    
    echo "Workers"
    echo "  Total:      $TOTAL"
    echo "  Active:     $ACTIVE"
    echo "  Working:    $WORKING"
    echo "  Done:       $DONE"
    echo "  Terminated: $TERMINATED"
    echo ""
    
    # Git worktrees
    echo "Git Worktrees:"
    git worktree list 2>/dev/null | grep -v "^$(pwd)" | head -10 || echo "  (none)"
    
    echo ""
    echo "═══════════════════════════════════════════════════════════"
fi
```

## Integration with Loop

Workers integrate with the loop command:

```bash
# In /speckle.loop, spawn a fresh worker for each task:
/speckle.workers spawn --task "$BEAD_ID"

# Work in isolated context
cd "$WORKTREE_PATH"
# ... implement task ...

# Terminate and merge when done
/speckle.workers terminate "$WORKER_NAME" --merge
```
