---
description: Show current feature progress with task status and recent implementation activity
---

# Speckle Status

Display the current feature's progress including task completion status and recent implementation comments.

## Arguments

```text
$ARGUMENTS
```

Options:
- No args: Show status for current feature branch
- `--all`: Show all open tasks across all features
- `--verbose`: Include full comment history
- `--by-story`: Group progress by story labels instead of phases

## Environment Check

```bash
# Verify beads is available
if ! command -v bd &>/dev/null; then
    echo "❌ Beads not installed"
    exit 1
fi

# Get current branch info
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
echo "📍 Branch: $BRANCH"
```

## Feature Detection

```bash
# Check if on a feature branch
if [[ "$BRANCH" =~ ^[0-9]{3}- ]]; then
    PREFIX="${BRANCH:0:3}"
    FEATURE_DIR=$(find specs -maxdepth 1 -type d -name "${PREFIX}-*" 2>/dev/null | head -1)
    
    if [ -n "$FEATURE_DIR" ]; then
        echo "📁 Feature: $FEATURE_DIR"
        FEATURE_NAME=$(basename "$FEATURE_DIR")
    else
        echo "⚠️  No specs directory found for branch $BRANCH"
        FEATURE_NAME="$BRANCH"
    fi
else
    echo "ℹ️  Not on a feature branch"
    FEATURE_NAME="(no feature)"
fi
```

## Task Summary

```bash
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📊 Feature Status: $FEATURE_NAME"
echo "═══════════════════════════════════════════════════════════"

# Get issue counts by status
TOTAL=$(bd list 2>/dev/null | grep -c "speckle-" || echo 0)
OPEN=$(bd list --status open 2>/dev/null | grep -c "speckle-" || echo 0)
IN_PROGRESS=$(bd list --status in_progress 2>/dev/null | grep -c "speckle-" || echo 0)
CLOSED=$(bd list --status closed 2>/dev/null | grep -c "speckle-" || echo 0)

echo ""
echo "📋 Tasks:"
echo "   Total:       $TOTAL"
echo "   ✅ Closed:    $CLOSED"
echo "   🔄 In Progress: $IN_PROGRESS"
echo "   ⏳ Open:      $OPEN"

# Calculate progress percentage
if [ "$TOTAL" -gt 0 ]; then
    PROGRESS=$((CLOSED * 100 / TOTAL))
    echo ""
    echo "   Progress: $PROGRESS%"
    
    # Visual progress bar
    FILLED=$((PROGRESS / 5))
    EMPTY=$((20 - FILLED))
    BAR=$(printf '█%.0s' $(seq 1 $FILLED 2>/dev/null) || echo "")
    BAR+=$(printf '░%.0s' $(seq 1 $EMPTY 2>/dev/null) || echo "")
    echo "   [$BAR]"
fi
```

## Progress by Phase

```bash
# Source the labels helper
source ".speckle/scripts/labels.sh"

echo ""
echo "═══════════════════════════════════════════════════════════"

# Check if --by-story flag is set
if [[ "$ARGUMENTS" == *"--by-story"* ]]; then
    echo "📈 Progress by Story"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    # Get unique story labels
    STORY_LABELS=$(bd list 2>/dev/null | grep -oE 'story:[a-z0-9-]+' | sort -u || echo "")
    
    if [ -z "$STORY_LABELS" ]; then
        echo "   No story labels found"
    else
        printf "   %-20s %6s %6s %8s\n" "Story" "Total" "Done" "Progress"
        printf "   %-20s %6s %6s %8s\n" "────────────────────" "──────" "──────" "────────"
        
        echo "$STORY_LABELS" | while read -r label; do
            if [ -n "$label" ]; then
                LABEL_TOTAL=$(count_by_label "$label" "")
                LABEL_CLOSED=$(count_by_label "$label" "closed")
                
                if [ "$LABEL_TOTAL" -gt 0 ]; then
                    LABEL_PCT=$((LABEL_CLOSED * 100 / LABEL_TOTAL))
                else
                    LABEL_PCT=0
                fi
                
                # Format the label for display (remove "story:" prefix)
                DISPLAY_NAME="${label#story:}"
                
                printf "   %-20s %6d %6d %7d%%\n" "$DISPLAY_NAME" "$LABEL_TOTAL" "$LABEL_CLOSED" "$LABEL_PCT"
            fi
        done
    fi
else
    echo "📈 Progress by Phase"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    # Get unique phase labels
    PHASE_LABELS=$(get_phase_labels)
    
    if [ -z "$PHASE_LABELS" ]; then
        echo "   No phase labels found"
    else
        printf "   %-20s %6s %6s %8s\n" "Phase" "Total" "Done" "Progress"
        printf "   %-20s %6s %6s %8s\n" "────────────────────" "──────" "──────" "────────"
        
        echo "$PHASE_LABELS" | while read -r label; do
            if [ -n "$label" ]; then
                LABEL_TOTAL=$(count_by_label "$label" "")
                LABEL_CLOSED=$(count_by_label "$label" "closed")
                
                if [ "$LABEL_TOTAL" -gt 0 ]; then
                    LABEL_PCT=$((LABEL_CLOSED * 100 / LABEL_TOTAL))
                else
                    LABEL_PCT=0
                fi
                
                # Format the label for display (remove "phase:" prefix)
                DISPLAY_NAME="${label#phase:}"
                
                printf "   %-20s %6d %6d %7d%%\n" "$DISPLAY_NAME" "$LABEL_TOTAL" "$LABEL_CLOSED" "$LABEL_PCT"
            fi
        done
    fi
fi
```

## In-Progress Tasks

```bash
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🔄 Currently In Progress"
echo "═══════════════════════════════════════════════════════════"

# List in-progress tasks with details
IN_PROGRESS_LIST=$(bd list --status in_progress 2>/dev/null | grep "speckle-" || echo "")

if [ -z "$IN_PROGRESS_LIST" ]; then
    echo ""
    echo "   No tasks currently in progress"
    echo "   Run: bd ready  (to see available work)"
else
    echo "$IN_PROGRESS_LIST" | while read -r line; do
        # Extract issue ID
        ISSUE_ID=$(echo "$line" | grep -oE 'speckle-[a-z0-9]+' | head -1)
        if [ -n "$ISSUE_ID" ]; then
            echo ""
            echo "   $line"
            
            # Try to get most recent comment
            LAST_COMMENT=$(bd comments "$ISSUE_ID" 2>/dev/null | tail -5 || echo "")
            if [ -n "$LAST_COMMENT" ]; then
                echo "   └─ Recent activity:"
                echo "$LAST_COMMENT" | sed 's/^/      /'
            fi
        fi
    done
fi
```

## Ready Tasks

```bash
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "⏳ Ready to Start"
echo "═══════════════════════════════════════════════════════════"

READY_LIST=$(bd ready 2>/dev/null | head -10 || echo "")

if [ -z "$READY_LIST" ]; then
    echo ""
    echo "   ✅ All tasks complete or blocked!"
else
    echo ""
    echo "$READY_LIST" | sed 's/^/   /'
fi
```

## Next Steps Guidance

```bash
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "💡 Next Steps"
echo "═══════════════════════════════════════════════════════════"
echo ""

if [ "$IN_PROGRESS" -gt 0 ]; then
    echo "   You have $IN_PROGRESS task(s) in progress."
    echo "   → Continue with: /speckle.implement"
    echo "   → Add notes with: /speckle.progress \"your note\""
elif [ "$OPEN" -gt 0 ]; then
    echo "   Ready to start new work!"
    echo "   → Start next task: /speckle.implement"
else
    echo "   🎉 All tasks complete!"
    echo "   → Review changes: git log --oneline"
    echo "   → Merge when ready: git checkout main && git merge $BRANCH"
fi
```
