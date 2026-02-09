---
description: Start a bugfix workflow with lightweight tracking
---

# Speckle Bugfix

Create a bugfix branch and issue for tracking a bug fix.

## Arguments

```text
$ARGUMENTS
```

The text after `/speckle.bugfix` is the bug description.

Example: `/speckle.bugfix "Login timeout after 30 seconds"`

## Prerequisites

```bash
# Verify on main/master or a release branch
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
if [[ "$BRANCH" =~ ^[0-9]{3}- ]]; then
    echo "⚠️  Currently on feature branch: $BRANCH"
    echo "   Bugfixes should typically branch from main"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi
```

## Parse Input

```bash
BUG_DESCRIPTION="$ARGUMENTS"

if [ -z "$BUG_DESCRIPTION" ]; then
    echo "❌ No bug description provided"
    echo ""
    echo "Usage: /speckle.bugfix \"Description of the bug\""
    exit 1
fi

# Generate branch name
BUG_SLUG=$(echo "$BUG_DESCRIPTION" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | cut -c1-40)
BRANCH_NAME="fix-$BUG_SLUG"

echo "🐛 Bug: $BUG_DESCRIPTION"
echo "📁 Branch: $BRANCH_NAME"
```

## Create Branch and Issue

```bash
# Create and switch to bugfix branch
git checkout -b "$BRANCH_NAME"

# Create bug issue
ISSUE_ID=$(bd create "Bug: $BUG_DESCRIPTION" \
    --type bug \
    --priority 2 \
    --labels "speckle,bug,fix" \
    --description "## Bug Report

**Description:** $BUG_DESCRIPTION

### Fix Checklist
- [ ] Reproduce the bug
- [ ] Write failing test
- [ ] Implement fix
- [ ] Verify fix passes
- [ ] Update related tests

### Context
- Branch: $BRANCH_NAME
- Created: $(date -u +%Y-%m-%dT%H:%M:%SZ)

---
*Created by Speckle bugfix workflow*" 2>&1 | grep -oE 'speckle-[a-z0-9]+')

echo ""
echo "✅ Bugfix workflow started"
echo ""
echo "🐛 Issue: $ISSUE_ID"
echo "📁 Branch: $BRANCH_NAME"
echo ""
echo "Next steps:"
echo "  1. Reproduce the bug"
echo "  2. Write a failing test"
echo "  3. Fix the bug"
echo "  4. Run: bd close $ISSUE_ID"
echo "  5. Merge to main"
```
