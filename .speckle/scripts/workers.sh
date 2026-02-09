#!/usr/bin/env bash
# Speckle Ephemeral Worker Management
# Source this in commands: source ".speckle/scripts/workers.sh"

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Worker storage
WORKERS_DIR="${SPECKLE_WORKERS_DIR:-.speckle/workers}"
WORKTREES_DIR="${SPECKLE_WORKTREES_DIR:-.speckle/worktrees}"

# Initialize worker directories
init_worker_dirs() {
    mkdir -p "$WORKERS_DIR"
    mkdir -p "$WORKTREES_DIR"
}

# Generate a worker name
generate_worker_name() {
    echo "polecat-$(date +%s%N | shasum | head -c 4)"
}

# Get worker file path
get_worker_file() {
    local name="$1"
    echo "$WORKERS_DIR/${name}.json"
}

# Check if worker exists
worker_exists() {
    local name="$1"
    [ -f "$(get_worker_file "$name")" ]
}

# Spawn a new worker
worker_spawn() {
    local name="${1:-$(generate_worker_name)}"
    local task_id="${2:-}"
    
    init_worker_dirs
    
    local worker_file
    worker_file=$(get_worker_file "$name")
    
    if [ -f "$worker_file" ]; then
        log_error "Worker already exists: $name"
        return 1
    fi
    
    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
    local worker_branch="worker/$name"
    local worktree_path="$WORKTREES_DIR/$name"
    
    log_info "Spawning worker: $name"
    
    # Create worktree with new branch
    if ! git worktree add "$worktree_path" -b "$worker_branch" 2>/dev/null; then
        # Branch might exist, try without -b
        if ! git worktree add "$worktree_path" "$worker_branch" 2>/dev/null; then
            log_error "Failed to create worktree for $name"
            return 1
        fi
    fi
    
    # Create worker metadata
    local task_json="null"
    [ -n "$task_id" ] && task_json="\"$task_id\""
    
    cat > "$worker_file" <<EOF
{
    "name": "$name",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "status": "active",
    "branch": "$worker_branch",
    "base_branch": "$current_branch",
    "worktree": "$worktree_path",
    "task": $task_json,
    "commits": [],
    "metadata": {}
}
EOF
    
    # If task provided, claim it
    if [ -n "$task_id" ]; then
        bd update "$task_id" --status in_progress --assignee "$name" 2>/dev/null || true
    fi
    
    log_success "Worker spawned: $name"
    echo "$name"
}

# Get worker status
worker_status() {
    local name="$1"
    local worker_file
    worker_file=$(get_worker_file "$name")
    
    if [ ! -f "$worker_file" ]; then
        echo "not_found"
        return 1
    fi
    
    jq -r '.status' "$worker_file"
}

# Update worker status
worker_set_status() {
    local name="$1"
    local status="$2"
    
    local worker_file
    worker_file=$(get_worker_file "$name")
    
    if [ ! -f "$worker_file" ]; then
        log_error "Worker not found: $name"
        return 1
    fi
    
    jq ".status = \"$status\"" "$worker_file" > "${worker_file}.tmp"
    mv "${worker_file}.tmp" "$worker_file"
}

# Get worker worktree path
worker_worktree() {
    local name="$1"
    local worker_file
    worker_file=$(get_worker_file "$name")
    
    if [ ! -f "$worker_file" ]; then
        return 1
    fi
    
    jq -r '.worktree' "$worker_file"
}

# Get worker branch
worker_branch() {
    local name="$1"
    local worker_file
    worker_file=$(get_worker_file "$name")
    
    if [ ! -f "$worker_file" ]; then
        return 1
    fi
    
    jq -r '.branch' "$worker_file"
}

# Check if worker has uncommitted changes
worker_has_changes() {
    local name="$1"
    local worktree
    worktree=$(worker_worktree "$name")
    
    if [ -d "$worktree" ]; then
        local changes
        changes=$(cd "$worktree" && git status --porcelain)
        [ -n "$changes" ]
    else
        return 1
    fi
}

# Record a commit for a worker
worker_record_commit() {
    local name="$1"
    local commit_hash="$2"
    
    local worker_file
    worker_file=$(get_worker_file "$name")
    
    if [ ! -f "$worker_file" ]; then
        return 1
    fi
    
    jq ".commits += [\"$commit_hash\"]" "$worker_file" > "${worker_file}.tmp"
    mv "${worker_file}.tmp" "$worker_file"
}

# Terminate a worker
worker_terminate() {
    local name="$1"
    local merge="${2:-false}"
    local force="${3:-false}"
    
    local worker_file
    worker_file=$(get_worker_file "$name")
    
    if [ ! -f "$worker_file" ]; then
        log_error "Worker not found: $name"
        return 1
    fi
    
    local branch base_branch worktree task_id
    branch=$(jq -r '.branch' "$worker_file")
    base_branch=$(jq -r '.base_branch' "$worker_file")
    worktree=$(jq -r '.worktree' "$worker_file")
    task_id=$(jq -r '.task // ""' "$worker_file")
    
    log_info "Terminating worker: $name"
    
    # Check for uncommitted changes
    if [ -d "$worktree" ]; then
        local changes
        changes=$(cd "$worktree" && git status --porcelain 2>/dev/null || echo "")
        if [ -n "$changes" ] && [ "$force" != "true" ]; then
            log_warn "Worker has uncommitted changes"
            return 1
        fi
    fi
    
    # Merge if requested
    if [ "$merge" = "true" ]; then
        local current_branch
        current_branch=$(git rev-parse --abbrev-ref HEAD)
        
        git checkout "$base_branch" 2>/dev/null
        if git merge "$branch" --no-edit 2>/dev/null; then
            log_success "Merged $branch into $base_branch"
        else
            log_error "Merge conflicts - resolve manually"
            git checkout "$current_branch" 2>/dev/null
            return 1
        fi
    fi
    
    # Remove worktree
    if [ -d "$worktree" ]; then
        git worktree remove "$worktree" --force 2>/dev/null || rm -rf "$worktree"
    fi
    
    # Delete branch if not merged
    if [ "$merge" != "true" ]; then
        git branch -D "$branch" 2>/dev/null || true
    fi
    
    # Close task if assigned
    if [ -n "$task_id" ] && [ "$task_id" != "null" ]; then
        bd close "$task_id" 2>/dev/null || true
    fi
    
    # Update worker metadata
    jq '.status = "terminated" | .terminated_at = "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"' "$worker_file" > "${worker_file}.tmp"
    mv "${worker_file}.tmp" "$worker_file"
    
    log_success "Worker terminated: $name"
}

# List all workers
worker_list() {
    init_worker_dirs
    
    for worker_file in "$WORKERS_DIR"/*.json; do
        [ -f "$worker_file" ] || continue
        jq -r '[.name, .status, .task // "none", .branch] | @tsv' "$worker_file"
    done
}

# Count workers by status
worker_count() {
    local status="${1:-}"
    init_worker_dirs
    
    local count=0
    for worker_file in "$WORKERS_DIR"/*.json; do
        [ -f "$worker_file" ] || continue
        
        if [ -z "$status" ]; then
            ((count++))
        else
            local worker_status
            worker_status=$(jq -r '.status' "$worker_file")
            [ "$worker_status" = "$status" ] && ((count++))
        fi
    done
    
    echo "$count"
}

# Clean terminated workers
worker_clean() {
    init_worker_dirs
    
    local cleaned=0
    for worker_file in "$WORKERS_DIR"/*.json; do
        [ -f "$worker_file" ] || continue
        
        local status
        status=$(jq -r '.status' "$worker_file")
        if [ "$status" = "terminated" ]; then
            rm "$worker_file"
            ((cleaned++))
        fi
    done
    
    # Prune orphaned worktrees
    git worktree prune 2>/dev/null || true
    
    echo "$cleaned"
}

# Get active workers for a task
worker_for_task() {
    local task_id="$1"
    
    for worker_file in "$WORKERS_DIR"/*.json; do
        [ -f "$worker_file" ] || continue
        
        local task status
        task=$(jq -r '.task // ""' "$worker_file")
        status=$(jq -r '.status' "$worker_file")
        
        if [ "$task" = "$task_id" ] && [ "$status" != "terminated" ]; then
            jq -r '.name' "$worker_file"
            return 0
        fi
    done
    
    return 1
}

# Export functions
export -f init_worker_dirs
export -f generate_worker_name
export -f get_worker_file
export -f worker_exists
export -f worker_spawn
export -f worker_status
export -f worker_set_status
export -f worker_worktree
export -f worker_branch
export -f worker_has_changes
export -f worker_record_commit
export -f worker_terminate
export -f worker_list
export -f worker_count
export -f worker_clean
export -f worker_for_task
export WORKERS_DIR WORKTREES_DIR
