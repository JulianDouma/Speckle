---
description: Review and prioritize issues across GitHub and beads
---

# Speckle Triage

Review, prioritize, and sync issues between GitHub and beads.

## Arguments

```text
$ARGUMENTS
```

Options:
- `--sync` - Sync all open GitHub issues to beads
- `--review` - Interactive review of unprocessed issues
- `--stale` - Find stale issues that need attention

Example: `/speckle.triage --review`

## Prerequisites

```bash
# Source common utilities
source ".speckle/scripts/common.sh"

# Check GitHub CLI is available
if ! command -v gh &> /dev/null; then
    log_error "GitHub CLI not installed"
    echo "Install from: https://cli.github.com"
    exit 1
fi

# Check beads is available
if ! check_beads; then
    exit 1
fi

# Verify gh is authenticated
if ! gh auth status &>/dev/null; then
    log_error "GitHub CLI not authenticated"
    echo "Run: gh auth login"
    exit 1
fi
```

## Parse Arguments

```bash
ARGS="$ARGUMENTS"
ACTION=""

if [[ "$ARGS" == *"--sync"* ]]; then
    ACTION="sync"
elif [[ "$ARGS" == *"--review"* ]]; then
    ACTION="review"
elif [[ "$ARGS" == *"--stale"* ]]; then
    ACTION="stale"
else
    # Default: show dashboard
    ACTION="dashboard"
fi
```

## Dashboard View

```bash
if [ "$ACTION" = "dashboard" ]; then
    echo "📊 Speckle Issue Triage Dashboard"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    
    # Get GitHub issues count
    GH_OPEN=$(gh issue list --state open --json number --jq 'length' 2>/dev/null || echo "0")
    GH_BUGS=$(gh issue list --state open --label bug --json number --jq 'length' 2>/dev/null || echo "0")
    GH_FEATURES=$(gh issue list --state open --label feature --json number --jq 'length' 2>/dev/null || echo "0")
    
    # Get beads counts
    BD_OPEN=$(bd list --status open 2>/dev/null | wc -l | tr -d ' ')
    BD_IN_PROGRESS=$(bd list --status in_progress 2>/dev/null | wc -l | tr -d ' ')
    BD_BLOCKED=$(bd list --status blocked 2>/dev/null | wc -l | tr -d ' ')
    
    echo "📌 GitHub Issues"
    echo "   Open: $GH_OPEN"
    echo "   Bugs: $GH_BUGS"
    echo "   Features: $GH_FEATURES"
    echo ""
    echo "🔮 Beads Issues"
    echo "   Open: $BD_OPEN"
    echo "   In Progress: $BD_IN_PROGRESS"
    echo "   Blocked: $BD_BLOCKED"
    echo ""
    
    # Check for sync issues
    echo "⚠️  Potential Issues:"
    
    # Find GitHub issues not in beads
    UNSYNCED=0
    while IFS= read -r issue; do
        GH_NUM=$(echo "$issue" | jq -r '.number')
        # Check if beads has this issue
        if ! bd list 2>/dev/null | grep -q "gh-$GH_NUM"; then
            UNSYNCED=$((UNSYNCED + 1))
        fi
    done < <(gh issue list --state open --json number 2>/dev/null)
    
    if [ "$UNSYNCED" -gt 0 ]; then
        echo "   $UNSYNCED GitHub issue(s) not synced to beads"
        echo "   Run: /speckle.triage --sync"
    else
        echo "   None - all issues synced!"
    fi
    
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "Actions:"
    echo "  /speckle.triage --sync    Sync GitHub issues to beads"
    echo "  /speckle.triage --review  Interactive issue review"
    echo "  /speckle.triage --stale   Find stale issues"
    
    exit 0
fi
```

## Sync Action

```bash
if [ "$ACTION" = "sync" ]; then
    echo "🔄 Syncing GitHub Issues to Beads"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    
    SYNCED=0
    SKIPPED=0
    
    # Get all open GitHub issues
    gh issue list --state open --json number,title,labels,body --limit 100 2>/dev/null | jq -c '.[]' | while read -r issue; do
        GH_NUM=$(echo "$issue" | jq -r '.number')
        GH_TITLE=$(echo "$issue" | jq -r '.title')
        GH_LABELS=$(echo "$issue" | jq -r '.labels[].name' | tr '\n' ',' | sed 's/,$//')
        
        # Check if already synced
        if bd list 2>/dev/null | grep -q "gh-$GH_NUM"; then
            echo "⏭️  #$GH_NUM - Already synced"
            continue
        fi
        
        # Determine type from labels
        BD_TYPE="task"
        if echo "$GH_LABELS" | grep -qi "bug"; then
            BD_TYPE="bug"
        elif echo "$GH_LABELS" | grep -qi "feature"; then
            BD_TYPE="feature"
        fi
        
        # Determine priority from labels
        PRIORITY=2
        if echo "$GH_LABELS" | grep -qi "critical\|p0"; then
            PRIORITY=0
        elif echo "$GH_LABELS" | grep -qi "high\|p1"; then
            PRIORITY=1
        elif echo "$GH_LABELS" | grep -qi "low\|p3\|p4"; then
            PRIORITY=3
        fi
        
        # Create beads issue
        BD_ID=$(bd create "$GH_TITLE" \
            --type "$BD_TYPE" \
            --priority "$PRIORITY" \
            --labels "speckle,gh-$GH_NUM,$GH_LABELS" \
            --description "Synced from GitHub Issue #$GH_NUM

https://github.com/$(gh repo view --json nameWithOwner --jq '.nameWithOwner')/issues/$GH_NUM

---
*Synced by Speckle triage*" 2>&1 | grep -oE 'speckle-[a-z0-9]+')
        
        if [ -n "$BD_ID" ]; then
            echo "✅ #$GH_NUM -> $BD_ID: $GH_TITLE"
            SYNCED=$((SYNCED + 1))
        else
            echo "❌ #$GH_NUM - Failed to sync"
        fi
    done
    
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "✅ Sync complete"
    echo ""
    echo "Run \`bd ready\` to see available work"
    
    exit 0
fi
```

## Review Action

```bash
if [ "$ACTION" = "review" ]; then
    echo "📋 Interactive Issue Review"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    
    # Get open beads issues without priority action
    bd list --status open 2>/dev/null | head -20 | while read -r line; do
        # Extract issue ID (first word)
        ISSUE_ID=$(echo "$line" | awk '{print $1}')
        
        if [ -z "$ISSUE_ID" ]; then
            continue
        fi
        
        echo ""
        echo "────────────────────────────────────────────────────────────"
        bd show "$ISSUE_ID" 2>/dev/null | head -15
        echo ""
        
        echo "Actions for $ISSUE_ID:"
        echo "  1) Set priority (P0-P4)"
        echo "  2) Add labels"
        echo "  3) Start work (in_progress)"
        echo "  4) Block issue"
        echo "  5) Close issue"
        echo "  6) Skip"
        echo "  q) Quit review"
        echo ""
        read -p "Action [1-6/q]: " REVIEW_ACTION
        
        case "$REVIEW_ACTION" in
            1)
                read -p "Priority (0-4): " NEW_PRIORITY
                bd update "$ISSUE_ID" --priority "$NEW_PRIORITY"
                log_success "Priority updated"
                ;;
            2)
                read -p "Labels (comma-separated): " NEW_LABELS
                bd update "$ISSUE_ID" --labels "$NEW_LABELS"
                log_success "Labels added"
                ;;
            3)
                bd update "$ISSUE_ID" --status in_progress
                log_success "Started work on $ISSUE_ID"
                ;;
            4)
                read -p "Blocked by (issue ID or reason): " BLOCKED_BY
                bd update "$ISSUE_ID" --status blocked
                bd comment "$ISSUE_ID" "Blocked: $BLOCKED_BY"
                log_success "Issue blocked"
                ;;
            5)
                bd close "$ISSUE_ID"
                log_success "Issue closed"
                ;;
            6)
                echo "Skipped"
                ;;
            q|Q)
                echo "Review ended"
                exit 0
                ;;
        esac
    done
    
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "✅ Review complete"
    
    exit 0
fi
```

## Stale Action

```bash
if [ "$ACTION" = "stale" ]; then
    echo "🕸️  Stale Issue Detection"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    
    # Define stale threshold (14 days)
    STALE_DAYS=14
    STALE_THRESHOLD=$(date -v-${STALE_DAYS}d +%Y-%m-%d 2>/dev/null || date -d "$STALE_DAYS days ago" +%Y-%m-%d 2>/dev/null || echo "2026-01-26")
    
    echo "Finding issues not updated since $STALE_THRESHOLD..."
    echo ""
    
    # Check GitHub issues
    echo "📌 Stale GitHub Issues:"
    STALE_GH=$(gh issue list --state open --json number,title,updatedAt --jq ".[] | select(.updatedAt < \"${STALE_THRESHOLD}T00:00:00Z\") | \"  #\(.number) - \(.title)\"" 2>/dev/null)
    
    if [ -n "$STALE_GH" ]; then
        echo "$STALE_GH"
    else
        echo "  None found"
    fi
    
    echo ""
    echo "🔮 Stale Beads Issues (in_progress for too long):"
    
    # Get in_progress issues (beads doesn't have date filtering, so we list and check)
    bd list --status in_progress 2>/dev/null | while read -r line; do
        ISSUE_ID=$(echo "$line" | awk '{print $1}')
        if [ -n "$ISSUE_ID" ]; then
            echo "  $ISSUE_ID - Consider reviewing progress"
        fi
    done
    
    echo ""
    echo "🔮 Blocked Issues:"
    bd list --status blocked 2>/dev/null | while read -r line; do
        ISSUE_ID=$(echo "$line" | awk '{print $1}')
        if [ -n "$ISSUE_ID" ]; then
            TITLE=$(bd show "$ISSUE_ID" 2>/dev/null | grep -m1 "title:" | cut -d: -f2- | xargs)
            echo "  $ISSUE_ID - $TITLE"
        fi
    done
    
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "Recommendations:"
    echo "  - Review stale issues and close or update them"
    echo "  - Check blocked issues for unblocking opportunities"
    echo "  - Use /speckle.triage --review for interactive triage"
    
    exit 0
fi
```
