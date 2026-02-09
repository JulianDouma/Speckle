# Spec 020: Ephemeral Claude Sessions for In-Progress Beads

## Executive Summary

This spec proposes that each in-progress bead automatically spawns an **ephemeral Claude session** that:
1. Opens when the bead transitions to `in_progress`
2. Works autonomously on the assigned task
3. Streams terminal output to the kanban board (via terminal mirroring)
4. Closes when the task is complete or explicitly terminated

**Verdict: This is a SMART approach**, supported by academic research and industry patterns.

---

## Research Findings

### Academic Support

| Source | Key Finding |
|--------|-------------|
| **AutoGen (arXiv:2308.08155)** | Multi-agent conversation framework - agents should be "customizable, conversable, and operate in various modes" |
| **HAX Framework (arXiv:2512.11979)** | "Behavioral proxy" concept - orchestrate agent activity to reduce cognitive load while maintaining transparency |
| **HAACS Position Paper (arXiv:2505.00018)** | "capacity-aware human interfaces" and "instantaneous and auditable reconfiguration" |
| **AI Agent Systems Survey (arXiv:2601.01743)** | Key trade-off: "autonomy vs controllability" - ephemeral sessions provide controllability |

### Industry Patterns

| Framework | Pattern |
|-----------|---------|
| **LangGraph** | Graph-based workflows with explicit state management and interrupt points |
| **CrewAI** | Flows orchestrating Crews - separation of orchestration from execution |
| **OpenAI Agents SDK** | Human-in-the-loop with persistent sessions per task |
| **Anthropic Prompt Caching** | 90% cost reduction for cached prompts - makes ephemeral sessions cost-effective |

### Existing Speckle Patterns

1. **Ralph Pattern** (speckle.loop): Fresh context per task, progress.txt persistence
2. **Mayor Pattern** (speckle.mayor): Coordinator that delegates but never implements
3. **Workers Pattern** (workers.sh): Ephemeral git worktrees per worker
4. **Terminal Mirroring**: Already implemented in this session

---

## Why Ephemeral Sessions Are Smart

### 1. Context Isolation ✓
```
Session A (bead-001: "Add auth")     Session B (bead-002: "Fix bug")
┌─────────────────────────┐          ┌─────────────────────────┐
│ Clean context           │          │ Clean context           │
│ No pollution from A     │          │ No pollution from B     │
│ Focused on single task  │          │ Focused on single task  │
└─────────────────────────┘          └─────────────────────────┘
```

**Problem with long-running sessions:**
- Context window fills up over time
- Early context gets "forgotten" (attention degradation)
- Cross-task pollution causes confusion

### 2. Cost Efficiency with Prompt Caching ✓

| Scenario | Cost per 1M tokens |
|----------|-------------------|
| No caching | $15 (base input) |
| Cache write (first call) | $18.75 (1.25x) |
| Cache hit (subsequent) | $1.50 (0.1x) |

**With ephemeral sessions:**
- System prompt cached for 5 minutes
- Multiple beads share cache if using same system prompt
- Only task-specific context is unique per session

### 3. Failure Isolation ✓

```
Bead A fails       →  Only A affected
Bead B continues   →  Unaware of A's failure
Mayor observes     →  Can reassign A's work
```

### 4. Parallelization ✓

```
                    ┌─────────────────┐
                    │     Mayor       │
                    │  (coordinator)  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Session A    │   │  Session B    │   │  Session C    │
│  bead-001     │   │  bead-002     │   │  bead-003     │
│  (parallel)   │   │  (parallel)   │   │  (parallel)   │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 5. Auditability ✓

- Each session has dedicated terminal log
- Clear start/end timestamps
- Easy to replay/debug specific tasks
- Supports LangSmith-style tracing

---

## Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         Kanban Board                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ BACKLOG  │  │IN PROGRESS│  │ BLOCKED  │  │   DONE   │        │
│  │          │  │ ┌──────┐ │  │          │  │          │        │
│  │  bead-3  │  │ │bead-1│ │  │          │  │  bead-0  │        │
│  │  bead-4  │  │ │ 🟢   │ │  │          │  │          │        │
│  │          │  │ │[Term]│ │  │          │  │          │        │
│  │          │  │ └──────┘ │  │          │  │          │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │ Click "Start Session" or auto-trigger
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Session Manager                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  spawn_session(bead_id) →                               │   │
│  │    1. Create terminal session                           │   │
│  │    2. Launch Claude CLI with task context               │   │
│  │    3. Stream output to WebSocket                        │   │
│  │    4. Monitor for completion                            │   │
│  │    5. Close bead on success                             │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Session Lifecycle

```
┌─────────────┐   bd update --status in_progress   ┌──────────────┐
│   BACKLOG   │ ────────────────────────────────▶  │  SPAWNING    │
│   (open)    │                                     │              │
└─────────────┘                                     └──────┬───────┘
                                                          │
                                    Session created       │
                                    Terminal attached     ▼
                                                   ┌──────────────┐
                                                   │   RUNNING    │
                                                   │  Claude CLI  │
                                                   │  working...  │
                                                   └──────┬───────┘
                                                          │
                              ┌────────────────────┬──────┴──────┐
                              │                    │             │
                              ▼                    ▼             ▼
                       ┌───────────┐       ┌───────────┐  ┌───────────┐
                       │ COMPLETED │       │  BLOCKED  │  │  FAILED   │
                       │  (closed) │       │  (stuck)  │  │  (error)  │
                       └───────────┘       └───────────┘  └───────────┘
```

---

## Implementation Plan

### Phase 1: Session Manager (Core)

Create `session_manager.py` that:

```python
class BeadSessionManager:
    """Manages ephemeral Claude sessions for in-progress beads."""
    
    def spawn_session(self, bead_id: str) -> Session:
        """
        1. Get bead details from `bd show <id>`
        2. Create terminal session (terminal_server.py)
        3. Launch Claude CLI with task context
        4. Return session handle
        """
        
    def terminate_session(self, bead_id: str) -> bool:
        """
        1. Send SIGTERM to Claude process
        2. Wait for graceful shutdown
        3. Update bead status
        4. Clean up terminal session
        """
        
    def get_session_status(self, bead_id: str) -> SessionStatus:
        """Check if session is running, blocked, or completed."""
```

### Phase 2: Auto-Spawn on Status Change

Hook into `bd update --status in_progress`:

```bash
# In bd daemon or via file watcher
on_status_change(bead_id, old_status, new_status):
    if new_status == "in_progress" and old_status == "open":
        session_manager.spawn_session(bead_id)
    elif new_status == "closed" or new_status == "blocked":
        session_manager.terminate_session(bead_id)
```

### Phase 3: Task Context Injection

Each session receives:

```markdown
## Task Assignment

**Bead:** {BEAD_ID}
**Title:** {TITLE}
**Description:** {DESCRIPTION}
**Priority:** P{PRIORITY}

## Previous Learnings
{CONTENTS_OF_PROGRESS_TXT}

## Definition of Done
1. Code compiles/runs without errors
2. Tests pass (if applicable)
3. Changes committed to git
4. Update progress.txt with learnings

## On Completion
Run: `bd close {BEAD_ID} --reason "Your summary"`
```

### Phase 4: Board UI Integration

Enhance kanban cards for in-progress beads:

```
┌─────────────────────────────────────┐
│ 🔄 bead-abc  [P1]                   │
│ ─────────────────────────────────── │
│ Add user authentication             │
│ ─────────────────────────────────── │
│ 🟢 Session active (2m 34s)          │
│ ─────────────────────────────────── │
│ [View Terminal] [Send Ctrl+C] [Stop]│
│ ─────────────────────────────────── │
│ Last output: "Running tests..."     │
└─────────────────────────────────────┘
```

### Phase 5: Mayor Integration

The Mayor can orchestrate multiple sessions:

```python
class Mayor:
    def execute_plan(self, plan: ExecutionPlan):
        for task in plan.parallelizable_tasks:
            bd.update(task.bead_id, status="in_progress")
            # Auto-spawn triggers session
            
        # Monitor all sessions
        while active_sessions:
            for session in active_sessions:
                if session.completed:
                    bd.close(session.bead_id)
                elif session.stuck:
                    self.handle_stuck(session)
```

---

## Claude CLI Integration

### Option A: Use `claude` CLI (Recommended)

```bash
# The Claude Code CLI with task context
claude --task "$(bd show $BEAD_ID)" \
       --dangerously-skip-permissions \
       --output-format stream
```

### Option B: Use Anthropic API directly

```python
# For more control, use the API
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    system=[{
        "type": "text",
        "text": SPECKLE_SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"}  # 5-min cache
    }],
    messages=[{
        "role": "user",
        "content": task_context
    }],
    max_tokens=8192,
    stream=True
)
```

### Option C: Use MCP Tools

Claude can use bd commands directly:

```json
{
    "name": "bd_update",
    "description": "Update bead status",
    "input_schema": {
        "type": "object",
        "properties": {
            "bead_id": {"type": "string"},
            "status": {"enum": ["open", "in_progress", "blocked", "closed"]}
        }
    }
}
```

---

## Cost Analysis

### Assumptions
- Average task: 10 API calls
- System prompt: 4000 tokens (cached)
- Task context: 2000 tokens (unique)
- Output: 500 tokens per call

### Per-Bead Cost (with caching)

| Component | Tokens | Rate | Cost |
|-----------|--------|------|------|
| System prompt (cache write) | 4000 | $18.75/MTok | $0.075 |
| System prompt (9 cache hits) | 36000 | $1.50/MTok | $0.054 |
| Task context (10 calls) | 20000 | $15/MTok | $0.30 |
| Output (10 calls) | 5000 | $75/MTok | $0.375 |
| **Total per bead** | | | **~$0.80** |

### Without Caching

| Component | Tokens | Rate | Cost |
|-----------|--------|------|------|
| System prompt (10 calls) | 40000 | $15/MTok | $0.60 |
| Task context (10 calls) | 20000 | $15/MTok | $0.30 |
| Output (10 calls) | 5000 | $75/MTok | $0.375 |
| **Total per bead** | | | **~$1.28** |

**Caching saves ~37% per bead session.**

---

## Security Considerations

1. **Sandboxing**: Sessions run in isolated git worktrees
2. **Resource Limits**: Max concurrent sessions, timeout per session
3. **Secrets**: Never expose API keys in terminal output
4. **Human Approval**: Critical actions require confirmation

---

## File Structure

```
.speckle/
├── sessions/
│   ├── {bead-id}/
│   │   ├── session.json      # Session metadata
│   │   ├── context.md        # Injected task context
│   │   └── output.log        # Terminal output
├── scripts/
│   ├── session_manager.py    # NEW: Session lifecycle
│   ├── terminal_server.py    # Existing: WebSocket server
│   └── board.py              # Enhanced: Session UI
```

---

## Definition of Done

- [ ] Session manager spawns Claude on `in_progress`
- [ ] Terminal output streams to kanban board
- [ ] Session terminates on `closed` or `blocked`
- [ ] Mayor can orchestrate multiple sessions
- [ ] Cost tracking per session
- [ ] Graceful error handling (stuck, timeout, crash)
- [ ] Documentation updated

---

## References

1. AutoGen: Multi-Agent Conversation (arXiv:2308.08155)
2. HAX Framework: Human-Agent Interaction (arXiv:2512.11979)
3. Anthropic Prompt Caching Documentation
4. LangGraph Human-in-the-Loop Patterns
5. CrewAI Flows and Crews Architecture
