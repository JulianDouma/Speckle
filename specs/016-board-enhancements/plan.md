# Implementation Plan: Board Enhancements

## Overview

Implement system color mode and GitHub integration for the Speckle Kanban Board.

**Technology Stack:**
- Python 3.8+ (stdlib + gh CLI for GitHub)
- CSS custom properties with `prefers-color-scheme`
- JavaScript for theme toggle and persistence
- JSONL for linkage storage (consistent with beads)

## Phases

### Phase 1: System Color Mode
Complete dark/light theme support with automatic detection and user override.

**Deliverables:**
- CSS custom properties for both themes
- `prefers-color-scheme` media query support
- JavaScript ThemeController
- Toggle button in header
- localStorage persistence
- Smooth transition animations

**Dependencies:** None (modifies existing board.py)

### Phase 2: GitHub Authentication
Layered authentication system for GitHub API access.

**Deliverables:**
- `github.py` module with auth logic
- Environment variable support
- gh CLI token extraction
- Config file support (~/.speckle/config.toml)
- Auth status command

**Dependencies:** None

### Phase 3: GitHub Sync
Bidirectional sync between beads and GitHub Issues.

**Deliverables:**
- Issue linkage tracking (github-links.jsonl)
- Push beads → GitHub
- Pull GitHub → beads
- Conflict detection
- CLI commands (sync, push, pull)

**Dependencies:** Phase 2

### Phase 4: Board Integration
Show GitHub status on board cards.

**Deliverables:**
- GitHub icon on linked cards
- Click to open in browser
- Sync status in footer
- `--github` flag for board

**Dependencies:** Phase 3

### Phase 5: Polish & Documentation
Error handling, edge cases, and docs.

**Deliverables:**
- Rate limit handling
- Offline mode graceful degradation
- User documentation
- CHANGELOG update

**Dependencies:** Phase 4

## Task Breakdown

### Phase 1: System Color Mode (2-3 hours)

| Task | Description | Estimate | Parallel |
|------|-------------|----------|----------|
| T001 | Add dark theme CSS custom properties | 20 min | - |
| T002 | Add prefers-color-scheme media query | 10 min | T001 |
| T003 | Implement ThemeController JavaScript | 25 min | T001 |
| T004 | Add theme toggle button to header | 15 min | T003 |
| T005 | Add localStorage persistence | 10 min | T003 |
| T006 | Add transition animations | 10 min | T004 |
| T007 | Verify WCAG contrast compliance | 15 min | T006 |

### Phase 2: GitHub Authentication (1-2 hours)

| Task | Description | Estimate | Parallel |
|------|-------------|----------|----------|
| T008 | Create github.py module skeleton | 15 min | - |
| T009 | Implement env var auth (GITHUB_TOKEN) | 15 min | T008 |
| T010 | Implement gh CLI auth extraction | 20 min | T009 |
| T011 | Implement config file auth | 15 min | T010 |
| T012 | Add get_github_client() with fallback | 15 min | T011 |
| T013 | Add `speckle github auth` command | 20 min | T012 |

### Phase 3: GitHub Sync (2-3 hours)

| Task | Description | Estimate | Parallel |
|------|-------------|----------|----------|
| T014 | Create github-links.jsonl storage | 15 min | - |
| T015 | Implement push_to_github() | 30 min | T014 |
| T016 | Implement pull_from_github() | 30 min | T015 |
| T017 | Add label/priority mapping | 20 min | T016 |
| T018 | Add `speckle github sync` command | 20 min | T017 |
| T019 | Add `speckle github push/pull` commands | 15 min | T018 |

### Phase 4: Board Integration (1-2 hours)

| Task | Description | Estimate | Parallel |
|------|-------------|----------|----------|
| T020 | Add GitHub icon SVG to card template | 15 min | - |
| T021 | Link icon to GitHub URL | 10 min | T020 |
| T022 | Add sync status to board footer | 15 min | T021 |
| T023 | Add --github flag to board.py | 15 min | T022 |
| T024 | Style GitHub elements for both themes | 15 min | T023 |

### Phase 5: Polish & Documentation (1 hour)

| Task | Description | Estimate | Parallel |
|------|-------------|----------|----------|
| T025 | Add rate limit handling with backoff | 20 min | - |
| T026 | Add offline graceful degradation | 15 min | T025 |
| T027 | Update README with GitHub setup | 15 min | T025 |
| T028 | Update CHANGELOG for v1.3.0 | 10 min | T027 |

## Parallel Execution Map

```
Phase 1: T001 ──┬── T002 ─────────────┐
                └── T003 ─┬── T004 ───┼── T006 ── T007
                          └── T005 ───┘

Phase 2: T008 ── T009 ── T010 ── T011 ── T012 ── T013

Phase 3: T014 ── T015 ── T016 ── T017 ── T018 ── T019

Phase 4: T020 ── T021 ── T022 ── T023 ── T024

Phase 5: T025 ──┬── T026
                └── T027 ── T028
```

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Token exposure | High | Never log tokens, use env vars |
| Rate limiting | Medium | Exponential backoff, cache responses |
| Contrast issues | Medium | Test with WCAG tools before merge |
| gh CLI not installed | Low | Graceful fallback, clear error message |
| Beads format changes | Low | Version check, schema validation |

## Definition of Done

### Color Mode
- [ ] Board auto-detects system preference
- [ ] Toggle button works correctly
- [ ] Preference persists in localStorage
- [ ] All text meets 4.5:1 contrast
- [ ] Smooth transitions (no flash)

### GitHub Integration
- [ ] Auth works via env, gh CLI, or config
- [ ] Can push beads to GitHub Issues
- [ ] Can pull GitHub Issues to beads
- [ ] Linkage tracked in JSONL
- [ ] GitHub icon appears on linked cards
- [ ] Rate limits handled gracefully
- [ ] Tokens never exposed in output

### Documentation
- [ ] README updated with GitHub setup
- [ ] CHANGELOG has v1.3.0 entry
- [ ] All commands have help text
