#!/usr/bin/env bash
# Speckle Convoy Management
# Source this in commands: source ".speckle/scripts/convoy.sh"

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Convoy storage directory
CONVOY_DIR="${SPECKLE_CONVOY_DIR:-.speckle/convoys}"

# Ensure convoy directory exists
init_convoy_dir() {
    mkdir -p "$CONVOY_DIR"
}

# Generate a convoy ID
generate_convoy_id() {
    echo "cv-$(date +%s%N | shasum | head -c 5)"
}

# Get convoy file path
get_convoy_file() {
    local convoy_id="$1"
    echo "$CONVOY_DIR/${convoy_id}.json"
}

# Check if convoy exists
convoy_exists() {
    local convoy_id="$1"
    local convoy_file
    convoy_file=$(get_convoy_file "$convoy_id")
    [ -f "$convoy_file" ]
}

# Create a new convoy
convoy_create() {
    local name="$1"
    shift
    local bead_ids=("$@")
    
    init_convoy_dir
    
    local convoy_id
    convoy_id=$(generate_convoy_id)
    local convoy_file
    convoy_file=$(get_convoy_file "$convoy_id")
    
    # Create convoy JSON
    cat > "$convoy_file" <<EOF
{
    "id": "$convoy_id",
    "name": "$name",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "status": "open",
    "beads": [],
    "assigned_to": null,
    "progress": {
        "total": 0,
        "completed": 0,
        "in_progress": 0,
        "blocked": 0
    },
    "metadata": {}
}
EOF
    
    # Add beads if provided
    for bead_id in "${bead_ids[@]}"; do
        [ -n "$bead_id" ] && convoy_add_bead "$convoy_id" "$bead_id"
    done
    
    echo "$convoy_id"
}

# Add a bead to a convoy
convoy_add_bead() {
    local convoy_id="$1"
    local bead_id="$2"
    
    local convoy_file
    convoy_file=$(get_convoy_file "$convoy_id")
    
    if [ ! -f "$convoy_file" ]; then
        log_error "Convoy not found: $convoy_id"
        return 1
    fi
    
    # Verify bead exists
    if ! bd show "$bead_id" &>/dev/null 2>&1; then
        log_warn "Bead not found: $bead_id"
        return 1
    fi
    
    # Check if already in convoy
    local existing
    existing=$(jq -r ".beads | index(\"$bead_id\")" "$convoy_file")
    if [ "$existing" != "null" ]; then
        log_warn "Bead already in convoy: $bead_id"
        return 0
    fi
    
    # Add bead to convoy
    jq ".beads += [\"$bead_id\"]" "$convoy_file" > "${convoy_file}.tmp"
    mv "${convoy_file}.tmp" "$convoy_file"
    
    # Add convoy label to bead
    bd update "$bead_id" --add-label "convoy:$convoy_id" 2>/dev/null || true
    
    # Update progress
    convoy_update_progress "$convoy_id"
    
    log_info "Added $bead_id to convoy $convoy_id"
    return 0
}

# Remove a bead from a convoy
convoy_remove_bead() {
    local convoy_id="$1"
    local bead_id="$2"
    
    local convoy_file
    convoy_file=$(get_convoy_file "$convoy_id")
    
    if [ ! -f "$convoy_file" ]; then
        log_error "Convoy not found: $convoy_id"
        return 1
    fi
    
    # Remove bead from convoy
    jq ".beads = (.beads | map(select(. != \"$bead_id\")))" "$convoy_file" > "${convoy_file}.tmp"
    mv "${convoy_file}.tmp" "$convoy_file"
    
    # Remove convoy label from bead
    bd update "$bead_id" --remove-label "convoy:$convoy_id" 2>/dev/null || true
    
    # Update progress
    convoy_update_progress "$convoy_id"
    
    log_info "Removed $bead_id from convoy $convoy_id"
}

# Update convoy progress based on bead statuses
convoy_update_progress() {
    local convoy_id="$1"
    
    local convoy_file
    convoy_file=$(get_convoy_file "$convoy_id")
    
    if [ ! -f "$convoy_file" ]; then
        return 1
    fi
    
    local total=0
    local completed=0
    local in_progress=0
    local blocked=0
    
    # Count beads by status
    while IFS= read -r bead_id; do
        [ -z "$bead_id" ] && continue
        ((total++))
        
        local status
        status=$(bd show "$bead_id" --json 2>/dev/null | jq -r '.status // "unknown"')
        
        case "$status" in
            closed) ((completed++)) ;;
            in_progress) ((in_progress++)) ;;
            blocked) ((blocked++)) ;;
        esac
    done < <(jq -r '.beads[]' "$convoy_file" 2>/dev/null)
    
    # Update convoy file
    jq ".progress = {\"total\": $total, \"completed\": $completed, \"in_progress\": $in_progress, \"blocked\": $blocked}" "$convoy_file" > "${convoy_file}.tmp"
    mv "${convoy_file}.tmp" "$convoy_file"
    
    # Check if all complete
    if [ "$total" -gt 0 ] && [ "$completed" -eq "$total" ]; then
        jq '.status = "completed"' "$convoy_file" > "${convoy_file}.tmp"
        mv "${convoy_file}.tmp" "$convoy_file"
    fi
}

# Get the next ready bead in a convoy
convoy_get_next_bead() {
    local convoy_id="$1"
    
    local convoy_file
    convoy_file=$(get_convoy_file "$convoy_id")
    
    if [ ! -f "$convoy_file" ]; then
        return 1
    fi
    
    # Find first open bead
    while IFS= read -r bead_id; do
        [ -z "$bead_id" ] && continue
        
        local status
        status=$(bd show "$bead_id" --json 2>/dev/null | jq -r '.status // "unknown"')
        
        if [ "$status" = "open" ]; then
            echo "$bead_id"
            return 0
        fi
    done < <(jq -r '.beads[]' "$convoy_file" 2>/dev/null)
    
    return 1
}

# Assign convoy to a worker
convoy_assign() {
    local convoy_id="$1"
    local worker="${2:-${USER:-agent}}"
    
    local convoy_file
    convoy_file=$(get_convoy_file "$convoy_id")
    
    if [ ! -f "$convoy_file" ]; then
        log_error "Convoy not found: $convoy_id"
        return 1
    fi
    
    jq ".assigned_to = \"$worker\" | .status = \"in_progress\"" "$convoy_file" > "${convoy_file}.tmp"
    mv "${convoy_file}.tmp" "$convoy_file"
    
    log_success "Assigned convoy $convoy_id to $worker"
}

# Close a convoy
convoy_close() {
    local convoy_id="$1"
    local force="${2:-false}"
    
    local convoy_file
    convoy_file=$(get_convoy_file "$convoy_id")
    
    if [ ! -f "$convoy_file" ]; then
        log_error "Convoy not found: $convoy_id"
        return 1
    fi
    
    # Check for unclosed beads
    convoy_update_progress "$convoy_id"
    local completed
    completed=$(jq -r '.progress.completed' "$convoy_file")
    local total
    total=$(jq -r '.progress.total' "$convoy_file")
    
    if [ "$completed" -ne "$total" ] && [ "$force" != "true" ]; then
        log_warn "Convoy has unclosed beads ($completed/$total)"
        return 1
    fi
    
    jq ".status = \"completed\" | .completed_at = \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"" "$convoy_file" > "${convoy_file}.tmp"
    mv "${convoy_file}.tmp" "$convoy_file"
    
    log_success "Closed convoy: $convoy_id"
}

# List all convoys
convoy_list() {
    init_convoy_dir
    
    local count=0
    for convoy_file in "$CONVOY_DIR"/*.json; do
        [ -f "$convoy_file" ] || continue
        
        local id name status total completed
        id=$(jq -r '.id' "$convoy_file")
        name=$(jq -r '.name' "$convoy_file")
        status=$(jq -r '.status' "$convoy_file")
        total=$(jq -r '.progress.total' "$convoy_file")
        completed=$(jq -r '.progress.completed' "$convoy_file")
        
        printf "%-12s %-30s %-12s [%d/%d]\n" "$id" "$name" "$status" "$completed" "$total"
        ((count++))
    done
    
    if [ "$count" -eq 0 ]; then
        echo "No convoys found"
    fi
}

# Show convoy details
convoy_show() {
    local convoy_id="$1"
    
    local convoy_file
    convoy_file=$(get_convoy_file "$convoy_id")
    
    if [ ! -f "$convoy_file" ]; then
        log_error "Convoy not found: $convoy_id"
        return 1
    fi
    
    jq '.' "$convoy_file"
}

# Get convoy summary stats
convoy_stats() {
    init_convoy_dir
    
    local total=0
    local open=0
    local in_progress=0
    local completed=0
    
    for convoy_file in "$CONVOY_DIR"/*.json; do
        [ -f "$convoy_file" ] || continue
        ((total++))
        
        local status
        status=$(jq -r '.status' "$convoy_file")
        
        case "$status" in
            open) ((open++)) ;;
            in_progress) ((in_progress++)) ;;
            completed) ((completed++)) ;;
        esac
    done
    
    echo "total=$total open=$open in_progress=$in_progress completed=$completed"
}

# Export functions
export -f init_convoy_dir
export -f generate_convoy_id
export -f get_convoy_file
export -f convoy_exists
export -f convoy_create
export -f convoy_add_bead
export -f convoy_remove_bead
export -f convoy_update_progress
export -f convoy_get_next_bead
export -f convoy_assign
export -f convoy_close
export -f convoy_list
export -f convoy_show
export -f convoy_stats
export CONVOY_DIR
