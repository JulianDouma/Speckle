#!/usr/bin/env bash
# Speckle common utilities
# Source this in other scripts: source "$(dirname "$0")/common.sh"

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log_info() { echo -e "${BLUE}ℹ${NC} $*"; }
log_success() { echo -e "${GREEN}✅${NC} $*"; }
log_warn() { echo -e "${YELLOW}⚠️${NC} $*"; }
log_error() { echo -e "${RED}❌${NC} $*" >&2; }

# Get repository root
get_repo_root() {
    git rev-parse --show-toplevel 2>/dev/null || pwd
}

# Get current feature branch
get_feature_branch() {
    local branch
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
    
    if [[ "$branch" =~ ^[0-9]{3}- ]]; then
        echo "$branch"
    else
        echo ""
    fi
}

# Find feature directory from branch
get_feature_dir() {
    local branch="${1:-$(get_feature_branch)}"
    local repo_root
    repo_root=$(get_repo_root)
    
    if [ -z "$branch" ]; then
        return 1
    fi
    
    local prefix="${branch:0:3}"
    local feature_dir
    feature_dir=$(find "$repo_root/specs" -maxdepth 1 -type d -name "${prefix}-*" 2>/dev/null | head -1)
    
    if [ -d "$feature_dir" ]; then
        echo "$feature_dir"
    else
        return 1
    fi
}

# Check if beads is available
check_beads() {
    if ! command -v bd &>/dev/null; then
        log_error "Beads not installed"
        echo "Install from: https://github.com/steveyegge/beads"
        return 1
    fi
    return 0
}

# Check if spec-kit is available
check_speckit() {
    if ! command -v specify &>/dev/null; then
        log_error "Spec-kit not installed"
        echo "Install from: https://github.com/github/spec-kit"
        return 1
    fi
    return 0
}

# Slugify a string (for labels, filenames)
slugify() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-\|-$//g'
}

# Truncate string with ellipsis
truncate() {
    local str="$1"
    local max="${2:-80}"
    if [ "${#str}" -gt "$max" ]; then
        echo "${str:0:$((max-3))}..."
    else
        echo "$str"
    fi
}

# Export functions
export -f log_info log_success log_warn log_error
export -f get_repo_root get_feature_branch get_feature_dir
export -f check_beads check_speckit
export -f slugify truncate
