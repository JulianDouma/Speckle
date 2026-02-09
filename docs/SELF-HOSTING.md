# Speckle Self-Hosted Development

Speckle is developed using Speckle - the ultimate dogfooding approach.

## The Bootstrap Problem

We can't use Speckle v1.0 to build Speckle v1.0 because it doesn't exist yet.

**Solution:** A phased bootstrap approach.

## Development Phases

### Phase 0: Bootstrap (Manual)

Create minimal Speckle manually:
- Repository structure
- Basic `/speckle.sync` command
- Basic `/speckle.implement` command

Tag as `v0.1.0-bootstrap`

### Phase 1: Self-Hosting Begins

Use v0.1.0 to develop v0.2.0:

```bash
# Create feature branch
git checkout -b 001-comments-integration

# Use spec-kit for planning
/speckit.specify "Add beads comments for progress tracking"
/speckit.plan
/speckit.tasks

# Use Speckle for tracking (our own tool!)
/speckle.sync
/speckle.implement  # Repeat until done

# Tag release
git tag v0.2.0
```

### Phase 2: Iterative Improvement

Each version develops the next:

| Version | Features Added | Developed Using |
|---------|---------------|-----------------|
| v0.1.0 | Bootstrap (sync, implement) | Manual |
| v0.2.0 | Comments integration | v0.1.0 |
| v0.3.0 | Enhanced labels | v0.2.0 |
| v0.4.0 | Epic lifecycle | v0.3.0 |
| v0.5.0 | Formulas | v0.4.0 |
| v0.6.0 | Bugfix workflow | v0.5.0 |
| v1.0.0 | Production ready | v0.6.0 |

## Self-Validation

Every feature validates itself:

| Feature | Self-Validation |
|---------|----------------|
| Comments | Comments appear on own task issues |
| Labels | Own issues have rich labels |
| Epic lifecycle | Own feature epics tracked |
| Formulas | Use formula for own development |

## Dogfood Log

Maintain `DOGFOOD.md` capturing insights:

```markdown
## v0.2.0 Development

### Pain Points Discovered
- Missing feature X → Planned for v0.3.0

### What Worked Well
- Feature Y saved time

### Mid-Development Improvements
- Fixed bug in sync script
```

## Getting Started

```bash
# Clone Speckle
git clone https://github.com/JulianDouma/Speckle.git
cd Speckle

# Start new feature
git checkout -b NNN-feature-name

# Use Speckle to develop Speckle!
/speckit.specify "Your improvement"
/speckit.plan
/speckit.tasks
/speckle.sync
/speckle.implement
```

---

## Dogfood Log

### v0.2.0 Development (2026-02-09)

**Feature:** Beads Comments Integration

**Developed Using:** v0.1.0-bootstrap (manual sync, manual beads issue creation)

#### What Worked Well
- Beads issue tracking provided clear task visibility via `bd ready`
- Task closure gave satisfying progress feedback
- Branch naming convention (001-feature-name) worked seamlessly with spec-kit

#### Pain Points Discovered
- Manual sync is tedious → `/speckle.sync` automation is essential
- No way to see progress mid-implementation → Added `/speckle.progress`
- Needed status overview → Added `/speckle.status`

#### Self-Validation
- ✅ Created 14 bead issues for v0.2.0 tasks
- ✅ Used `bd update --status in_progress` to claim tasks
- ✅ Used `bd close` to complete tasks
- ⏳ Comment recording will self-validate in v0.3.0 development

#### Metrics
- Tasks: 14 (T001-T014)
- User Stories: 3 (US1: Core comments, US2: Status, US3: Manual notes)
- Commands Added: 2 (`/speckle.status`, `/speckle.progress`)
- Commands Updated: 1 (`/speckle.implement`)
- Helper Scripts: 1 (`comments.sh`)

### v0.3.0 Development (2026-02-09)

**Feature:** Enhanced Labels

**Developed Using:** v0.2.0 (comments integration, status command, sync automation)

#### What Worked Well
- Parallel task markers (`[P]`) enabled multiple agents to work simultaneously on foundation tasks (T002, T003)
- Phase-based organization provided clear structure: Foundation → US1 → US2 → US3 → Polish
- Label filtering with `bd list --label` validated immediately - used to query own tasks by version, phase, and story
- Story markers (`[US1]`, `[US2]`, `[US3]`) mapped cleanly to story labels for traceability
- Self-dogfooding: the label system was tested on its own issues during development

#### Pain Points Discovered
- No issues discovered - the enhanced labels feature worked as designed
- Label generation from branch names, phases, and story markers all functioning correctly

#### Self-Validation (T016)
- ✅ `bd list --label v0.3.0` returns all 16 tasks with version label
- ✅ `bd list --label phase:us1` returns 5 tasks for User Story 1
- ✅ `bd list --label phase:us2` returns 2 tasks for User Story 2 (closed)
- ✅ `bd list --label phase:us3` returns 3 tasks for User Story 3 (closed)
- ✅ `bd list --label phase:polish` returns 2 tasks for Polish phase
- ✅ `bd list --label phase:foundation` returns 4 tasks (all closed)
- ✅ `bd list --label story:us1` returns tasks with story marker
- ✅ Labels include: `speckle`, `v0.3.0`, `phase:*`, `story:*`, `task`, `docs`

#### Metrics
- Tasks: 16 (T001-T016)
- User Stories: 3 (US1: Auto labels, US2: Filter labels, US3: Status enhancement)
- Phases: 5 (Foundation, US1, US2, US3, Polish)
- Commands Updated: 1 (`/speckle.status` - phase grouping, --by-story)
- Helper Scripts: 1 (`labels.sh` - slugify, extract_phase_label, extract_story_label, build_label_string)
- Files Changed: 7
- Lines Added: 587

#### Development Approach
- Used parallel agents for foundation phase (T002, T003 marked with `[P]`)
- Sequential implementation for user story phases
- Self-validation baked into polish phase (T016)

### v0.4.0 Development (2026-02-09)

**Feature:** Epic Lifecycle

**Developed Using:** v0.3.0 (enhanced labels, phase markers, story labels)

#### What Worked Well
- Parallel agent execution for foundation tasks (T002, T003) maximized throughput
- Clear separation of concerns: epics.sh handles lifecycle, sync.md orchestrates creation
- Phase-based organization (Foundation → US1 → US2 → US3 → Polish) provided clear structure
- All 4 work streams (foundation, US1, US2, US3) could be parallelized with sub-agents
- Label system from v0.3.0 enabled clear task filtering by phase and story

#### Pain Points Discovered
- None - implementation went smoothly
- The epic lifecycle feature design aligned well with existing beads capabilities (`bd dep add` for linking)

#### Self-Validation (T017)
- ✅ Feature 003-epic-lifecycle would benefit from an epic to track overall progress
- ✅ `bd list --label epic` returns no epics yet (this is the feature that creates them!)
- ✅ The epic feature validates itself: once deployed, future features will have epics
- ✅ This is a "chicken and egg" scenario - v0.4.0 creates the epic system, v0.5.0+ will use it

#### Metrics
- Tasks: 17 (T001-T017)
- User Stories: 3 (US1: Epic creation, US2: State transitions, US3: Progress display)
- Phases: 5 (Foundation, US1, US2, US3, Polish)
- Helper Scripts: 1 (`epics.sh` - create_epic, get_epic_id, update_epic_status, get_epic_progress, link_task_to_epic)
- Functions Added: 6 (in epics.sh)
- Commands Updated: 2 (`/speckle.sync`, `/speckle.status`)

#### Development Approach
- Foundation phase: 5 tasks for epics.sh infrastructure (T001-T005)
- US1 phase: 4 tasks for epic creation during sync (T006-T009)
- US2 phase: 3 tasks for state transitions (T010-T012)
- US3 phase: 3 tasks for progress display (T013-T015)
- Polish phase: 2 tasks for documentation and self-validation (T016-T017)
- Parallelization: T002/T003 marked with `[P]`, all 4 work streams executed via sub-agents

### v0.5.0 Development (2026-02-09)

**Feature:** Formulas Integration

**Developed Using:** v0.4.0 (epic lifecycle, phase markers, enhanced labels)

#### What Worked Well
- Quick implementation - formulas feature was straightforward to integrate
- TOML format is clean and readable for formula definitions
- Minimal scope kept the feature focused and manageable
- `bd formula list` command works well - found 32 formulas across workflow, expansion, and aspect categories

#### Pain Points Discovered
- None - implementation went smoothly
- Note: No local `.beads/formulas/` directory needed - formulas discovered from global/embedded sources

#### Self-Validation
- ✅ `bd formula list` shows 32 available formulas (workflow, expansion, aspect categories)
- ✅ Formula categories include: workflow (27), expansion (1), aspect (1), plus 3 Towers of Hanoi variants
- ✅ Formulas include shiny, shiny-enterprise, shiny-secure, and mol-* molecules
- ⏳ First version where formulas could be used to create Speckle itself (but weren't yet)
- ⏳ Future versions will dogfood formulas for feature development

#### Metrics
- Tasks: 6 (minimal scope, focused feature)
- Implementation: Straightforward integration with existing bd formula subcommands
- Formula discovery: Global/embedded formulas work without local `.beads/formulas/` directory

#### Development Approach
- Focused feature with minimal task count
- Clean integration with existing beads infrastructure
- Self-validation confirms formula discovery works correctly

### v0.6.0 Development (2026-02-09)

**Feature:** Bugfix Workflow

**Developed Using:** v0.5.0 (formulas integration, epic lifecycle, enhanced labels)

#### What Worked Well
- Simple, focused feature - bugfix/hotfix commands are lightweight
- Clear separation: `/speckle.bugfix` for standard bugs, `/speckle.hotfix` for urgent issues
- Integrates with existing formula system (`bd formula speckle-bugfix`)
- Minimal implementation scope kept development quick

#### Pain Points Discovered
- None - straightforward feature implementation

#### Self-Validation
- ⚠️ This feature itself wasn't a bugfix, so couldn't fully self-validate
- ✅ Establishes the pattern for future bugfix workflows
- ✅ Commands created and documented for immediate use
- ⏳ First real bugfix will validate the workflow end-to-end

#### Metrics
- Tasks: 4 (T001-T004)
- Commands Added: 2 (`/speckle.bugfix`, `/speckle.hotfix`)
- Documentation: README bugfix section, SELF-HOSTING.md entry

#### Development Approach
- Phase 1: Command creation (T001-T002, parallel)
- Phase 2: Documentation (T003-T004, parallel)
- Minimal scope, focused on bugfix/hotfix differentiation
