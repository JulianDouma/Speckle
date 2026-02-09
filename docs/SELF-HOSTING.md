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
