# Changelog

All notable changes to Speckle are documented here.

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
