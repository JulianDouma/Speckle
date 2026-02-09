---
description: Synchronize spec-kit tasks.md with beads issue tracking (bidirectional)
---

# Speckle Sync

Bidirectional synchronization between `tasks.md` (planning) and beads (execution tracking).

## Arguments

```text
$ARGUMENTS
```

Process arguments if provided (e.g., `--dry-run`, `--force`).

## Prerequisites

Verify environment before proceeding:

```bash
# Check beads is available
if ! command -v bd &> /dev/null; then
    echo "❌ Beads not installed. Install from: https://github.com/steveyegge/beads"
    exit 1
fi

# Find feature directory (spec-kit convention: specs/NNN-feature-name/)
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
if [[ ! "$BRANCH" =~ ^[0-9]{3}- ]]; then
    echo "❌ Not on a feature branch. Expected: NNN-feature-name"
    echo "   Current branch: $BRANCH"
    exit 1
fi

PREFIX="${BRANCH:0:3}"
FEATURE_DIR=$(find specs -maxdepth 1 -type d -name "${PREFIX}-*" 2>/dev/null | head -1)

if [ -z "$FEATURE_DIR" ] || [ ! -f "$FEATURE_DIR/tasks.md" ]; then
    echo "❌ tasks.md not found. Run /speckit.tasks first."
    exit 1
fi

echo "📁 Feature: $FEATURE_DIR"
```

## Load Context

Read spec-kit documents for rich issue context:

```bash
SPEC_FILE="$FEATURE_DIR/spec.md"
PLAN_FILE="$FEATURE_DIR/plan.md"
TASKS_FILE="$FEATURE_DIR/tasks.md"
MAPPING_FILE="$FEATURE_DIR/.speckle-mapping.json"

# Initialize mapping if not exists
if [ ! -f "$MAPPING_FILE" ]; then
    echo '{"version":1,"feature":"'$BRANCH'","created":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","tasks":{}}' > "$MAPPING_FILE"
fi
```

## Parse Tasks

Extract tasks from `tasks.md`:

```javascript
// Task line format: - [ ] T001 [P] [US1] Description
// - [ ] = incomplete, - [x] = complete
// T001 = task ID
// [P] = parallel (optional)
// [US1] = user story (optional)

const taskRegex = /^-\s+\[([ x])\]\s+(T\d{3})\s*(\[P\])?\s*(\[US\d+\])?\s*(.+)$/

function parseTasks(content) {
    const tasks = []
    let currentPhase = "default"
    
    for (const line of content.split('\n')) {
        // Track phase headers
        const phaseMatch = line.match(/^#{2,3}\s+(.+)$/)
        if (phaseMatch) {
            currentPhase = phaseMatch[1]
            continue
        }
        
        const match = line.match(taskRegex)
        if (match) {
            tasks.push({
                completed: match[1] === 'x',
                id: match[2],
                parallel: !!match[3],
                story: match[4]?.replace(/[\[\]]/g, '') || null,
                description: match[5].trim(),
                phase: currentPhase
            })
        }
    }
    return tasks
}
```

## Sync Logic

For each task, determine action:

```javascript
const mapping = JSON.parse(fs.readFileSync(MAPPING_FILE))

for (const task of tasks) {
    const existing = mapping.tasks[task.id]
    
    if (existing) {
        // Task exists in mapping - reconcile status
        const beadStatus = exec(`bd show ${existing.beadId} --json | jq -r '.status'`)
        
        if (beadStatus === 'closed' && !task.completed) {
            // Bead closed but task not checked - update tasks.md
            markTaskComplete(task.id)
            console.log(`✓ Marked ${task.id} complete (synced from beads)`)
        } else if (task.completed && beadStatus !== 'closed') {
            // Task checked but bead open - close bead
            exec(`bd close ${existing.beadId}`)
            console.log(`✓ Closed ${existing.beadId} (synced from tasks.md)`)
        }
    } else if (!task.completed) {
        // New task - create bead issue
        const beadId = createBeadIssue(task)
        mapping.tasks[task.id] = {
            beadId: beadId,
            created: new Date().toISOString()
        }
        console.log(`+ Created ${beadId} for ${task.id}`)
    }
}

// Save updated mapping
mapping.lastSync = new Date().toISOString()
fs.writeFileSync(MAPPING_FILE, JSON.stringify(mapping, null, 2))
```

## Create Bead Issue

Build rich issue with context from spec and plan:

```javascript
function createBeadIssue(task) {
    // Extract relevant context
    const specContext = extractContext(SPEC_FILE, task.story)
    const planContext = extractContext(PLAN_FILE, task.phase)
    
    // Build description
    const description = `
## Task: ${task.description}

### Context
${specContext || 'See spec.md for full context'}

### Technical Approach  
${planContext || 'See plan.md for implementation details'}

### Metadata
- **Task ID**: ${task.id}
- **Phase**: ${task.phase}
- **Story**: ${task.story || 'N/A'}
- **Parallel**: ${task.parallel ? 'Yes' : 'No'}
- **Source**: ${TASKS_FILE}

---
*Synced by Speckle*
`.trim()

    // Determine priority from phase
    const priority = task.phase.match(/foundational|setup/i) ? 1 
                   : task.story === 'US1' ? 2 
                   : 3

    // Build labels
    const labels = ['speckle', `phase:${slugify(task.phase)}`]
    if (task.story) labels.push(`story:${task.story.toLowerCase()}`)
    if (task.parallel) labels.push('parallel')

    // Create issue
    const result = exec(`bd create "${task.id}: ${truncate(task.description, 60)}" \
        --type task \
        --priority ${priority} \
        --labels "${labels.join(',')}" \
        --description "${escape(description)}" \
        --silent`)
    
    return result.trim()
}
```

## Add Dependencies

Map task ordering to bead dependencies:

```javascript
// Phase-based: Later phases depend on earlier phases
const phases = [...new Set(tasks.map(t => t.phase))]
for (let i = 1; i < phases.length; i++) {
    const currentPhaseTasks = tasks.filter(t => t.phase === phases[i])
    const prevPhaseTasks = tasks.filter(t => t.phase === phases[i-1])
    
    // First task of current phase depends on all tasks of previous phase
    if (currentPhaseTasks[0] && prevPhaseTasks.length) {
        const currentBead = mapping.tasks[currentPhaseTasks[0].id]?.beadId
        for (const prev of prevPhaseTasks) {
            const prevBead = mapping.tasks[prev.id]?.beadId
            if (currentBead && prevBead) {
                exec(`bd dep add ${currentBead} ${prevBead}`)
            }
        }
    }
}
```

## Summary

```javascript
const created = Object.keys(mapping.tasks).length
const synced = tasks.filter(t => t.completed).length

console.log(`
✅ Speckle Sync Complete

📊 Summary:
   Tasks in tasks.md: ${tasks.length}
   Bead issues: ${created}
   Completed: ${synced}
   
📁 Mapping: ${MAPPING_FILE}

🎯 Next: Run \`bd ready\` to see available work
`)
```
