#!/usr/bin/env bash
#
# Speckle Installer
# Bridges spec-kit specifications with beads issue tracking
#
# Usage: ./install.sh [OPTIONS] [TARGET_DIR]
#
# Options:
#   --help, -h      Show this help message
#   --uninstall     Remove Speckle from target directory
#   --check         Run health check only (no installation)
#   --force         Skip prerequisite warnings
#   --quiet, -q     Minimal output
#   --version, -v   Show version
#

set -euo pipefail

VERSION="1.3.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors (with fallback for non-color terminals)
if [[ -t 1 ]] && [[ "${TERM:-}" != "dumb" ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    NC='\033[0m' # No Color
else
    RED='' GREEN='' YELLOW='' BLUE='' CYAN='' BOLD='' NC=''
fi

# Globals
QUIET=false
FORCE=false
ACTION="install"
TARGET_DIR="."

#######################################
# Print usage information
#######################################
usage() {
    cat <<EOF
${BOLD}Speckle Installer v${VERSION}${NC}
Bridges spec-kit specifications with beads issue tracking

${BOLD}USAGE:${NC}
    ./install.sh [OPTIONS] [TARGET_DIR]

${BOLD}OPTIONS:${NC}
    -h, --help      Show this help message
    -v, --version   Show version information
    -q, --quiet     Minimal output
    --uninstall     Remove Speckle from target directory
    --check         Run health check only (no installation)
    --force         Skip prerequisite warnings and continue

${BOLD}EXAMPLES:${NC}
    ./install.sh                    # Install to current directory
    ./install.sh ~/my-project       # Install to specific directory
    ./install.sh --uninstall .      # Uninstall from current directory
    ./install.sh --check            # Check prerequisites only

${BOLD}PREREQUISITES:${NC}
    Required:
      - git         Version control
      - bash 4+     Shell (zsh/fish compatible)

    Recommended:
      - bd          Beads issue tracking (https://github.com/steveyegge/beads)
      - gh          GitHub CLI (https://cli.github.com)
      - specify     Spec-kit (https://github.com/github/spec-kit)

${BOLD}DOCUMENTATION:${NC}
    https://github.com/JulianDouma/Speckle

EOF
}

#######################################
# Print message (respects quiet mode)
#######################################
log() {
    if [[ "$QUIET" == false ]]; then
        echo -e "$1"
    fi
}

#######################################
# Print error message to stderr
#######################################
error() {
    echo -e "${RED}Error:${NC} $1" >&2
}

#######################################
# Print warning message
#######################################
warn() {
    echo -e "${YELLOW}Warning:${NC} $1" >&2
}

#######################################
# Print success message
#######################################
success() {
    log "${GREEN}$1${NC}"
}

#######################################
# Detect current shell environment
#######################################
detect_shell() {
    local shell_name
    shell_name="$(basename "${SHELL:-/bin/bash}")"
    
    case "$shell_name" in
        bash)
            echo "bash"
            ;;
        zsh)
            echo "zsh"
            ;;
        fish)
            echo "fish"
            ;;
        *)
            echo "unknown ($shell_name)"
            ;;
    esac
}

#######################################
# Check if a command exists
#######################################
command_exists() {
    command -v "$1" &>/dev/null
}

#######################################
# Get command version (or "not found")
#######################################
get_version() {
    local cmd="$1"
    if command_exists "$cmd"; then
        case "$cmd" in
            git)
                git --version 2>/dev/null | head -1 | sed 's/git version //'
                ;;
            gh)
                gh --version 2>/dev/null | head -1 | sed 's/gh version //' | cut -d' ' -f1
                ;;
            bd)
                bd --version 2>/dev/null | head -1 || echo "installed"
                ;;
            specify)
                echo "installed"
                ;;
            *)
                echo "installed"
                ;;
        esac
    else
        echo "not found"
    fi
}

#######################################
# Check all prerequisites
# Returns: 0 if all required present, 1 otherwise
#######################################
check_prerequisites() {
    local has_errors=false
    local shell_env
    shell_env="$(detect_shell)"
    
    log ""
    log "${BOLD}Checking prerequisites...${NC}"
    log ""
    
    # Shell
    log "  Shell:    ${CYAN}$shell_env${NC}"
    
    # Git (required)
    local git_ver
    git_ver="$(get_version git)"
    if [[ "$git_ver" == "not found" ]]; then
        log "  git:      ${RED}not found${NC}"
        error "git is required but not installed"
        echo "         Install: https://git-scm.com/downloads" >&2
        has_errors=true
    else
        log "  git:      ${GREEN}$git_ver${NC}"
    fi
    
    # GitHub CLI (recommended)
    local gh_ver
    gh_ver="$(get_version gh)"
    if [[ "$gh_ver" == "not found" ]]; then
        log "  gh:       ${YELLOW}not found (recommended)${NC}"
        warn "GitHub CLI enhances the experience"
        echo "         Install: https://cli.github.com" >&2
    else
        log "  gh:       ${GREEN}$gh_ver${NC}"
    fi
    
    # Beads (recommended)
    local bd_ver
    bd_ver="$(get_version bd)"
    if [[ "$bd_ver" == "not found" ]]; then
        log "  bd:       ${YELLOW}not found (recommended)${NC}"
        warn "Beads is needed for issue tracking"
        echo "         Install: https://github.com/steveyegge/beads" >&2
    else
        log "  bd:       ${GREEN}$bd_ver${NC}"
    fi
    
    # Spec-kit (optional)
    local spec_ver
    spec_ver="$(get_version specify)"
    if [[ "$spec_ver" == "not found" ]]; then
        log "  specify:  ${BLUE}not found (optional)${NC}"
    else
        log "  specify:  ${GREEN}$spec_ver${NC}"
    fi
    
    log ""
    
    if [[ "$has_errors" == true ]]; then
        return 1
    fi
    return 0
}

#######################################
# Verify installation is working
#######################################
verify_installation() {
    local target="$1"
    local issues=0
    
    log ""
    log "${BOLD}Verifying installation...${NC}"
    log ""
    
    # Check directories exist
    if [[ -d "$target/.speckle" ]]; then
        log "  ${GREEN}[OK]${NC} .speckle/ directory exists"
    else
        log "  ${RED}[FAIL]${NC} .speckle/ directory missing"
        ((issues++))
    fi
    
    if [[ -d "$target/.speckle/scripts" ]]; then
        log "  ${GREEN}[OK]${NC} .speckle/scripts/ directory exists"
    else
        log "  ${RED}[FAIL]${NC} .speckle/scripts/ missing"
        ((issues++))
    fi
    
    if [[ -d "$target/.claude/commands" ]]; then
        log "  ${GREEN}[OK]${NC} .claude/commands/ directory exists"
    else
        log "  ${RED}[FAIL]${NC} .claude/commands/ missing"
        ((issues++))
    fi
    
    # Check key files
    local commands=(speckle.sync.md speckle.implement.md speckle.status.md)
    for cmd in "${commands[@]}"; do
        if [[ -f "$target/.claude/commands/$cmd" ]]; then
            log "  ${GREEN}[OK]${NC} $cmd installed"
        else
            log "  ${YELLOW}[WARN]${NC} $cmd not found"
        fi
    done
    
    # Check scripts are executable
    if [[ -f "$target/.speckle/scripts/common.sh" ]]; then
        if [[ -x "$target/.speckle/scripts/common.sh" ]]; then
            log "  ${GREEN}[OK]${NC} Scripts are executable"
        else
            log "  ${YELLOW}[WARN]${NC} Scripts not executable"
        fi
    fi
    
    # Check beads initialization
    if [[ -d "$target/.beads" ]]; then
        log "  ${GREEN}[OK]${NC} Beads initialized"
    else
        log "  ${YELLOW}[INFO]${NC} Beads not initialized (run 'bd init')"
    fi
    
    log ""
    
    if [[ $issues -eq 0 ]]; then
        success "Installation verified successfully!"
        return 0
    else
        error "Found $issues issue(s) with installation"
        return 1
    fi
}

#######################################
# Install Speckle to target directory
#######################################
do_install() {
    local target="$1"
    
    log ""
    log "${BOLD}Speckle Installer v${VERSION}${NC}"
    log "================================"
    
    # Check prerequisites first
    if ! check_prerequisites; then
        if [[ "$FORCE" == false ]]; then
            error "Missing required prerequisites. Use --force to continue anyway."
            return 1
        fi
        warn "Continuing despite missing prerequisites (--force)"
    fi
    
    # Validate target directory
    if [[ ! -d "$target" ]]; then
        error "Target directory does not exist: $target"
        echo "" >&2
        echo "To create it, run:" >&2
        echo "  mkdir -p \"$target\" && ./install.sh \"$target\"" >&2
        return 1
    fi
    
    target="$(cd "$target" && pwd)"
    log ""
    log "Target: ${CYAN}$target${NC}"
    
    # Check if it's a git repository
    if [[ ! -d "$target/.git" ]]; then
        warn "Target is not a git repository"
        echo "       Consider: cd \"$target\" && git init" >&2
    fi
    
    log ""
    log "${BOLD}Creating directories...${NC}"
    mkdir -p "$target/.speckle/scripts"
    mkdir -p "$target/.speckle/templates"
    mkdir -p "$target/.speckle/formulas"
    mkdir -p "$target/.claude/commands"
    mkdir -p "$target/.beads/formulas"
    log "  ${GREEN}[OK]${NC} Directories created"
    
    # Copy commands
    log ""
    log "${BOLD}Installing commands...${NC}"
    local cmd_count=0
    for cmd in speckle.sync.md speckle.implement.md speckle.status.md speckle.progress.md speckle.bugfix.md speckle.hotfix.md speckle.doctor.md speckle.board.md speckle.issue.md speckle.triage.md; do
        if [[ -f "$SCRIPT_DIR/.claude/commands/$cmd" ]]; then
            cp "$SCRIPT_DIR/.claude/commands/$cmd" "$target/.claude/commands/"
            log "  ${GREEN}[OK]${NC} $cmd"
            ((cmd_count++))
        fi
    done
    
    if [[ $cmd_count -eq 0 ]]; then
        warn "No commands found to install"
        echo "       Make sure you're running from the Speckle source directory" >&2
    fi
    
    # Copy scripts
    log ""
    log "${BOLD}Installing scripts...${NC}"
    for script in common.sh comments.sh labels.sh epics.sh board.py; do
        if [[ -f "$SCRIPT_DIR/.speckle/scripts/$script" ]]; then
            cp "$SCRIPT_DIR/.speckle/scripts/$script" "$target/.speckle/scripts/"
            chmod +x "$target/.speckle/scripts/$script"
            log "  ${GREEN}[OK]${NC} $script"
        fi
    done
    
    # Copy templates (don't overwrite existing)
    log ""
    log "${BOLD}Installing templates...${NC}"
    for template in personas.md constitution.md; do
        if [[ -f "$SCRIPT_DIR/.speckle/templates/$template" ]]; then
            if [[ ! -f "$target/.speckle/templates/$template" ]]; then
                cp "$SCRIPT_DIR/.speckle/templates/$template" "$target/.speckle/templates/"
                log "  ${GREEN}[OK]${NC} $template"
            else
                log "  ${BLUE}[SKIP]${NC} $template (already exists)"
            fi
        fi
    done
    
    # Copy GitHub issue templates
    log ""
    log "${BOLD}Installing GitHub issue templates...${NC}"
    if [[ -d "$SCRIPT_DIR/.github/ISSUE_TEMPLATE" ]]; then
        mkdir -p "$target/.github/ISSUE_TEMPLATE"
        local template_count=0
        for template in "$SCRIPT_DIR"/.github/ISSUE_TEMPLATE/*.md "$SCRIPT_DIR"/.github/ISSUE_TEMPLATE/*.yml; do
            if [[ -f "$template" ]]; then
                local template_name
                template_name="$(basename "$template")"
                if [[ ! -f "$target/.github/ISSUE_TEMPLATE/$template_name" ]]; then
                    cp "$template" "$target/.github/ISSUE_TEMPLATE/"
                    log "  ${GREEN}[OK]${NC} $template_name"
                    ((template_count++))
                else
                    log "  ${BLUE}[SKIP]${NC} $template_name (already exists)"
                fi
            fi
        done
        if [[ $template_count -eq 0 ]]; then
            log "  ${BLUE}[INFO]${NC} All templates already exist"
        fi
    else
        log "  ${BLUE}[INFO]${NC} No GitHub issue templates found"
    fi
    
    # Copy formulas
    log ""
    log "${BOLD}Installing formulas...${NC}"
    local formula_count=0
    if compgen -G "$SCRIPT_DIR/.speckle/formulas/*.toml" > /dev/null 2>&1; then
        for formula in "$SCRIPT_DIR"/.speckle/formulas/*.toml; do
            if [[ -f "$formula" ]]; then
                local formula_name
                formula_name="$(basename "$formula")"
                cp "$formula" "$target/.beads/formulas/"
                log "  ${GREEN}[OK]${NC} $formula_name"
                ((formula_count++))
            fi
        done
    fi
    if [[ $formula_count -eq 0 ]]; then
        log "  ${BLUE}[INFO]${NC} No formulas found"
    fi
    
    # Initialize beads if not already
    if [[ ! -f "$target/.beads/config.toml" ]] && command_exists bd; then
        log ""
        log "${BOLD}Initializing beads...${NC}"
        if (cd "$target" && bd init 2>/dev/null); then
            log "  ${GREEN}[OK]${NC} Beads initialized"
        else
            log "  ${YELLOW}[SKIP]${NC} Beads init failed (may already exist)"
        fi
    fi
    
    # Verify installation
    verify_installation "$target"
    
    # Print success message
    log ""
    log "════════════════════════════════════════════════════════"
    success "  Speckle v${VERSION} installed successfully!"
    log "════════════════════════════════════════════════════════"
    log ""
    log "${BOLD}Available commands:${NC}"
    log "   /speckle.sync      - Sync tasks.md <-> beads"
    log "   /speckle.implement - Implement next ready task"
    log "   /speckle.status    - Show epic progress"
    log "   /speckle.progress  - Add progress note"
    log "   /speckle.bugfix    - Start bugfix workflow"
    log "   /speckle.hotfix    - Start urgent fix workflow"
    log "   /speckle.issue     - Guided issue creation"
    log "   /speckle.triage    - Review and prioritize issues"
    log "   /speckle.doctor    - Diagnose installation issues"
    log "   /speckle.board     - Web-based kanban board"
    log ""
    log "${BOLD}Quick start:${NC}"
    log "   1. Create spec:  ${CYAN}/speckit.specify \"Your feature\"${NC}"
    log "   2. Create plan:  ${CYAN}/speckit.plan${NC}"
    log "   3. Create tasks: ${CYAN}/speckit.tasks${NC}"
    log "   4. Sync:         ${CYAN}/speckle.sync${NC}"
    log "   5. Implement:    ${CYAN}/speckle.implement${NC}"
    log ""
    log "Documentation: ${BLUE}https://github.com/JulianDouma/Speckle${NC}"
    log ""
}

#######################################
# Uninstall Speckle from target directory
#######################################
do_uninstall() {
    local target="$1"
    
    log ""
    log "${BOLD}Speckle Uninstaller v${VERSION}${NC}"
    log "================================"
    log ""
    
    if [[ ! -d "$target" ]]; then
        error "Target directory does not exist: $target"
        return 1
    fi
    
    target="$(cd "$target" && pwd)"
    log "Target: ${CYAN}$target${NC}"
    log ""
    
    # Check if Speckle is installed
    if [[ ! -d "$target/.speckle" ]]; then
        warn "Speckle does not appear to be installed in $target"
        return 0
    fi
    
    log "${BOLD}Removing Speckle files...${NC}"
    
    # Remove commands
    for cmd in speckle.sync.md speckle.implement.md speckle.status.md speckle.progress.md speckle.bugfix.md speckle.hotfix.md speckle.doctor.md speckle.board.md speckle.issue.md speckle.triage.md; do
        if [[ -f "$target/.claude/commands/$cmd" ]]; then
            rm "$target/.claude/commands/$cmd"
            log "  ${GREEN}[OK]${NC} Removed $cmd"
        fi
    done
    
    # Remove .speckle directory
    if [[ -d "$target/.speckle" ]]; then
        rm -rf "$target/.speckle"
        log "  ${GREEN}[OK]${NC} Removed .speckle/"
    fi
    
    # Remove formulas (but keep .beads if it has other content)
    for formula in speckle-feature.toml speckle-bugfix.toml; do
        if [[ -f "$target/.beads/formulas/$formula" ]]; then
            rm "$target/.beads/formulas/$formula"
            log "  ${GREEN}[OK]${NC} Removed $formula"
        fi
    done
    
    log ""
    success "Speckle has been uninstalled from $target"
    log ""
    log "${BOLD}Note:${NC} The following were preserved:"
    log "   - .beads/ directory (your issue data)"
    log "   - .claude/commands/ (may contain other commands)"
    log "   - specs/ directory (your specifications)"
    log ""
}

#######################################
# Run health check only
#######################################
do_check() {
    local target="$1"
    
    log ""
    log "${BOLD}Speckle Health Check v${VERSION}${NC}"
    log "================================"
    
    check_prerequisites
    
    if [[ -d "$target/.speckle" ]]; then
        verify_installation "$target"
    else
        log ""
        log "${YELLOW}Speckle is not installed in $target${NC}"
        log "Run: ./install.sh \"$target\""
    fi
}

#######################################
# Parse command line arguments
#######################################
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--version)
                echo "Speckle v${VERSION}"
                exit 0
                ;;
            -q|--quiet)
                QUIET=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --uninstall)
                ACTION="uninstall"
                shift
                ;;
            --check)
                ACTION="check"
                shift
                ;;
            -*)
                error "Unknown option: $1"
                echo "Run './install.sh --help' for usage" >&2
                exit 1
                ;;
            *)
                TARGET_DIR="$1"
                shift
                ;;
        esac
    done
}

#######################################
# Main entry point
#######################################
main() {
    parse_args "$@"
    
    case "$ACTION" in
        install)
            do_install "$TARGET_DIR"
            ;;
        uninstall)
            do_uninstall "$TARGET_DIR"
            ;;
        check)
            do_check "$TARGET_DIR"
            ;;
    esac
}

main "$@"
