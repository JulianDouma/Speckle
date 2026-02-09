# Changelog

All notable changes to Speckle are documented here.

## [1.3.0] - 2026-02-09

### System Color Mode & GitHub Integration

Addresses [#16](https://github.com/JulianDouma/Speckle/issues/16) - Add system color mode and GitHub issue integration.

### Added

#### System Color Mode
- Automatic dark/light theme detection via `prefers-color-scheme`
- Theme toggle button in board header (sun/moon icons)
- localStorage persistence for user preference
- Smooth CSS transitions between themes
- WCAG 2.1 AA compliant contrast ratios
- Dark theme colors:
  - Background: slate-900 (#0f172a)
  - Cards: slate-800 (#1e293b)
  - Text: slate-200 (#e2e8f0)
  - Accessible priority/type badges

#### GitHub Integration
- `/speckle.github.auth` - Check authentication status
- `/speckle.github.sync` - Bidirectional sync with GitHub Issues
- Layered authentication:
  1. Environment variables (GITHUB_TOKEN, GH_TOKEN)
  2. GitHub CLI (gh auth token)
  3. Config file (~/.speckle/config.toml)
- Label mapping (priority/type to GitHub labels)
- Issue linkage tracking (.speckle/github-links.jsonl)
- GitHub icon on linked board cards
- `--github` flag for board to show GitHub links

### Board Enhancements
- New `--github` flag to display GitHub links on cards
- GitHub icon SVG in card header for linked issues
- Click to open linked issue in GitHub

### Technical
- `github.py` - 500+ lines, pure stdlib (no PyGithub dependency)
- Uses GitHub REST API via urllib
- Rate limit handling
- Built using Speckle workflow (28 tasks across 5 phases)
- Full spec in `specs/016-board-enhancements/`

### Systematic Issue Creation Workflow

Addresses [#2](https://github.com/JulianDouma/Speckle/issues/2) - Systematic approach for defining issues using Speckle.

### Added
- `/speckle.issue` command for guided issue creation
  - Interactive type selection (feature, bug, enhancement, chore, docs)
  - Severity/priority assignment for bugs
  - Optional spec linking for complex features
  - Automatic GitHub issue creation with proper templates
  - Automatic beads sync with cross-references
  - Smart next steps suggestions based on issue type
- `/speckle.triage` command for issue review and prioritization
  - Dashboard view with GitHub and beads counts
  - `--sync` option to sync GitHub issues to beads
  - `--review` option for interactive issue review
  - `--stale` option to find stale issues
- GitHub Issue templates in `.github/ISSUE_TEMPLATE/`:
  - `feature.md` - Feature requests with acceptance criteria
  - `bug.md` - Bug reports with severity tracking
  - `enhancement.md` - Improvement suggestions
  - `chore.md` - Maintenance and housekeeping tasks
  - `docs.md` - Documentation requests
  - `config.yml` - Template chooser configuration

### Benefits
- Consistent issue quality across the project
- Self-hosted validation (using Speckle to manage Speckle)
- Unified tracking across GitHub Issues and Beads
- Reduced friction for capturing ideas
- Automatic cross-references between systems

## [1.2.0] - 2026-02-09

### Kanban Board

Web-based kanban board for visualizing beads issues.

### Added
- `/speckle.board` command to launch kanban board server
  - 4-column layout: Backlog, In Progress, Blocked, Done
  - Priority color coding (P0-P4)
  - Type badges (task, bug, feature, epic)
  - Time ago formatting ("2h ago")
  - Label display on cards (up to 3)
  - Label filter dropdown
  - Auto-refresh (configurable interval)
  - Responsive CSS grid (tablet/mobile)
- Command-line options:
  - `--port`: Custom port (default: 8420)
  - `--filter`: Filter by label
  - `--refresh`: Refresh interval in seconds
  - `--no-browser`: Don't auto-open browser
- API endpoints:
  - `GET /`: HTML board
  - `GET /api/issues`: JSON issue list
  - `GET /health`: Health check
- `board.py` script using Python stdlib only (zero dependencies)

### Technical
- Built using Speckle workflow (self-hosted development)
- 17 tasks across 4 phases tracked in beads
- Full spec-kit specification in `specs/008-kanban-board/`

## [1.1.0] - 2026-02-09

### Improved Installation Experience

Addresses [#1](https://github.com/JulianDouma/Speckle/issues/1).

### Added
- `/speckle.doctor` command for diagnosing installation and configuration issues
  - Prerequisites check (git, gh, bd, specify)
  - Directory structure validation
  - Script permissions verification
  - Beads integration health check
  - `--fix` option for automatic repairs
  - `--verbose` option for detailed output
- `--help` option with comprehensive usage information
- `--uninstall` option to cleanly remove Speckle
- `--check` option to run health check without installing
- `--force` option to skip prerequisite warnings
- `--quiet` option for minimal output
- `--version` option to show version
- Color-coded terminal output (with fallback for non-color terminals)
- Shell environment detection (bash, zsh, fish)
- Post-install verification check

### Improved
- Comprehensive prerequisite validation with recovery suggestions
- Better error messages with actionable guidance
- Preserved existing files during uninstall (beads data, specs)
- Version bumped to 1.1.0

## [1.0.0] - 2026-02-09

### Production Release

Speckle is now production-ready! This release marks the completion of the self-hosted development cycle, where each version was built using the previous version.

### Features

#### Core Commands
- `/speckle.sync` - Bidirectional sync between spec-kit tasks.md and beads
- `/speckle.implement` - Implement tasks with automatic progress tracking
- `/speckle.status` - Show feature progress with epic and phase breakdown
- `/speckle.progress` - Add manual progress notes during implementation

#### Workflow Commands
- `/speckle.bugfix` - Start a bugfix workflow
- `/speckle.hotfix` - Start an urgent production fix workflow

#### Helper Libraries
- `comments.sh` - Comment formatting and safe recording
- `labels.sh` - Rich label generation (feature, phase, story, parallel)
- `epics.sh` - Epic lifecycle management

#### Formulas
- `speckle-feature.toml` - Full feature workflow setup
- `speckle-bugfix.toml` - Lightweight bugfix setup

### Development History

| Version | Feature | Built Using |
|---------|---------|-------------|
| v0.1.0 | Bootstrap (sync, implement) | Manual |
| v0.2.0 | Comments integration | v0.1.0 |
| v0.3.0 | Enhanced labels | v0.2.0 |
| v0.4.0 | Epic lifecycle | v0.3.0 |
| v0.5.0 | Formulas | v0.4.0 |
| v0.6.0 | Bugfix workflow | v0.5.0 |
| v1.0.0 | Production ready | v0.6.0 |

### Acknowledgments

- [GitHub Spec Kit](https://github.com/github/spec-kit) - Spec-driven development methodology
- [Beads](https://github.com/steveyegge/beads) - AI-native issue tracking

---

## [0.6.0] - 2026-02-09

### Added
- `/speckle.bugfix` command for standard bugfix workflow
- `/speckle.hotfix` command for urgent production fixes

## [0.5.0] - 2026-02-09

### Added
- `speckle-feature.toml` formula for feature workflows
- `speckle-bugfix.toml` formula for bugfix workflows
- Formula installation in `install.sh`

## [0.4.0] - 2026-02-09

### Added
- Epic lifecycle management (`epics.sh`)
- Automatic epic creation during sync
- Epic progress display in status
- `--epics` option for multi-epic view

## [0.3.0] - 2026-02-09

### Added
- Rich label generation (`labels.sh`)
- Feature, phase, story, and parallel labels
- Label filtering support
- Phase/story breakdown in status

## [0.2.0] - 2026-02-09

### Added
- Comment recording (`comments.sh`)
- `/speckle.status` command
- `/speckle.progress` command
- Automatic progress tracking in implement

## [0.1.0-bootstrap] - 2026-02-09

### Added
- Initial `/speckle.sync` command
- Initial `/speckle.implement` command
- Project structure and documentation
