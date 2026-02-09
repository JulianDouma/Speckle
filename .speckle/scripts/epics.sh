#!/usr/bin/env bash
# Speckle epic lifecycle helper functions
# Source this in commands: source ".speckle/scripts/epics.sh"

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"
source "$SCRIPT_DIR/labels.sh"

# Create an epic issue for a feature
# Arguments:
#   $1 - Feature name (e.g., "001-comments-integration")
#   $2 - Spec file path (for description extraction)
#   $3 - Extra labels (optional)
# Returns: Epic issue ID
create_epic() {
    local feature_name="${1:-}"
    local spec_file="${2:-}"
    local extra_labels="${3:-}"
    
    if [ -z "$feature_name" ]; then
        log_error "create_epic: feature name required"
        return 1
    fi
    
    # Extract summary from spec.md if available
    local description="Feature: $feature_name"
    if [ -f "$spec_file" ]; then
        # Get first paragraph after "# Feature Specification"
        local spec_summary
        spec_summary=$(sed -n '/^# Feature Specification/,/^##/p' "$spec_file" | \
            grep -v '^#' | grep -v '^\*\*' | head -20 | tr '\n' ' ' | xargs)
        if [ -n "$spec_summary" ]; then
            description="$spec_summary"
        fi
    fi
    
    # Build labels
    local labels="speckle,epic,epic:$(slugify "$feature_name")"
    if [ -n "$extra_labels" ]; then
        labels="$labels,$extra_labels"
    fi
    
    # Create epic issue
    local epic_id
    epic_id=$(bd create "Epic: $feature_name" \
        --type feature \
        --priority 1 \
        --labels "$labels" \
        --description "$description" \
        2>/dev/null | grep -oE 'speckle-[a-z0-9]+' || echo "")
    
    if [ -z "$epic_id" ]; then
        log_error "Failed to create epic"
        return 1
    fi
    
    echo "$epic_id"
}

# Get epic ID from mapping file
# Arguments:
#   $1 - Mapping file path
# Returns: Epic ID or empty string
get_epic_id() {
    local mapping_file="${1:-}"
    
    if [ ! -f "$mapping_file" ]; then
        return 0
    fi
    
    # Extract epicId from JSON using jq (portable and reliable)
    json_get "$mapping_file" "epicId"
}

# Save epic ID to mapping file
# Arguments:
#   $1 - Mapping file path
#   $2 - Epic ID
save_epic_id() {
    local mapping_file="${1:-}"
    local epic_id="${2:-}"
    
    if [ ! -f "$mapping_file" ]; then
        log_error "Mapping file not found: $mapping_file"
        return 1
    fi
    
    # Add/update epicId in mapping using jq (portable and reliable)
    json_set "$mapping_file" "epicId" "$epic_id"
}

# Update epic status based on task states
# Arguments:
#   $1 - Epic ID
#   $2 - Mapping file path (to get task IDs)
# Returns: New status (open, in_progress, closed)
update_epic_status() {
    local epic_id="${1:-}"
    local mapping_file="${2:-}"
    
    if [ -z "$epic_id" ]; then
        return 0
    fi
    
    # Get task bead IDs from mapping using jq
    local task_ids
    task_ids=$(jq -r '.tasks[]?.beadId // empty' "$mapping_file" 2>/dev/null || echo "")
    
    if [ -z "$task_ids" ]; then
        # No tasks yet - epic stays open
        return 0
    fi
    
    local total=0
    local closed=0
    local in_progress=0
    
    while read -r bead_id; do
        [ -z "$bead_id" ] && continue
        ((total++)) || true
        
        local status
        status=$(bd show "$bead_id" 2>/dev/null | grep -oE 'Status:\s*\w+' | awk '{print $2}' || echo "open")
        
        case "$status" in
            closed) ((closed++)) || true ;;
            in_progress) ((in_progress++)) || true ;;
        esac
    done <<< "$task_ids"
    
    # Determine new epic status
    local new_status="open"
    if [ "$closed" -eq "$total" ] && [ "$total" -gt 0 ]; then
        new_status="closed"
    elif [ "$in_progress" -gt 0 ] || [ "$closed" -gt 0 ]; then
        new_status="in_progress"
    fi
    
    # Update epic status
    bd update "$epic_id" --status "$new_status" 2>/dev/null || true
    
    echo "$new_status"
}

# Calculate epic progress percentage
# Arguments:
#   $1 - Epic ID
#   $2 - Mapping file path
# Returns: Progress percentage (0-100)
get_epic_progress() {
    local epic_id="${1:-}"
    local mapping_file="${2:-}"
    
    if [ -z "$epic_id" ] || [ ! -f "$mapping_file" ]; then
        echo "0"
        return
    fi
    
    # Get task bead IDs using jq
    local task_ids
    task_ids=$(jq -r '.tasks[]?.beadId // empty' "$mapping_file" 2>/dev/null || echo "")
    
    if [ -z "$task_ids" ]; then
        echo "0"
        return
    fi
    
    local total=0
    local closed=0
    
    while read -r bead_id; do
        [ -z "$bead_id" ] && continue
        ((total++)) || true
        
        local status
        status=$(bd show "$bead_id" 2>/dev/null | grep -oE 'Status:\s*\w+' | awk '{print $2}' || echo "open")
        
        if [ "$status" = "closed" ]; then
            ((closed++)) || true
        fi
    done <<< "$task_ids"
    
    if [ "$total" -eq 0 ]; then
        echo "0"
    else
        echo "$((closed * 100 / total))"
    fi
}

# Link a task to its epic
# Arguments:
#   $1 - Task bead ID
#   $2 - Epic bead ID
link_task_to_epic() {
    local task_id="${1:-}"
    local epic_id="${2:-}"
    
    if [ -z "$task_id" ] || [ -z "$epic_id" ]; then
        return 1
    fi
    
    # Task depends on epic (epic is the parent)
    bd dep add "$task_id" "$epic_id" 2>/dev/null || true
}

# Export functions
export -f create_epic
export -f get_epic_id
export -f save_epic_id
export -f update_epic_status
export -f get_epic_progress
export -f link_task_to_epic
