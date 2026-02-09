---
description: Manage work convoys (bundles of related tasks)
---

# Speckle Convoy

Manage convoys - bundles of related beads assigned together for coordinated work.
Inspired by Gastown's convoy system for multi-agent task distribution.

## Arguments

```text
$ARGUMENTS
```

Subcommands:
- `create <name> [bead-ids...]` - Create a new convoy
- `list` - List all convoys
- `show <convoy-id>` - Show convoy details
- `add <convoy-id> <bead-ids...>` - Add beads to convoy
- `remove <convoy-id> <bead-ids...>` - Remove beads from convoy
- `assign <convoy-id> [--worker <name>]` - Assign convoy to worker
- `close <convoy-id>` - Close completed convoy
- `status` - Show convoy dashboard

## Startup

```bash
source ".speckle/scripts/common.sh"
source ".speckle/scripts/convoy.sh"

# Ensure convoy directory exists
mkdir -p ".speckle/convoys"

ARGS="$ARGUMENTS"
SUBCOMMAND=$(echo "$ARGS" | awk '{print $1}')
CONVOY_ARGS=$(echo "$ARGS" | cut -d' ' -f2-)
```

## Create Convoy

```bash
if [ "$SUBCOMMAND" = "create" ]; then
    NAME=$(echo "$CONVOY_ARGS" | awk '{print $1}')
    BEAD_IDS=$(echo "$CONVOY_ARGS" | cut -d' ' -f2-)
    
    if [ -z "$NAME" ]; then
        log_error "Usage: /speckle.convoy create <name> [bead-ids...]"
        exit 1
    fi
    
    # Generate convoy ID
    CONVOY_ID="cv-$(date +%s | shasum | head -c 5)"
    CONVOY_FILE=".speckle/convoys/${CONVOY_ID}.json"
    
    # Create convoy JSON
    cat > "$CONVOY_FILE" <<EOF
{
    "id": "$CONVOY_ID",
    "name": "$NAME",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "status": "open",
    "beads": [],
    "assigned_to": null,
    "progress": {
        "total": 0,
        "completed": 0,
        "in_progress": 0,
        "blocked": 0
    }
}
EOF
    
    log_success "Created convoy: $CONVOY_ID ($NAME)"
    
    # Add beads if provided
    if [ -n "$BEAD_IDS" ]; then
        for bead in $BEAD_IDS; do
            convoy_add_bead "$CONVOY_ID" "$bead"
        done
    fi
    
    echo ""
    echo "📦 Convoy: $CONVOY_ID"
    echo "   Name: $NAME"
    echo "   File: $CONVOY_FILE"
    echo ""
    echo "Next: Add beads with /speckle.convoy add $CONVOY_ID <bead-id>"
fi
```

## List Convoys

```bash
if [ "$SUBCOMMAND" = "list" ] || [ -z "$SUBCOMMAND" ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "📦 Speckle Convoys"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    CONVOY_COUNT=0
    for convoy_file in .speckle/convoys/*.json; do
        [ -f "$convoy_file" ] || continue
        
        ID=$(jq -r '.id' "$convoy_file")
        NAME=$(jq -r '.name' "$convoy_file")
        STATUS=$(jq -r '.status' "$convoy_file")
        TOTAL=$(jq -r '.progress.total' "$convoy_file")
        COMPLETED=$(jq -r '.progress.completed' "$convoy_file")
        ASSIGNED=$(jq -r '.assigned_to // "unassigned"' "$convoy_file")
        
        # Status emoji
        case "$STATUS" in
            open) EMOJI="📭" ;;
            in_progress) EMOJI="🚚" ;;
            completed) EMOJI="✅" ;;
            *) EMOJI="❓" ;;
        esac
        
        printf "%s %-12s %-25s [%d/%d] %s\n" "$EMOJI" "$ID" "$NAME" "$COMPLETED" "$TOTAL" "$ASSIGNED"
        ((CONVOY_COUNT++))
    done
    
    if [ "$CONVOY_COUNT" -eq 0 ]; then
        echo "   No convoys found"
        echo ""
        echo "   Create one: /speckle.convoy create \"Feature Work\" bead-1 bead-2"
    fi
    
    echo ""
    echo "═══════════════════════════════════════════════════════════"
fi
```

## Show Convoy Details

```bash
if [ "$SUBCOMMAND" = "show" ]; then
    CONVOY_ID="$CONVOY_ARGS"
    CONVOY_FILE=".speckle/convoys/${CONVOY_ID}.json"
    
    if [ ! -f "$CONVOY_FILE" ]; then
        log_error "Convoy not found: $CONVOY_ID"
        exit 1
    fi
    
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "📦 Convoy Details"
    echo "═══════════════════════════════════════════════════════════"
    
    jq -r '"
ID:        \(.id)
Name:      \(.name)
Status:    \(.status)
Created:   \(.created_at)
Assigned:  \(.assigned_to // \"unassigned\")

Progress:  \(.progress.completed)/\(.progress.total) complete
           \(.progress.in_progress) in progress
           \(.progress.blocked) blocked

Beads:
"' "$CONVOY_FILE"
    
    # List beads with status
    jq -r '.beads[]' "$CONVOY_FILE" | while read -r bead_id; do
        STATUS=$(bd show "$bead_id" --json 2>/dev/null | jq -r '.status // "unknown"')
        TITLE=$(bd show "$bead_id" --json 2>/dev/null | jq -r '.title // "Unknown"' | head -c 50)
        
        case "$STATUS" in
            open) EMOJI="⬜" ;;
            in_progress) EMOJI="🔄" ;;
            closed) EMOJI="✅" ;;
            blocked) EMOJI="🚫" ;;
            *) EMOJI="❓" ;;
        esac
        
        printf "  %s %-12s %s\n" "$EMOJI" "$bead_id" "$TITLE"
    done
    
    echo ""
    echo "═══════════════════════════════════════════════════════════"
fi
```

## Add Beads to Convoy

```bash
if [ "$SUBCOMMAND" = "add" ]; then
    CONVOY_ID=$(echo "$CONVOY_ARGS" | awk '{print $1}')
    BEAD_IDS=$(echo "$CONVOY_ARGS" | cut -d' ' -f2-)
    
    CONVOY_FILE=".speckle/convoys/${CONVOY_ID}.json"
    
    if [ ! -f "$CONVOY_FILE" ]; then
        log_error "Convoy not found: $CONVOY_ID"
        exit 1
    fi
    
    for bead_id in $BEAD_IDS; do
        # Verify bead exists
        if ! bd show "$bead_id" &>/dev/null; then
            log_warn "Bead not found: $bead_id (skipping)"
            continue
        fi
        
        # Add to convoy (avoid duplicates)
        EXISTING=$(jq -r ".beads | index(\"$bead_id\")" "$CONVOY_FILE")
        if [ "$EXISTING" != "null" ]; then
            log_warn "Bead already in convoy: $bead_id"
            continue
        fi
        
        # Add bead
        jq ".beads += [\"$bead_id\"] | .progress.total = (.beads | length)" "$CONVOY_FILE" > "${CONVOY_FILE}.tmp"
        mv "${CONVOY_FILE}.tmp" "$CONVOY_FILE"
        
        # Add convoy label to bead
        bd update "$bead_id" --add-label "convoy:$CONVOY_ID" 2>/dev/null || true
        
        log_success "Added $bead_id to convoy $CONVOY_ID"
    done
    
    # Update progress
    convoy_update_progress "$CONVOY_ID"
fi
```

## Assign Convoy

```bash
if [ "$SUBCOMMAND" = "assign" ]; then
    CONVOY_ID=$(echo "$CONVOY_ARGS" | awk '{print $1}')
    WORKER=$(echo "$CONVOY_ARGS" | grep -oP '(?<=--worker\s)\S+' || echo "")
    
    CONVOY_FILE=".speckle/convoys/${CONVOY_ID}.json"
    
    if [ ! -f "$CONVOY_FILE" ]; then
        log_error "Convoy not found: $CONVOY_ID"
        exit 1
    fi
    
    if [ -z "$WORKER" ]; then
        WORKER="${USER:-agent}"
    fi
    
    # Update convoy
    jq ".assigned_to = \"$WORKER\" | .status = \"in_progress\"" "$CONVOY_FILE" > "${CONVOY_FILE}.tmp"
    mv "${CONVOY_FILE}.tmp" "$CONVOY_FILE"
    
    log_success "Assigned convoy $CONVOY_ID to $WORKER"
    
    # Show convoy details
    echo ""
    convoy_show "$CONVOY_ID"
fi
```

## Close Convoy

```bash
if [ "$SUBCOMMAND" = "close" ]; then
    CONVOY_ID="$CONVOY_ARGS"
    CONVOY_FILE=".speckle/convoys/${CONVOY_ID}.json"
    
    if [ ! -f "$CONVOY_FILE" ]; then
        log_error "Convoy not found: $CONVOY_ID"
        exit 1
    fi
    
    # Check all beads are closed
    OPEN_COUNT=$(jq -r '.beads[]' "$CONVOY_FILE" | while read -r bead_id; do
        STATUS=$(bd show "$bead_id" --json 2>/dev/null | jq -r '.status')
        [ "$STATUS" != "closed" ] && echo "$bead_id"
    done | wc -l | tr -d ' ')
    
    if [ "$OPEN_COUNT" -gt 0 ]; then
        log_warn "Convoy has $OPEN_COUNT unclosed beads"
        echo "Use --force to close anyway"
        
        if [[ "$CONVOY_ARGS" != *"--force"* ]]; then
            exit 1
        fi
    fi
    
    # Close convoy
    jq ".status = \"completed\" | .completed_at = \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"" "$CONVOY_FILE" > "${CONVOY_FILE}.tmp"
    mv "${CONVOY_FILE}.tmp" "$CONVOY_FILE"
    
    log_success "Closed convoy: $CONVOY_ID"
fi
```

## Status Dashboard

```bash
if [ "$SUBCOMMAND" = "status" ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "📊 Convoy Status Dashboard"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    TOTAL_CONVOYS=0
    OPEN_CONVOYS=0
    IN_PROGRESS_CONVOYS=0
    COMPLETED_CONVOYS=0
    TOTAL_BEADS=0
    COMPLETED_BEADS=0
    
    for convoy_file in .speckle/convoys/*.json; do
        [ -f "$convoy_file" ] || continue
        
        ((TOTAL_CONVOYS++))
        STATUS=$(jq -r '.status' "$convoy_file")
        BEADS=$(jq -r '.progress.total' "$convoy_file")
        DONE=$(jq -r '.progress.completed' "$convoy_file")
        
        case "$STATUS" in
            open) ((OPEN_CONVOYS++)) ;;
            in_progress) ((IN_PROGRESS_CONVOYS++)) ;;
            completed) ((COMPLETED_CONVOYS++)) ;;
        esac
        
        TOTAL_BEADS=$((TOTAL_BEADS + BEADS))
        COMPLETED_BEADS=$((COMPLETED_BEADS + DONE))
    done
    
    echo "Convoys"
    echo "  Total:       $TOTAL_CONVOYS"
    echo "  Open:        $OPEN_CONVOYS"
    echo "  In Progress: $IN_PROGRESS_CONVOYS"
    echo "  Completed:   $COMPLETED_CONVOYS"
    echo ""
    echo "Beads"
    echo "  Total:       $TOTAL_BEADS"
    echo "  Completed:   $COMPLETED_BEADS"
    
    if [ "$TOTAL_BEADS" -gt 0 ]; then
        PERCENT=$((COMPLETED_BEADS * 100 / TOTAL_BEADS))
        echo "  Progress:    ${PERCENT}%"
    fi
    
    echo ""
    echo "═══════════════════════════════════════════════════════════"
fi
```

## Helper Functions Reference

The convoy.sh script provides:

- `convoy_add_bead(convoy_id, bead_id)` - Add bead to convoy
- `convoy_remove_bead(convoy_id, bead_id)` - Remove bead from convoy
- `convoy_update_progress(convoy_id)` - Refresh progress counts
- `convoy_get_next_bead(convoy_id)` - Get next ready bead in convoy
- `convoy_show(convoy_id)` - Display convoy details
