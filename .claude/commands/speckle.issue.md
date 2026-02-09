---
description: Create a GitHub issue using a guided, spec-driven workflow
---

# Speckle Issue

Guided issue creation that integrates with beads tracking and optionally links to specs.

## Arguments

```text
$ARGUMENTS
```

The text after `/speckle.issue` is the issue title/description.

Example: `/speckle.issue "Add dark mode support"`

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

## Parse Input

```bash
ISSUE_TITLE="$ARGUMENTS"

# If no title provided, prompt for interactive mode
if [ -z "$ISSUE_TITLE" ]; then
    echo "📝 Guided Issue Creation"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    read -p "Issue title: " ISSUE_TITLE
    
    if [ -z "$ISSUE_TITLE" ]; then
        log_error "Issue title is required"
        exit 1
    fi
fi

echo ""
echo "📝 Creating issue: $ISSUE_TITLE"
echo ""
```

## Classify Issue Type

```bash
echo "Select issue type:"
echo "  1) feature  - New functionality"
echo "  2) bug      - Something isn't working"
echo "  3) enhancement - Improvement to existing functionality"
echo "  4) chore    - Maintenance or housekeeping"
echo "  5) docs     - Documentation"
echo ""
read -p "Type [1-5]: " TYPE_CHOICE

case "$TYPE_CHOICE" in
    1|feature)   ISSUE_TYPE="feature" ;;
    2|bug)       ISSUE_TYPE="bug" ;;
    3|enhancement) ISSUE_TYPE="enhancement" ;;
    4|chore)     ISSUE_TYPE="chore" ;;
    5|docs)      ISSUE_TYPE="docs" ;;
    *)           ISSUE_TYPE="feature" ;;
esac

echo "   Type: $ISSUE_TYPE"
```

## Collect Details

```bash
# Severity/Priority (for bugs)
if [ "$ISSUE_TYPE" = "bug" ]; then
    echo ""
    echo "Bug severity:"
    echo "  1) critical - Production down, data loss"
    echo "  2) high     - Major feature broken"
    echo "  3) medium   - Feature impaired but workaround exists"
    echo "  4) low      - Minor issue"
    echo ""
    read -p "Severity [1-4]: " SEV_CHOICE
    
    case "$SEV_CHOICE" in
        1|critical) SEVERITY="critical"; PRIORITY=0 ;;
        2|high)     SEVERITY="high"; PRIORITY=1 ;;
        3|medium)   SEVERITY="medium"; PRIORITY=2 ;;
        4|low)      SEVERITY="low"; PRIORITY=3 ;;
        *)          SEVERITY="medium"; PRIORITY=2 ;;
    esac
    
    echo "   Severity: $SEVERITY"
else
    PRIORITY=2
fi

# Description
echo ""
echo "Enter description (press Enter twice to finish):"
DESCRIPTION=""
while IFS= read -r line; do
    [ -z "$line" ] && break
    DESCRIPTION="${DESCRIPTION}${line}
"
done

# Labels
echo ""
read -p "Additional labels (comma-separated, or empty): " EXTRA_LABELS
```

## Determine Spec Linking

```bash
echo ""
echo "Link to specification?"
echo "  1) No spec needed - Simple issue"
echo "  2) Create new spec - Complex feature requiring planning"
echo "  3) Link existing spec - Connect to existing spec"
echo ""
read -p "Spec linking [1-3]: " SPEC_CHOICE

SPEC_LINK=""
CREATE_SPEC=false

case "$SPEC_CHOICE" in
    2)
        CREATE_SPEC=true
        echo ""
        echo "A spec will be created after the issue."
        echo "Use /speckit.specify to develop the specification."
        ;;
    3)
        echo ""
        echo "Available specs:"
        find specs -maxdepth 1 -type d -name "[0-9]*-*" 2>/dev/null | while read -r spec; do
            echo "  - $(basename "$spec")"
        done
        echo ""
        read -p "Spec name (e.g., 001-feature-name): " SPEC_NAME
        if [ -d "specs/$SPEC_NAME" ]; then
            SPEC_LINK="specs/$SPEC_NAME"
            echo "   Linked to: $SPEC_LINK"
        else
            log_warn "Spec not found, skipping link"
        fi
        ;;
esac
```

## Build Issue Body

```bash
# Select template based on type
TEMPLATE_PATH=".github/ISSUE_TEMPLATE/${ISSUE_TYPE}.md"
if [ -f "$TEMPLATE_PATH" ]; then
    # Use template as base
    BODY=$(cat "$TEMPLATE_PATH" | sed '/^---$/,/^---$/d')  # Remove front matter
else
    # Generate default body based on type
    case "$ISSUE_TYPE" in
        feature)
            BODY="## Summary

${DESCRIPTION:-Describe the feature...}

## Motivation

Why is this feature needed?

## Proposed Solution

How should this be implemented?

## Acceptance Criteria

- [ ] Criteria 1
- [ ] Criteria 2

## Additional Context

Add any other context or screenshots here."
            ;;
        bug)
            BODY="## Bug Description

${DESCRIPTION:-Describe the bug...}

## Steps to Reproduce

1. Step 1
2. Step 2
3. Step 3

## Expected Behavior

What should happen?

## Actual Behavior

What actually happens?

## Environment

- OS: 
- Version: 

## Severity

**${SEVERITY:-medium}**

## Additional Context

Add any other context or screenshots here."
            ;;
        enhancement)
            BODY="## Summary

${DESCRIPTION:-Describe the enhancement...}

## Current Behavior

How does it work now?

## Proposed Improvement

How should it work?

## Benefits

Why is this improvement valuable?

## Additional Context

Add any other context here."
            ;;
        chore)
            BODY="## Summary

${DESCRIPTION:-Describe the task...}

## Tasks

- [ ] Task 1
- [ ] Task 2

## Additional Context

Add any other context here."
            ;;
        docs)
            BODY="## Summary

${DESCRIPTION:-Describe the documentation needed...}

## Scope

What documentation needs to be created or updated?

## Sections

- [ ] Section 1
- [ ] Section 2

## Additional Context

Add any other context here."
            ;;
    esac
fi

# Add spec reference if linked
if [ -n "$SPEC_LINK" ]; then
    BODY="${BODY}

---

## Related Specification

📁 See [\`$SPEC_LINK\`]($SPEC_LINK/) for detailed specification."
fi

# Add Speckle footer
BODY="${BODY}

---
*Created via Speckle issue workflow*"
```

## Build Labels

```bash
# Start with type label
LABELS="$ISSUE_TYPE"

# Add severity for bugs
if [ "$ISSUE_TYPE" = "bug" ] && [ -n "$SEVERITY" ]; then
    LABELS="$LABELS,severity:$SEVERITY"
fi

# Add extra labels
if [ -n "$EXTRA_LABELS" ]; then
    LABELS="$LABELS,$EXTRA_LABELS"
fi

# Add spec label if linked
if [ -n "$SPEC_LINK" ]; then
    SPEC_NAME=$(basename "$SPEC_LINK")
    LABELS="$LABELS,spec:$SPEC_NAME"
fi

echo ""
echo "📋 Labels: $LABELS"
```

## Create GitHub Issue

```bash
echo ""
echo "Creating GitHub issue..."

# Create the issue
GH_ISSUE_URL=$(gh issue create \
    --title "$ISSUE_TITLE" \
    --body "$BODY" \
    --label "$LABELS" 2>&1)

if [ $? -ne 0 ]; then
    log_error "Failed to create GitHub issue"
    echo "$GH_ISSUE_URL"
    exit 1
fi

# Extract issue number
GH_ISSUE_NUM=$(echo "$GH_ISSUE_URL" | grep -oE '[0-9]+$')

echo ""
log_success "GitHub issue created: $GH_ISSUE_URL"
```

## Sync to Beads

```bash
echo ""
echo "Syncing to beads..."

# Map issue type to beads type
case "$ISSUE_TYPE" in
    feature)     BD_TYPE="feature" ;;
    bug)         BD_TYPE="bug" ;;
    enhancement) BD_TYPE="task" ;;
    chore)       BD_TYPE="task" ;;
    docs)        BD_TYPE="task" ;;
esac

# Create beads issue
BD_ISSUE_ID=$(bd create "$ISSUE_TITLE" \
    --type "$BD_TYPE" \
    --priority "${PRIORITY:-2}" \
    --labels "speckle,gh-$GH_ISSUE_NUM,$LABELS" \
    --description "## $ISSUE_TITLE

${DESCRIPTION:-See GitHub issue for details.}

### GitHub Reference
- Issue: #$GH_ISSUE_NUM
- URL: $GH_ISSUE_URL

---
*Synced from GitHub via Speckle*" 2>&1 | grep -oE 'speckle-[a-z0-9]+')

if [ -n "$BD_ISSUE_ID" ]; then
    log_success "Beads issue created: $BD_ISSUE_ID"
    
    # Add cross-reference comment to GitHub issue
    gh issue comment "$GH_ISSUE_NUM" --body "🔗 Tracked in beads: \`$BD_ISSUE_ID\`"
else
    log_warn "Could not create beads issue (non-fatal)"
fi
```

## Handle Spec Creation

```bash
if [ "$CREATE_SPEC" = true ]; then
    echo ""
    echo "📐 Spec creation suggested"
    echo ""
    echo "Next steps:"
    echo "  1. Create feature branch:"
    echo "     bd formula speckle-feature \"$ISSUE_TITLE\""
    echo ""
    echo "  2. Or manually create spec:"
    echo "     /speckit.specify \"$ISSUE_TITLE\""
fi
```

## Summary

```bash
echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ Issue created successfully!"
echo ""
echo "📋 Summary:"
echo "   Title: $ISSUE_TITLE"
echo "   Type: $ISSUE_TYPE"
echo "   GitHub: $GH_ISSUE_URL"
[ -n "$BD_ISSUE_ID" ] && echo "   Beads: $BD_ISSUE_ID"
[ -n "$SPEC_LINK" ] && echo "   Spec: $SPEC_LINK"
echo ""
echo "🎯 Next steps:"
if [ "$ISSUE_TYPE" = "bug" ]; then
    echo "   1. Reproduce the issue"
    echo "   2. Create a fix branch: /speckle.bugfix \"$ISSUE_TITLE\""
elif [ "$CREATE_SPEC" = true ]; then
    echo "   1. Create feature: bd formula speckle-feature \"$ISSUE_TITLE\""
    echo "   2. Develop spec: /speckit.specify"
    echo "   3. Plan: /speckit.plan"
    echo "   4. Tasks: /speckit.tasks"
    echo "   5. Sync: /speckle.sync"
else
    echo "   1. Start working on the issue"
    echo "   2. Update status: bd update $BD_ISSUE_ID --status in_progress"
    echo "   3. When done: bd close $BD_ISSUE_ID"
fi
echo "════════════════════════════════════════════════════════════"
```
