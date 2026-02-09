#!/usr/bin/env bash
#
# Speckle Remote Installer
# 
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/JulianDouma/Speckle/main/install-remote.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/JulianDouma/Speckle/main/install-remote.sh | bash -s -- /path/to/project
#   curl -fsSL https://raw.githubusercontent.com/JulianDouma/Speckle/main/install-remote.sh | bash -s -- --help
#

set -euo pipefail

REPO="JulianDouma/Speckle"
BRANCH="main"
TMP_DIR=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "$1"; }
error() { echo -e "${RED}Error: $1${NC}" >&2; exit 1; }

cleanup() {
    if [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]]; then
        rm -rf "$TMP_DIR"
    fi
}

trap cleanup EXIT

show_help() {
    cat << 'EOF'
Speckle Remote Installer

Usage:
  curl -fsSL https://raw.githubusercontent.com/JulianDouma/Speckle/main/install-remote.sh | bash
  curl -fsSL https://raw.githubusercontent.com/JulianDouma/Speckle/main/install-remote.sh | bash -s -- [OPTIONS] [TARGET]

Options:
  --help, -h      Show this help
  --check         Run health check only
  --uninstall     Remove Speckle from target
  --version, -v   Show version

Examples:
  # Install to current directory
  curl -fsSL .../install-remote.sh | bash

  # Install to specific project
  curl -fsSL .../install-remote.sh | bash -s -- /path/to/project

  # Check existing installation
  curl -fsSL .../install-remote.sh | bash -s -- --check /path/to/project

EOF
    exit 0
}

main() {
    # Parse args for --help before downloading
    for arg in "$@"; do
        case "$arg" in
            --help|-h) show_help ;;
        esac
    done

    log ""
    log "${BLUE}╔════════════════════════════════════════╗${NC}"
    log "${BLUE}║${NC}     ${GREEN}Speckle Remote Installer${NC}          ${BLUE}║${NC}"
    log "${BLUE}╚════════════════════════════════════════╝${NC}"
    log ""

    # Check for required tools
    if ! command -v git &>/dev/null; then
        error "git is required. Install from https://git-scm.com"
    fi

    # Create temp directory
    TMP_DIR=$(mktemp -d)
    log "${BLUE}→${NC} Downloading Speckle..."

    # Clone repository (shallow for speed)
    if ! git clone --depth 1 --branch "$BRANCH" "https://github.com/$REPO.git" "$TMP_DIR/speckle" 2>/dev/null; then
        error "Failed to download Speckle from GitHub"
    fi

    log "${GREEN}✓${NC} Downloaded"
    log ""

    # Run the actual installer
    chmod +x "$TMP_DIR/speckle/install.sh"
    "$TMP_DIR/speckle/install.sh" "$@"

    # Cleanup happens via trap
}

main "$@"
