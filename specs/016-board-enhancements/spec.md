# Board Enhancements: System Color Mode & GitHub Integration

## Problem Statement

The Speckle Kanban Board currently has two limitations:

1. **Fixed Light Theme** - Causes eye strain in dark environments, doesn't respect OS preferences, and looks inconsistent with other dev tools (VS Code, terminals).

2. **No GitHub Integration** - Issues only exist in local beads storage with no visibility for collaborators, no GitHub notifications, and no cross-referencing with PRs/commits.

## Goals

### Color Mode
- Respect system `prefers-color-scheme` automatically
- Allow user override with toggle button
- Persist preference across sessions
- Meet WCAG 2.1 AA accessibility standards (4.5:1 contrast)

### GitHub Integration
- Authenticate via environment variable, gh CLI, or config file
- Bidirectional sync between beads and GitHub Issues
- Show GitHub links on board cards
- Handle rate limiting and offline scenarios gracefully

## Non-Goals

- OAuth web flow (too complex for local tool)
- GitHub Projects integration (future enhancement)
- Real-time websocket sync (polling is sufficient)
- Full GitHub issue editing from board (read + link only)
- Supporting GitLab/Bitbucket (GitHub only for MVP)

## User Stories

### US1: Automatic Dark Mode
As a developer working in low-light, I want the board to automatically use dark mode when my OS is set to dark mode so that I don't strain my eyes.

**Acceptance Criteria:**
- Board detects `prefers-color-scheme: dark`
- Dark theme uses appropriate colors for readability
- All text meets WCAG 2.1 AA contrast requirements
- Column backgrounds are distinct but not jarring

### US2: Manual Theme Toggle
As a developer, I want to manually toggle between light and dark mode so that I can override my system preference when needed.

**Acceptance Criteria:**
- Toggle button visible in header
- Click toggles between light/dark
- Icon reflects current state (sun/moon)
- Smooth transition animation

### US3: Theme Persistence
As a developer, I want my theme preference to persist so that I don't have to set it every time.

**Acceptance Criteria:**
- Preference stored in localStorage
- Survives page refresh
- Survives browser restart
- Can reset to system default

### US4: Link Issues to GitHub
As a team lead, I want to push beads issues to GitHub so that stakeholders can see progress without CLI access.

**Acceptance Criteria:**
- Issues appear in GitHub with correct title/body
- Status mapped to open/closed
- Priority mapped to labels
- Linked issues trackable in both systems

### US5: Pull Issues from GitHub
As a developer, I want to pull GitHub issues into beads so that I can track external issues in my local workflow.

**Acceptance Criteria:**
- GitHub issues create corresponding beads
- Labels and state preserved
- Duplicate detection via linkage
- Manual link/unlink commands available

### US6: GitHub Badge on Cards
As a developer, I want to see which board cards are linked to GitHub so that I can quickly open the GitHub issue.

**Acceptance Criteria:**
- GitHub icon on linked cards
- Click opens issue in new tab
- Visual distinction from unlinked cards

## Technical Design

### Color Mode Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────┐
│  OS Preference  │────▶│  CSS Variables   │────▶│   Rendered    │
│  (prefers-     │     │  (:root, [data-  │     │   Board UI    │
│  color-scheme) │     │   theme="dark"]) │     │               │
└─────────────────┘     └──────────────────┘     └───────────────┘
         ▲                       ▲
         │                       │
         │              ┌────────┴────────┐
         │              │   JavaScript    │
         └──────────────│   Theme        │
                        │   Controller   │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │  localStorage   │
                        │  (persistence)  │
                        └─────────────────┘
```

### GitHub Integration Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   beads     │◀───▶│  github.py  │◀───▶│   GitHub    │
│  (JSONL)    │     │  (sync)     │     │   Issues    │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │   links     │
                    │  (JSONL)    │
                    └─────────────┘
```

### Authentication Priority

1. `GITHUB_TOKEN` / `GH_TOKEN` environment variable
2. `gh auth token` (GitHub CLI)
3. `~/.speckle/config.toml` (user config)
4. Graceful fallback (features disabled)

### File Structure

```
.speckle/
├── scripts/
│   ├── board.py      # (existing) + dark mode CSS
│   └── github.py     # (new) GitHub sync logic
├── github-links.jsonl  # (new) linkage tracking
└── config.toml       # (new) optional config
```

### Color Palette

| Variable | Light | Dark |
|----------|-------|------|
| `--bg` | #f8fafc | #0f172a |
| `--card-bg` | #ffffff | #1e293b |
| `--text` | #1e293b | #e2e8f0 |
| `--text-muted` | #64748b | #94a3b8 |
| `--backlog` | #f1f5f9 | #1e293b |
| `--progress` | #dbeafe | #1e3a5f |
| `--blocked` | #fee2e2 | #451a1a |
| `--done` | #d1fae5 | #14532d |

## Constraints

- Must work with Python 3.8+ (stdlib only for core)
- GitHub integration must work without PyGithub (use gh CLI or requests)
- Tokens must NEVER be logged or stored in repo
- Must handle rate limiting gracefully (5000 req/hr authenticated)
- Dark mode must not require JavaScript (CSS-first approach)

## Security Requirements

- Tokens only from env vars, gh CLI, or user home config
- Never store tokens in `.speckle/config.toml` (repo-committed)
- Mask tokens in any error output (`ghp_***`)
- Use fine-grained tokens when possible

## Success Metrics

- Color mode detection works instantly (no flash)
- Theme toggle responds < 100ms
- GitHub sync completes < 5s for 50 issues
- Zero token exposure in logs
- All contrast ratios > 4.5:1

## References

- [Analysis Document](../../docs/BOARD-ENHANCEMENTS-ANALYSIS.md)
- [GitHub Issue #16](https://github.com/JulianDouma/Speckle/issues/16)
