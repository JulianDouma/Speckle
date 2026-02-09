---
description: Start an urgent hotfix workflow with high priority tracking
---

# Speckle Hotfix

Create a hotfix branch and high-priority issue for urgent production fixes.

## Arguments

```text
$ARGUMENTS
```

The text after `/speckle.hotfix` is the hotfix description.

Example: `/speckle.hotfix "Critical: Payment processing failing"`

## Prerequisites

```bash
# Hotfixes should branch from main or a release tag
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
if [ "$BRANCH" != "main" ] && [ "$BRANCH" != "master" ]; then
    echo "⚠️  Not on main branch (currently: $BRANCH)"
    echo "   Hotfixes should branch from main for production fixes"
    echo ""
    git checkout main 2>/dev/null || git checkout master 2>/dev/null
fi
```

## Parse Input

```bash
HOTFIX_DESCRIPTION="$ARGUMENTS"

if [ -z "$HOTFIX_DESCRIPTION" ]; then
    echo "❌ No hotfix description provided"
    echo ""
    echo "Usage: /speckle.hotfix \"Description of urgent issue\""
    exit 1
fi

# Generate branch name with hotfix prefix
HOTFIX_SLUG=$(echo "$HOTFIX_DESCRIPTION" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | cut -c1-40)
BRANCH_NAME="hotfix-$HOTFIX_SLUG"

echo "🔥 HOTFIX: $HOTFIX_DESCRIPTION"
echo "📁 Branch: $BRANCH_NAME"
```

## Create Branch and Issue

```bash
# Create and switch to hotfix branch
git checkout -b "$BRANCH_NAME"

# Create high-priority issue
ISSUE_ID=$(bd create "HOTFIX: $HOTFIX_DESCRIPTION" \
    --type bug \
    --priority 1 \
    --labels "speckle,hotfix,critical,urgent" \
    --description "## 🔥 HOTFIX

**Description:** $HOTFIX_DESCRIPTION

### Priority: CRITICAL

### Hotfix Checklist
- [ ] Identify root cause
- [ ] Implement minimal fix
- [ ] Test fix locally
- [ ] Deploy to staging
- [ ] Deploy to production
- [ ] Post-mortem (after stable)

### Context
- Branch: $BRANCH_NAME
- Created: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- Severity: Critical

---
*Created by Speckle hotfix workflow*" 2>&1 | grep -oE 'speckle-[a-z0-9]+')

echo ""
echo "🔥 HOTFIX workflow started"
echo ""
echo "⚠️  Issue: $ISSUE_ID (Priority: P1 CRITICAL)"
echo "📁 Branch: $BRANCH_NAME"
echo ""
echo "⏱️  Hotfix protocol:"
echo "  1. Fix the issue (minimal changes only)"
echo "  2. Test locally"
echo "  3. Deploy immediately after review"
echo "  4. Run: bd close $ISSUE_ID"
echo "  5. Schedule post-mortem"
```
