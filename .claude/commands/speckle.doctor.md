---
description: Diagnose Speckle installation and configuration issues
---

# Speckle Doctor

Run diagnostics to check your Speckle installation and identify common issues.

## Arguments

```text
$ARGUMENTS
```

Options:
- No args: Run full diagnostic check
- `--fix`: Attempt to fix common issues automatically
- `--verbose`: Show detailed output for each check

## Overview

The doctor command checks:
1. Prerequisites (git, gh, bd, specify)
2. Directory structure (.speckle/, .claude/, .beads/)
3. File permissions and integrity
4. Configuration validity
5. Integration health (beads, git)

## System Check

```bash
echo ""
echo "════════════════════════════════════════════════════════════"
echo "🩺 Speckle Doctor"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Running diagnostics..."
echo ""

ISSUES=0
WARNINGS=0
FIX_MODE=false
VERBOSE=false

if [[ "$ARGUMENTS" == *"--fix"* ]]; then
    FIX_MODE=true
    echo "🔧 Fix mode enabled"
    echo ""
fi

if [[ "$ARGUMENTS" == *"--verbose"* ]]; then
    VERBOSE=true
fi
```

## Prerequisites Check

```bash
echo "═══════════════════════════════════════════════════════════"
echo "📦 Prerequisites"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check git
if command -v git &>/dev/null; then
    GIT_VERSION=$(git --version 2>/dev/null | head -1)
    echo "  ✅ git: $GIT_VERSION"
else
    echo "  ❌ git: NOT FOUND"
    echo "     → Install from https://git-scm.com/downloads"
    ((ISSUES++))
fi

# Check GitHub CLI
if command -v gh &>/dev/null; then
    GH_VERSION=$(gh --version 2>/dev/null | head -1)
    echo "  ✅ gh: $GH_VERSION"
    
    # Check if authenticated
    if gh auth status &>/dev/null 2>&1; then
        echo "     └─ Authenticated"
    else
        echo "     └─ ⚠️  Not authenticated (run: gh auth login)"
        ((WARNINGS++))
    fi
else
    echo "  ⚠️  gh: NOT FOUND (recommended)"
    echo "     → Install from https://cli.github.com"
    ((WARNINGS++))
fi

# Check Beads
if command -v bd &>/dev/null; then
    BD_VERSION=$(bd --version 2>/dev/null | head -1 || echo "installed")
    echo "  ✅ bd: $BD_VERSION"
else
    echo "  ⚠️  bd: NOT FOUND (recommended)"
    echo "     → Install from https://github.com/steveyegge/beads"
    ((WARNINGS++))
fi

# Check Spec-kit
if command -v specify &>/dev/null; then
    echo "  ✅ specify: installed"
else
    echo "  ℹ️  specify: NOT FOUND (optional)"
    echo "     → Install from https://github.com/github/spec-kit"
fi

# Check shell
CURRENT_SHELL=$(basename "${SHELL:-/bin/bash}")
echo ""
echo "  Shell: $CURRENT_SHELL"
```

## Directory Structure Check

```bash
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📁 Directory Structure"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check .speckle directory
if [ -d ".speckle" ]; then
    echo "  ✅ .speckle/"
    
    # Check subdirectories
    for subdir in scripts templates formulas; do
        if [ -d ".speckle/$subdir" ]; then
            FILE_COUNT=$(ls -1 ".speckle/$subdir" 2>/dev/null | wc -l | tr -d ' ')
            echo "     └─ $subdir/ ($FILE_COUNT files)"
        else
            echo "     └─ ⚠️  $subdir/ MISSING"
            ((WARNINGS++))
            if [ "$FIX_MODE" = true ]; then
                mkdir -p ".speckle/$subdir"
                echo "        → Created"
            fi
        fi
    done
else
    echo "  ❌ .speckle/ NOT FOUND"
    echo "     → Run install.sh to set up Speckle"
    ((ISSUES++))
    if [ "$FIX_MODE" = true ]; then
        mkdir -p ".speckle/scripts" ".speckle/templates" ".speckle/formulas"
        echo "     → Created directory structure"
    fi
fi

# Check .claude directory
if [ -d ".claude/commands" ]; then
    COMMAND_COUNT=$(ls -1 ".claude/commands"/speckle*.md 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✅ .claude/commands/ ($COMMAND_COUNT speckle commands)"
else
    echo "  ⚠️  .claude/commands/ NOT FOUND"
    ((WARNINGS++))
    if [ "$FIX_MODE" = true ]; then
        mkdir -p ".claude/commands"
        echo "     → Created"
    fi
fi

# Check .beads directory
if [ -d ".beads" ]; then
    echo "  ✅ .beads/"
    
    if [ -f ".beads/config.toml" ]; then
        echo "     └─ config.toml exists"
    else
        echo "     └─ ⚠️  config.toml MISSING (run: bd init)"
        ((WARNINGS++))
    fi
    
    if [ -d ".beads/formulas" ]; then
        FORMULA_COUNT=$(ls -1 ".beads/formulas"/*.toml 2>/dev/null | wc -l | tr -d ' ')
        echo "     └─ formulas/ ($FORMULA_COUNT formulas)"
    fi
else
    echo "  ⚠️  .beads/ NOT FOUND"
    echo "     → Run: bd init"
    ((WARNINGS++))
    if [ "$FIX_MODE" = true ] && command -v bd &>/dev/null; then
        bd init 2>/dev/null || true
        echo "     → Initialized beads"
    fi
fi

# Check specs directory
if [ -d "specs" ]; then
    SPEC_COUNT=$(find specs -maxdepth 1 -type d | wc -l | tr -d ' ')
    SPEC_COUNT=$((SPEC_COUNT - 1))  # Exclude specs/ itself
    echo "  ✅ specs/ ($SPEC_COUNT features)"
else
    echo "  ℹ️  specs/ NOT FOUND (created on first feature)"
fi
```

## Scripts Check

```bash
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🔧 Scripts & Helpers"
echo "═══════════════════════════════════════════════════════════"
echo ""

EXPECTED_SCRIPTS=(common.sh comments.sh labels.sh epics.sh)

for script in "${EXPECTED_SCRIPTS[@]}"; do
    SCRIPT_PATH=".speckle/scripts/$script"
    if [ -f "$SCRIPT_PATH" ]; then
        if [ -x "$SCRIPT_PATH" ]; then
            echo "  ✅ $script (executable)"
        else
            echo "  ⚠️  $script (not executable)"
            ((WARNINGS++))
            if [ "$FIX_MODE" = true ]; then
                chmod +x "$SCRIPT_PATH"
                echo "     → Fixed permissions"
            fi
        fi
        
        # Source check for syntax errors
        if [ "$VERBOSE" = true ]; then
            if bash -n "$SCRIPT_PATH" 2>/dev/null; then
                echo "     └─ Syntax OK"
            else
                echo "     └─ ❌ Syntax error!"
                ((ISSUES++))
            fi
        fi
    else
        echo "  ⚠️  $script MISSING"
        ((WARNINGS++))
    fi
done
```

## Commands Check

```bash
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📋 Speckle Commands"
echo "═══════════════════════════════════════════════════════════"
echo ""

EXPECTED_COMMANDS=(
    "speckle.sync.md:Sync tasks with beads"
    "speckle.implement.md:Implement tasks"
    "speckle.status.md:Show progress"
    "speckle.progress.md:Add progress notes"
    "speckle.bugfix.md:Bugfix workflow"
    "speckle.hotfix.md:Hotfix workflow"
    "speckle.doctor.md:This diagnostic"
)

for entry in "${EXPECTED_COMMANDS[@]}"; do
    CMD_FILE="${entry%%:*}"
    CMD_DESC="${entry#*:}"
    CMD_PATH=".claude/commands/$CMD_FILE"
    
    if [ -f "$CMD_PATH" ]; then
        echo "  ✅ $CMD_FILE"
        if [ "$VERBOSE" = true ]; then
            echo "     └─ $CMD_DESC"
        fi
    else
        echo "  ⚠️  $CMD_FILE MISSING"
        ((WARNINGS++))
    fi
done
```

## Git Integration Check

```bash
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🔗 Git Integration"
echo "═══════════════════════════════════════════════════════════"
echo ""

if [ -d ".git" ]; then
    echo "  ✅ Git repository detected"
    
    # Check current branch
    BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    echo "     └─ Branch: $BRANCH"
    
    # Check remote
    REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
    if [ -n "$REMOTE" ]; then
        echo "     └─ Remote: $REMOTE"
    else
        echo "     └─ ⚠️  No remote configured"
        ((WARNINGS++))
    fi
    
    # Check for uncommitted changes
    if git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null; then
        echo "     └─ Working tree clean"
    else
        CHANGED=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
        echo "     └─ ℹ️  $CHANGED uncommitted change(s)"
    fi
else
    echo "  ⚠️  Not a git repository"
    echo "     → Run: git init"
    ((WARNINGS++))
fi
```

## Beads Integration Check

```bash
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📝 Beads Integration"
echo "═══════════════════════════════════════════════════════════"
echo ""

if command -v bd &>/dev/null && [ -d ".beads" ]; then
    # Check if beads is functional
    if bd list &>/dev/null 2>&1; then
        ISSUE_COUNT=$(bd list 2>/dev/null | grep -c "speckle-" || echo 0)
        echo "  ✅ Beads operational"
        echo "     └─ $ISSUE_COUNT Speckle issue(s)"
        
        # Check for orphaned issues
        OPEN_COUNT=$(bd list --status open 2>/dev/null | grep -c "speckle-" || echo 0)
        IN_PROGRESS=$(bd list --status in_progress 2>/dev/null | grep -c "speckle-" || echo 0)
        
        if [ "$IN_PROGRESS" -gt 3 ]; then
            echo "     └─ ⚠️  Many in-progress issues ($IN_PROGRESS)"
            ((WARNINGS++))
        else
            echo "     └─ In progress: $IN_PROGRESS"
        fi
        
        echo "     └─ Open: $OPEN_COUNT"
    else
        echo "  ⚠️  Beads command failed"
        echo "     → Check .beads/config.toml"
        ((WARNINGS++))
    fi
else
    echo "  ℹ️  Beads not configured"
fi
```

## Summary

```bash
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📊 Diagnosis Summary"
echo "═══════════════════════════════════════════════════════════"
echo ""

if [ "$ISSUES" -eq 0 ] && [ "$WARNINGS" -eq 0 ]; then
    echo "  🎉 All checks passed! Speckle is healthy."
elif [ "$ISSUES" -eq 0 ]; then
    echo "  ✅ No critical issues found"
    echo "  ⚠️  $WARNINGS warning(s) - optional improvements available"
else
    echo "  ❌ $ISSUES critical issue(s) found"
    echo "  ⚠️  $WARNINGS warning(s)"
    echo ""
    echo "  Run with --fix to attempt automatic repairs:"
    echo "    /speckle.doctor --fix"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"

# Exit code
if [ "$ISSUES" -gt 0 ]; then
    echo ""
    echo "💡 Tip: Re-run install.sh to fix most issues"
fi
```

## Recommendations

```bash
echo ""
echo "💡 Recommendations"
echo ""

# Provide context-specific recommendations
if [ ! -d ".beads" ] || ! command -v bd &>/dev/null; then
    echo "  → Install Beads for issue tracking:"
    echo "    https://github.com/steveyegge/beads"
    echo ""
fi

if ! command -v gh &>/dev/null; then
    echo "  → Install GitHub CLI for better integration:"
    echo "    https://cli.github.com"
    echo ""
fi

if [ ! -d "specs" ]; then
    echo "  → Create your first feature spec:"
    echo "    /speckit.specify \"My feature idea\""
    echo ""
fi

echo "📖 Documentation: https://github.com/JulianDouma/Speckle"
echo ""
```
