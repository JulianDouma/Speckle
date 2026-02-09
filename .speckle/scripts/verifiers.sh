#!/usr/bin/env bash
# Speckle DoD (Definition of Done) Verifier System
# Source this in commands: source ".speckle/scripts/verifiers.sh"

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Default paths
VERIFIERS_DIR="${SPECKLE_VERIFIERS_DIR:-.speckle/verifiers}"
DEFAULT_VERIFIER_FILE="$VERIFIERS_DIR/default.toml"
DEFAULT_TIMEOUT=300

# Parse TOML verifier file and return verifiers as JSON
# Uses basic bash parsing (no external dependencies)
parse_verifier_file() {
    local file="$1"
    
    if [ ! -f "$file" ]; then
        log_warn "Verifier file not found: $file"
        echo "[]"
        return
    fi
    
    # Simple TOML parser for verifiers
    local in_verifier=false
    local name="" command="" expect="0" timeout="$DEFAULT_TIMEOUT" optional="false"
    local verifiers="["
    local first=true
    
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        
        # Start of new verifier
        if [[ "$line" =~ ^\[\[verifiers\]\] ]]; then
            # Save previous verifier if exists
            if [ "$in_verifier" = true ] && [ -n "$name" ]; then
                [ "$first" = false ] && verifiers+=","
                verifiers+="{\"name\":\"$name\",\"command\":\"$command\",\"expect\":$expect,\"timeout\":$timeout,\"optional\":$optional}"
                first=false
            fi
            # Reset for new verifier
            in_verifier=true
            name="" command="" expect="0" timeout="$DEFAULT_TIMEOUT" optional="false"
            continue
        fi
        
        # Parse key-value pairs
        if [ "$in_verifier" = true ]; then
            if [[ "$line" =~ ^name[[:space:]]*=[[:space:]]*\"(.*)\" ]]; then
                name="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^expect[[:space:]]*=[[:space:]]*([0-9]+) ]]; then
                expect="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^timeout[[:space:]]*=[[:space:]]*([0-9]+) ]]; then
                timeout="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^optional[[:space:]]*=[[:space:]]*(true|false) ]]; then
                optional="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^command[[:space:]]*=[[:space:]]*\"\"\" ]]; then
                # Multi-line command starts
                command=""
                while IFS= read -r cmdline; do
                    if [[ "$cmdline" =~ \"\"\"$ ]]; then
                        # End of multi-line
                        cmdline="${cmdline%\"\"\"}"
                        command+="$cmdline"
                        break
                    fi
                    command+="$cmdline\n"
                done
            elif [[ "$line" =~ ^command[[:space:]]*=[[:space:]]*\"(.*)\" ]]; then
                command="${BASH_REMATCH[1]}"
            fi
        fi
    done < "$file"
    
    # Save last verifier
    if [ "$in_verifier" = true ] && [ -n "$name" ]; then
        [ "$first" = false ] && verifiers+=","
        verifiers+="{\"name\":\"$name\",\"command\":\"$command\",\"expect\":$expect,\"timeout\":$timeout,\"optional\":$optional}"
    fi
    
    verifiers+="]"
    echo "$verifiers"
}

# Run a single verifier
# Returns: 0 on success, 1 on failure
run_verifier() {
    local name="$1"
    local command="$2"
    local expect="${3:-0}"
    local timeout="${4:-$DEFAULT_TIMEOUT}"
    local optional="${5:-false}"
    
    log_info "Running: $name"
    
    # Create temp script
    local tmp_script
    tmp_script=$(mktemp)
    echo -e "$command" > "$tmp_script"
    chmod +x "$tmp_script"
    
    # Run with timeout
    local exit_code=0
    local output
    if command -v timeout &>/dev/null; then
        output=$(timeout "$timeout" bash "$tmp_script" 2>&1) || exit_code=$?
    else
        # macOS doesn't have timeout, use perl
        output=$(perl -e "alarm $timeout; exec @ARGV" bash "$tmp_script" 2>&1) || exit_code=$?
    fi
    
    rm -f "$tmp_script"
    
    # Check result
    if [ "$exit_code" -eq "$expect" ]; then
        log_success "$name: PASSED"
        return 0
    elif [ "$exit_code" -eq 124 ]; then
        log_error "$name: TIMEOUT (${timeout}s)"
        [ "$optional" = "true" ] && return 0
        return 1
    else
        if [ "$optional" = "true" ]; then
            log_warn "$name: FAILED (optional, continuing)"
            echo "$output" | head -10
            return 0
        else
            log_error "$name: FAILED (exit code: $exit_code, expected: $expect)"
            echo "$output" | head -20
            return 1
        fi
    fi
}

# Run all verifiers from a file
# Returns: 0 if all required verifiers pass, 1 otherwise
run_all_verifiers() {
    local verifier_file="${1:-$DEFAULT_VERIFIER_FILE}"
    local failed=0
    local passed=0
    local skipped=0
    
    if [ ! -f "$verifier_file" ]; then
        log_warn "No verifier file found at $verifier_file"
        log_info "Running standard verifiers only..."
        run_standard_verifiers
        return $?
    fi
    
    log_info "Running DoD verifiers from: $verifier_file"
    echo ""
    
    # Parse verifiers (simple approach - read file directly)
    local in_verifier=false
    local name="" command="" expect="0" timeout="$DEFAULT_TIMEOUT" optional="false"
    local multiline_cmd=false
    
    while IFS= read -r line || [ -n "$line" ]; do
        # Handle multi-line command continuation
        if [ "$multiline_cmd" = true ]; then
            if [[ "$line" =~ \"\"\"$ ]]; then
                command+="${line%\"\"\"}"
                multiline_cmd=false
            else
                command+="$line"$'\n'
            fi
            continue
        fi
        
        # Skip comments and empty lines outside verifier blocks
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Start of new verifier
        if [[ "$line" =~ ^\[\[verifiers\]\] ]]; then
            # Run previous verifier if exists
            if [ "$in_verifier" = true ] && [ -n "$name" ] && [ -n "$command" ]; then
                if run_verifier "$name" "$command" "$expect" "$timeout" "$optional"; then
                    ((passed++))
                else
                    ((failed++))
                fi
            fi
            # Reset for new verifier
            in_verifier=true
            name="" command="" expect="0" timeout="$DEFAULT_TIMEOUT" optional="false"
            continue
        fi
        
        # Parse key-value pairs
        if [ "$in_verifier" = true ]; then
            if [[ "$line" =~ ^name[[:space:]]*=[[:space:]]*\"(.*)\" ]]; then
                name="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^expect[[:space:]]*=[[:space:]]*([0-9]+) ]]; then
                expect="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^timeout[[:space:]]*=[[:space:]]*([0-9]+) ]]; then
                timeout="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^optional[[:space:]]*=[[:space:]]*(true|false) ]]; then
                optional="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^command[[:space:]]*=[[:space:]]*\"\"\" ]]; then
                # Multi-line command starts
                command=""
                multiline_cmd=true
            elif [[ "$line" =~ ^command[[:space:]]*=[[:space:]]*\"(.*)\" ]]; then
                command="${BASH_REMATCH[1]}"
            fi
        fi
    done < "$verifier_file"
    
    # Run last verifier
    if [ "$in_verifier" = true ] && [ -n "$name" ] && [ -n "$command" ]; then
        if run_verifier "$name" "$command" "$expect" "$timeout" "$optional"; then
            ((passed++))
        else
            ((failed++))
        fi
    fi
    
    # Summary
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "DoD Verification Summary"
    echo "════════════════════════════════════════════════════════════"
    echo "  Passed:  $passed"
    echo "  Failed:  $failed"
    echo "  Skipped: $skipped"
    echo "════════════════════════════════════════════════════════════"
    
    if [ "$failed" -gt 0 ]; then
        log_error "DoD verification FAILED"
        return 1
    else
        log_success "DoD verification PASSED"
        return 0
    fi
}

# Quick check - run only essential verifiers
run_quick_verifiers() {
    local failed=0
    
    log_info "Running quick DoD checks..."
    
    # 1. No uncommitted changes
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        log_warn "Uncommitted changes detected"
        git status --short
        ((failed++))
    else
        log_success "Working tree clean"
    fi
    
    # 2. Last commit exists
    if ! git log -1 --oneline &>/dev/null; then
        log_error "No commits found"
        ((failed++))
    else
        log_success "Commit exists: $(git log -1 --oneline)"
    fi
    
    return $failed
}

# Create custom verifier file for a project
init_verifiers() {
    local target="${1:-.speckle/verifiers}"
    
    mkdir -p "$target"
    
    if [ -f "$target/default.toml" ]; then
        log_info "Verifier config already exists at $target/default.toml"
        return 0
    fi
    
    # Copy from Speckle source or create minimal
    if [ -f "$SCRIPT_DIR/../verifiers/default.toml" ]; then
        cp "$SCRIPT_DIR/../verifiers/default.toml" "$target/"
        log_success "Created verifier config from template"
    else
        cat > "$target/default.toml" <<'EOF'
# Project DoD Verifiers
# Customize these for your project

[meta]
version = 1
description = "Project verifiers"

[[verifiers]]
name = "No uncommitted changes"
command = "test -z \"$(git status --porcelain)\""
expect = 0
timeout = 10

[[verifiers]]
name = "Tests pass"
command = "make test || npm test || echo 'No tests configured'"
expect = 0
timeout = 300
EOF
        log_success "Created minimal verifier config"
    fi
    
    log_info "Edit $target/default.toml to customize verifiers"
}

# Export functions
export -f parse_verifier_file
export -f run_verifier
export -f run_all_verifiers
export -f run_quick_verifiers
export -f init_verifiers
export VERIFIERS_DIR DEFAULT_VERIFIER_FILE DEFAULT_TIMEOUT
