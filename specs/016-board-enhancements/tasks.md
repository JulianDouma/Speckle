# Tasks: Board Enhancements

## Phase 1: System Color Mode

### T001: Add dark theme CSS custom properties
- [ ] Add complete `:root` CSS variables for light theme
- [ ] Add `[data-theme="dark"]` selector with dark values
- [ ] Include all colors: bg, card-bg, text, muted, border
- [ ] Include column colors: backlog, progress, blocked, done
- [ ] Include shadows with appropriate opacity
- [ ] Include header gradient variant

**Labels:** phase:color-mode, priority:high

### T002: Add prefers-color-scheme media query
- [ ] Add `@media (prefers-color-scheme: dark)` query
- [ ] Target `:root:not([data-theme])` for auto-only
- [ ] Duplicate dark theme variables in media query
- [ ] Test with system dark mode enabled

**Labels:** phase:color-mode, priority:high

### T003: Implement ThemeController JavaScript
- [ ] Create ThemeController object with STORAGE_KEY
- [ ] Implement `init()` to check localStorage on load
- [ ] Implement `apply(theme)` to set data-theme attribute
- [ ] Implement `toggle()` to switch between light/dark
- [ ] Implement `getCurrent()` with system fallback
- [ ] Implement `updateToggleUI()` to sync button state
- [ ] Add DOMContentLoaded listener for init
- [ ] Add matchMedia listener for system changes

**Labels:** phase:color-mode, priority:high

### T004: Add theme toggle button to header
- [ ] Add button element with `theme-toggle` class
- [ ] Use emoji icons (sun/moon) for states
- [ ] Add onclick handler for ThemeController.toggle()
- [ ] Add title attribute for accessibility
- [ ] Style with semi-transparent background
- [ ] Add hover effect

**Labels:** phase:color-mode, priority:high

### T005: Add localStorage persistence
- [ ] Store preference in 'speckle-theme' key
- [ ] Read on page load before rendering
- [ ] Update on toggle
- [ ] Handle localStorage unavailable (private browsing)

**Labels:** phase:color-mode, priority:medium

### T006: Add transition animations
- [ ] Add CSS transition for background-color
- [ ] Add transition for color
- [ ] Add transition for border-color
- [ ] Use 200ms duration for smooth feel
- [ ] Exclude transitions on page load (flash prevention)

**Labels:** phase:color-mode, priority:low

### T007: Verify WCAG contrast compliance
- [ ] Test body text contrast (target > 7:1)
- [ ] Test muted text contrast (target > 4.5:1)
- [ ] Test priority badges contrast
- [ ] Test column header contrast
- [ ] Adjust colors if any fail
- [ ] Document final contrast ratios

**Labels:** phase:color-mode, priority:high

---

## Phase 2: GitHub Authentication

### T008: Create github.py module skeleton
- [ ] Create `.speckle/scripts/github.py`
- [ ] Add imports: os, subprocess, json, dataclasses
- [ ] Add GitHubAuth dataclass for credentials
- [ ] Add GitHubClient class skeleton
- [ ] Add main() for CLI testing

**Labels:** phase:github-auth, priority:high

### T009: Implement env var auth (GITHUB_TOKEN)
- [ ] Check for GITHUB_TOKEN environment variable
- [ ] Check for GH_TOKEN as fallback
- [ ] Return token if found
- [ ] Log source (masked) for debugging

**Labels:** phase:github-auth, priority:high

### T010: Implement gh CLI auth extraction
- [ ] Run `gh auth token` subprocess
- [ ] Capture stdout with 5s timeout
- [ ] Handle FileNotFoundError (gh not installed)
- [ ] Handle TimeoutExpired
- [ ] Return token if successful

**Labels:** phase:github-auth, priority:high

### T011: Implement config file auth
- [ ] Check ~/.speckle/config.toml
- [ ] Parse TOML (use tomllib in 3.11+ or fallback)
- [ ] Extract github.token if present
- [ ] Handle missing file/section gracefully

**Labels:** phase:github-auth, priority:medium

### T012: Add get_github_client() with fallback
- [ ] Try each auth method in priority order
- [ ] Return authenticated client on success
- [ ] Return None if all methods fail
- [ ] Add status() method to check auth state

**Labels:** phase:github-auth, priority:high

### T013: Add speckle.github.auth.md command
- [ ] Create `.claude/commands/speckle.github.auth.md`
- [ ] Show current auth status
- [ ] Show which method is active
- [ ] Provide setup instructions if not authenticated

**Labels:** phase:github-auth, priority:high

---

## Phase 3: GitHub Sync

### T014: Create github-links.jsonl storage
- [ ] Define IssueLinkage dataclass
- [ ] Implement load_links() from JSONL
- [ ] Implement save_link() to append JSONL
- [ ] Implement update_link() for sync updates
- [ ] Handle missing file gracefully

**Labels:** phase:github-sync, priority:high

### T015: Implement push_to_github()
- [ ] Accept beads issue dict as input
- [ ] Check if already linked
- [ ] Map beads fields to GitHub fields
- [ ] Use gh CLI: `gh issue create` or `gh issue edit`
- [ ] Extract issue number from output
- [ ] Save linkage on success

**Labels:** phase:github-sync, priority:high

### T016: Implement pull_from_github()
- [ ] Accept GitHub issue number as input
- [ ] Fetch issue via `gh issue view --json`
- [ ] Check if already linked to bead
- [ ] Map GitHub fields to beads fields
- [ ] Create/update bead via `bd create`/`bd update`
- [ ] Save linkage on success

**Labels:** phase:github-sync, priority:high

### T017: Add label/priority mapping
- [ ] Define default label mappings
- [ ] Map beads priority 0-4 to GitHub labels
- [ ] Map beads type to GitHub labels
- [ ] Extract priority from GitHub labels on pull
- [ ] Make mappings configurable

**Labels:** phase:github-sync, priority:medium

### T018: Add speckle.github.sync.md command
- [ ] Create `.claude/commands/speckle.github.sync.md`
- [ ] Document bidirectional sync
- [ ] Show sync status before/after
- [ ] Handle errors with clear messages

**Labels:** phase:github-sync, priority:high

### T019: Add push/pull commands
- [ ] Create `speckle.github.push.md` for one-way push
- [ ] Create `speckle.github.pull.md` for one-way pull
- [ ] Accept optional issue ID filter
- [ ] Show progress during operation

**Labels:** phase:github-sync, priority:medium

---

## Phase 4: Board Integration

### T020: Add GitHub icon SVG to card template
- [ ] Add SVG path for GitHub logo (16x16)
- [ ] Create CSS class for icon styling
- [ ] Position in card header
- [ ] Use currentColor for theme compatibility

**Labels:** phase:board-integration, priority:medium

### T021: Link icon to GitHub URL
- [ ] Wrap icon in anchor tag
- [ ] Set href to issue.github_url
- [ ] Add target="_blank" for new tab
- [ ] Add title with issue number
- [ ] Only render if github_url exists

**Labels:** phase:board-integration, priority:medium

### T022: Add sync status to board footer
- [ ] Count linked vs unlinked issues
- [ ] Show "X/Y synced to GitHub"
- [ ] Show last sync timestamp
- [ ] Style for both themes

**Labels:** phase:board-integration, priority:low

### T023: Add --github flag to board.py
- [ ] Add argparse argument for --github
- [ ] Load linkage data when flag is set
- [ ] Merge github_url into issue dicts
- [ ] Add note in startup banner

**Labels:** phase:board-integration, priority:medium

### T024: Style GitHub elements for both themes
- [ ] Ensure icon visible in light mode
- [ ] Ensure icon visible in dark mode
- [ ] Add hover effect
- [ ] Test contrast compliance

**Labels:** phase:board-integration, priority:medium

---

## Phase 5: Polish & Documentation

### T025: Add rate limit handling with backoff
- [ ] Check X-RateLimit-Remaining header
- [ ] Implement exponential backoff
- [ ] Show warning when approaching limit
- [ ] Abort gracefully when exceeded

**Labels:** phase:polish, priority:high

### T026: Add offline graceful degradation
- [ ] Detect network failures
- [ ] Show clear error message
- [ ] Continue with local-only mode
- [ ] Cache last known sync state

**Labels:** phase:polish, priority:medium

### T027: Update README with GitHub setup
- [ ] Add "GitHub Integration" section
- [ ] Document authentication methods
- [ ] Show sync command examples
- [ ] Add troubleshooting tips

**Labels:** phase:docs, priority:high

### T028: Update CHANGELOG for v1.3.0
- [ ] Add v1.3.0 section with date
- [ ] Document color mode feature
- [ ] Document GitHub integration
- [ ] List all new commands
- [ ] Reference GitHub issue #16

**Labels:** phase:docs, priority:high
