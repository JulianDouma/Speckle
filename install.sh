#!/usr/bin/env bash
#
# Speckle Installer
# Bridges spec-kit specifications with beads issue tracking
#

set -euo pipefail

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "🔮 Speckle Installer v${VERSION}"
echo "================================"
echo ""

# Check for target directory
TARGET_DIR="${1:-.}"
if [ ! -d "$TARGET_DIR" ]; then
    echo "❌ Target directory does not exist: $TARGET_DIR"
    exit 1
fi

TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
echo "📁 Target: $TARGET_DIR"
echo ""

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Beads
if command -v bd &>/dev/null; then
    echo "✅ Beads: $(bd --version 2>&1 | head -1)"
else
    echo "⚠️  Beads not found - install from https://github.com/steveyegge/beads"
fi

# Spec-kit
if command -v specify &>/dev/null; then
    echo "✅ Spec-kit: installed"
else
    echo "⚠️  Spec-kit not found - install from https://github.com/github/spec-kit"
fi

# Claude Code (optional)
if [ -d "$TARGET_DIR/.claude" ]; then
    echo "✅ Claude Code: .claude/ exists"
else
    echo "ℹ️  Creating .claude/commands/"
    mkdir -p "$TARGET_DIR/.claude/commands"
fi

echo ""

# Create directories
echo "📂 Creating Speckle directories..."
mkdir -p "$TARGET_DIR/.speckle/scripts"
mkdir -p "$TARGET_DIR/.speckle/templates"
mkdir -p "$TARGET_DIR/.speckle/formulas"
mkdir -p "$TARGET_DIR/.claude/commands"

# Copy commands
echo "📋 Installing commands..."
for cmd in speckle.sync.md speckle.implement.md speckle.status.md speckle.progress.md; do
    if [ -f "$SCRIPT_DIR/.claude/commands/$cmd" ]; then
        cp "$SCRIPT_DIR/.claude/commands/$cmd" "$TARGET_DIR/.claude/commands/"
        echo "   ✅ $cmd"
    fi
done

# Copy scripts
echo "🔧 Installing scripts..."
for script in common.sh prerequisites.sh comments.sh; do
    if [ -f "$SCRIPT_DIR/.speckle/scripts/$script" ]; then
        cp "$SCRIPT_DIR/.speckle/scripts/$script" "$TARGET_DIR/.speckle/scripts/"
        chmod +x "$TARGET_DIR/.speckle/scripts/$script"
        echo "   ✅ $script"
    fi
done

# Copy templates
echo "📝 Installing templates..."
for template in personas.md constitution.md; do
    if [ -f "$SCRIPT_DIR/.speckle/templates/$template" ]; then
        # Don't overwrite existing
        if [ ! -f "$TARGET_DIR/.speckle/templates/$template" ]; then
            cp "$SCRIPT_DIR/.speckle/templates/$template" "$TARGET_DIR/.speckle/templates/"
            echo "   ✅ $template"
        else
            echo "   ⏭️  $template (exists)"
        fi
    fi
done

# Copy formulas
echo "📜 Installing formulas..."
mkdir -p "$TARGET_DIR/.beads/formulas"
for formula in "$SCRIPT_DIR"/.speckle/formulas/*.toml; do
    if [ -f "$formula" ]; then
        formula_name="$(basename "$formula")"
        cp "$formula" "$TARGET_DIR/.beads/formulas/"
        echo "   ✅ $formula_name"
    fi
done

# Initialize beads if not already
if [ ! -d "$TARGET_DIR/.beads" ]; then
    echo ""
    echo "🔗 Initializing beads..."
    (cd "$TARGET_DIR" && bd init)
fi

echo ""
echo "════════════════════════════════════════════"
echo "✅ Speckle installation complete!"
echo "════════════════════════════════════════════"
echo ""
echo "Available commands:"
echo "   /speckle.sync      - Sync tasks.md ↔ beads"
echo "   /speckle.implement - Implement next ready task"
echo "   /speckle.status    - Show epic progress"
echo "   /speckle.progress  - Add progress note"
echo ""
echo "Quick start:"
echo "   1. Create spec:  /speckit.specify \"Your feature\""
echo "   2. Create plan:  /speckit.plan"
echo "   3. Create tasks: /speckit.tasks"
echo "   4. Sync:         /speckle.sync"
echo "   5. Implement:    /speckle.implement"
echo ""
echo "📖 Documentation: https://github.com/JulianDouma/Speckle"
echo ""
