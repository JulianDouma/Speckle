#!/usr/bin/env bash
# Speckle comment helper functions
# Source this in commands: source ".speckle/scripts/comments.sh"

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Format a completion comment for an implemented task
# Arguments:
#   $1 - Task ID (e.g., T001)
#   $2 - Bead ID (e.g., speckle-065)
#   $3 - Files changed (newline-separated list)
#   $4 - Lines added
#   $5 - Lines removed
# Returns: Formatted markdown comment
format_completion_comment() {
    local task_id="${1:-unknown}"
    local bead_id="${2:-unknown}"
    local files_changed="${3:-}"
    local lines_added="${4:-0}"
    local lines_removed="${5:-0}"
    local actor="${BD_ACTOR:-${GIT_AUTHOR_NAME:-$(git config user.name 2>/dev/null || echo 'unknown')}}"
    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    
    # Truncate files list if too long
    local file_count
    file_count=$(echo "$files_changed" | grep -c '.' || echo 0)
    local files_display="$files_changed"
    if [ "$file_count" -gt 20 ]; then
        files_display=$(echo "$files_changed" | head -20)
        files_display="${files_display}
... and $((file_count - 20)) more files"
    fi
    
    cat <<EOF
## Implementation Complete

**Task:** $task_id
**Bead:** $bead_id
**Actor:** $actor
**Time:** $timestamp

### Changes
- Lines added: +$lines_added
- Lines removed: -$lines_removed
- Files changed: $file_count

### Files Modified
\`\`\`
$files_display
\`\`\`

---
*Recorded by Speckle*
EOF
}

# Format a progress note for mid-implementation context
# Arguments:
#   $1 - Note content
#   $2 - Task ID (optional)
#   $3 - Bead ID (optional)
# Returns: Formatted markdown comment
format_progress_note() {
    local note="${1:-}"
    local task_id="${2:-}"
    local bead_id="${3:-}"
    local actor="${BD_ACTOR:-${GIT_AUTHOR_NAME:-$(git config user.name 2>/dev/null || echo 'unknown')}}"
    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    
    local header="## Progress Note"
    if [ -n "$task_id" ]; then
        header="## Progress Note: $task_id"
    fi
    
    cat <<EOF
$header

**Actor:** $actor
**Time:** $timestamp

$note

---
*Recorded by Speckle*
EOF
}

# Safely add a comment to a bead issue
# Arguments:
#   $1 - Bead ID
#   $2 - Comment content
# Returns: 0 on success, 1 on failure (but doesn't exit)
add_comment_safe() {
    local bead_id="${1:-}"
    local comment="${2:-}"
    
    if [ -z "$bead_id" ]; then
        log_warn "Cannot add comment: no bead ID provided"
        return 1
    fi
    
    if [ -z "$comment" ]; then
        log_warn "Cannot add comment: no content provided"
        return 1
    fi
    
    # Check if bd is available
    if ! command -v bd &>/dev/null; then
        log_warn "Cannot add comment: beads (bd) not available"
        return 1
    fi
    
    # Try to add the comment
    if bd comments add "$bead_id" "$comment" 2>/dev/null; then
        log_success "Comment added to $bead_id"
        return 0
    else
        log_warn "Failed to add comment to $bead_id (continuing anyway)"
        return 1
    fi
}

# Get git diff statistics for the last commit
# Returns: JSON object with files, added, removed counts
# Output format: {"files":"file1,file2","files_count":2,"added":10,"removed":5}
get_diff_stats() {
    local base="${1:-HEAD~1}"
    
    # Get files changed as comma-separated list
    local files
    files=$(git diff --name-only "$base" 2>/dev/null | tr '\n' ',' | sed 's/,$//' || echo "")
    
    # Count files
    local files_count=0
    if [ -n "$files" ]; then
        files_count=$(echo "$files" | tr ',' '\n' | wc -l | tr -d ' ')
    fi
    
    # Get line stats
    local stats
    stats=$(git diff --numstat "$base" 2>/dev/null || echo "")
    
    local lines_added=0
    local lines_removed=0
    
    if [ -n "$stats" ]; then
        while IFS=$'\t' read -r added removed _file; do
            if [ "$added" != "-" ] && [ -n "$added" ]; then
                lines_added=$((lines_added + added))
            fi
            if [ "$removed" != "-" ] && [ -n "$removed" ]; then
                lines_removed=$((lines_removed + removed))
            fi
        done <<< "$stats"
    fi
    
    # Output as JSON for reliable parsing
    printf '{"files":"%s","files_count":%d,"added":%d,"removed":%d}\n' \
        "$files" "$files_count" "$lines_added" "$lines_removed"
}

# Parse diff stats JSON - helper for callers without jq
# Usage: parse_diff_stats "$json" "field"  where field is files|files_count|added|removed
parse_diff_stats() {
    local json="${1:-}"
    local field="${2:-}"
    
    case "$field" in
        files)
            echo "$json" | sed 's/.*"files":"\([^"]*\)".*/\1/'
            ;;
        files_count)
            echo "$json" | sed 's/.*"files_count":\([0-9]*\).*/\1/'
            ;;
        added)
            echo "$json" | sed 's/.*"added":\([0-9]*\).*/\1/'
            ;;
        removed)
            echo "$json" | sed 's/.*"removed":\([0-9]*\).*/\1/'
            ;;
        *)
            echo "0"
            ;;
    esac
}

# Export functions for use in commands
export -f format_completion_comment
export -f format_progress_note
export -f add_comment_safe
export -f get_diff_stats
export -f parse_diff_stats
