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
git clone https://github.com/YOUR-USERNAME/Speckle.git
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
