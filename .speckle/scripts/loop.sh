#!/usr/bin/env bash
# Speckle loop helper functions
# Source this in commands: source ".speckle/scripts/loop.sh"

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Source verifiers if available
if [ -f "$SCRIPT_DIR/verifiers.sh" ]; then
    source "$SCRIPT_DIR/verifiers.sh"
fi

# Progress file location
PROGRESS_FILE="${SPECKLE_PROGRESS_FILE:-.speckle/progress.txt}"

# Initialize progress file with header if empty
init_progress_file() {
    local progress_file="${1:-$PROGRESS_FILE}"
    
    mkdir -p "$(dirname "$progress_file")"
    
    if [ ! -s "$progress_file" ]; then
        cat > "$progress_file" <<EOF
# Speckle Progress Log
# Ralph-style iterative development progress tracking
# Each iteration records learnings for future context

Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

EOF
        log_info "Initialized progress file: $progress_file"
    fi
}

# Record iteration start
record_iteration_start() {
    local iteration="$1"
    local bead_id="$2"
    local task_title="$3"
    local progress_file="${4:-$PROGRESS_FILE}"
    
    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    
    cat >> "$progress_file" <<EOF

---
## Iteration $iteration: $task_title
**Bead:** $bead_id
**Started:** $timestamp
**Status:** in_progress

EOF
}

# Record iteration completion
record_iteration_complete() {
    local iteration="$1"
    local bead_id="$2"
    local status="$3"  # success, failed, skipped
    local learnings="$4"
    local progress_file="${5:-$PROGRESS_FILE}"
    
    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    
    # Get git state
    local git_state
    git_state=$(git log -1 --format="%h %s" 2>/dev/null || echo "No commits")
    local files_changed
    files_changed=$(git diff --name-only HEAD~1 2>/dev/null | wc -l | tr -d ' ')
    
    cat >> "$progress_file" <<EOF
**Completed:** $timestamp
**Result:** $status

### Changes
- Commit: $git_state
- Files changed: $files_changed

### Learnings
$learnings

EOF
}

# Record loop summary
record_loop_summary() {
    local total_iterations="$1"
    local completed="$2"
    local failed="$3"
    local remaining="$4"
    local progress_file="${5:-$PROGRESS_FILE}"
    
    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    
    cat >> "$progress_file" <<EOF

---
# Loop Summary
**Time:** $timestamp
**Iterations:** $total_iterations
**Completed:** $completed
**Failed:** $failed
**Remaining:** $remaining

EOF
}

# Get next ready task as JSON
get_next_task() {
    bd ready --json 2>/dev/null | jq -r '.[0] // empty'
}

# Get task count
get_ready_count() {
    bd ready 2>/dev/null | grep -c "^" || echo "0"
}

# Check if task exists and is ready
is_task_ready() {
    local bead_id="$1"
    local status
    status=$(bd show "$bead_id" --json 2>/dev/null | jq -r '.status // "unknown"')
    [ "$status" = "open" ]
}

# Claim a task (mark as in_progress)
claim_task() {
    local bead_id="$1"
    
    if ! bd update "$bead_id" --status in_progress 2>/dev/null; then
        log_error "Failed to claim task $bead_id"
        return 1
    fi
    
    # Verify claim
    local status
    status=$(bd show "$bead_id" --json 2>/dev/null | jq -r '.status')
    if [ "$status" != "in_progress" ]; then
        log_error "Task $bead_id not in_progress after claim (status: $status)"
        return 1
    fi
    
    log_success "Claimed task: $bead_id"
    return 0
}

# Release a task (revert to open)
release_task() {
    local bead_id="$1"
    local reason="${2:-Released by loop}"
    
    bd update "$bead_id" --status open 2>/dev/null
    log_warn "Released task $bead_id: $reason"
}

# Close a task
close_task() {
    local bead_id="$1"
    
    if ! bd close "$bead_id" 2>/dev/null; then
        log_error "Failed to close task $bead_id"
        return 1
    fi
    
    log_success "Closed task: $bead_id"
    return 0
}

# Run standard DoD verifiers
run_standard_verifiers() {
    local failed=0
    
    log_info "Running standard DoD verifiers..."
    
    # 1. No uncommitted changes
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        log_warn "Uncommitted changes detected"
        git status --short
        failed=1
    else
        log_success "Working tree clean"
    fi
    
    # 2. Build passes (if Makefile exists)
    if [ -f "Makefile" ]; then
        if grep -q "^build:" Makefile; then
            log_info "Running: make build"
            if make build 2>&1; then
                log_success "Build passed"
            else
                log_error "Build failed"
                failed=1
            fi
        fi
    fi
    
    # 3. Tests pass
    if [ -f "Makefile" ] && grep -q "^test:" Makefile; then
        log_info "Running: make test"
        if make test 2>&1; then
            log_success "Tests passed"
        else
            log_error "Tests failed"
            failed=1
        fi
    elif [ -f "package.json" ]; then
        if grep -q '"test"' package.json && ! grep -q '"test": "echo' package.json; then
            log_info "Running: npm test"
            if npm test 2>&1; then
                log_success "Tests passed"
            else
                log_error "Tests failed"
                failed=1
            fi
        fi
    elif [ -f "composer.json" ]; then
        if grep -q '"test"' composer.json; then
            log_info "Running: composer test"
            if composer test 2>&1; then
                log_success "Tests passed"
            else
                log_error "Tests failed"
                failed=1
            fi
        fi
    fi
    
    return $failed
}

# Format task details for agent prompt
format_task_prompt() {
    local bead_id="$1"
    
    local task_json
    task_json=$(bd show "$bead_id" --json 2>/dev/null)
    
    local title
    title=$(echo "$task_json" | jq -r '.title // "Unknown"')
    local description
    description=$(echo "$task_json" | jq -r '.description // "No description"')
    local labels
    labels=$(echo "$task_json" | jq -r '.labels // [] | join(", ")')
    local priority
    priority=$(echo "$task_json" | jq -r '.priority // "P2"')
    
    cat <<EOF
## Task: $title

**Bead ID:** $bead_id
**Priority:** $priority
**Labels:** $labels

### Description
$description

### Context from Previous Iterations
$(tail -30 "$PROGRESS_FILE" 2>/dev/null | grep -A5 "### Learnings" | head -20 || echo "No previous learnings")

### Instructions
1. Implement this task completely
2. Write tests if applicable
3. Commit your changes with message format: type(scope): description
4. Report what you changed and any learnings

### Definition of Done
- [ ] Code compiles without errors
- [ ] Tests pass (if applicable)
- [ ] Changes committed
- [ ] No hardcoded secrets or credentials
EOF
}

# Export functions
export -f init_progress_file
export -f record_iteration_start
export -f record_iteration_complete
export -f record_loop_summary
export -f get_next_task
export -f get_ready_count
export -f is_task_ready
export -f claim_task
export -f release_task
export -f close_task
export -f run_standard_verifiers
export -f format_task_prompt
export PROGRESS_FILE
