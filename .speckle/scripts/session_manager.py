#!/usr/bin/env python3
"""
Speckle Session Manager

Manages ephemeral Claude sessions for in-progress beads.
Each bead gets its own isolated Claude session that:
1. Spawns when bead transitions to in_progress
2. Works autonomously on the assigned task
3. Streams terminal output to the kanban board
4. Terminates when task is complete

Based on research from:
- AutoGen: Multi-agent conversation (arXiv:2308.08155)
- HAX Framework: Human-agent interaction (arXiv:2512.11979)
- Anthropic Prompt Caching for cost efficiency
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, List, Any, Callable, Set
import threading
import re

# Try to import terminal_server for integration
HAS_TERMINAL_SERVER = False
terminal_manager: Any = None
spawn_with_terminal: Any = None
try:
    from terminal_server import terminal_manager as _tm, spawn_with_terminal as _swt  # type: ignore
    terminal_manager = _tm
    spawn_with_terminal = _swt
    HAS_TERMINAL_SERVER = True
except ImportError:
    pass


# === Configuration ===
# Find project root (where .speckle directory lives)
def _find_project_root() -> Path:
    """Find the project root by looking for .speckle directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".speckle").is_dir():
            return current
        current = current.parent
    # Fallback to cwd
    return Path.cwd()

PROJECT_ROOT = _find_project_root()
SESSIONS_DIR = PROJECT_ROOT / ".speckle/sessions"
PROGRESS_FILE = PROJECT_ROOT / ".speckle/progress.txt"
MAX_CONCURRENT_SESSIONS = 3
SESSION_TIMEOUT = 1800  # 30 minutes default
HEARTBEAT_INTERVAL = 5  # seconds


class SessionState(Enum):
    """Possible states for a bead session."""
    PENDING = "pending"      # Waiting to spawn
    SPAWNING = "spawning"    # Session starting up
    RUNNING = "running"      # Claude is working
    STUCK = "stuck"          # No progress, needs help
    COMPLETED = "completed"  # Task finished successfully
    FAILED = "failed"        # Session crashed/errored
    TERMINATED = "terminated"  # Manually stopped


class AgentRole(Enum):
    """Agent roles based on opencode-agent-conversations framework."""
    CEO = "ceo"           # Tier 1: Strategy, priorities, success metrics
    PM = "pm"             # Tier 1: Delivery planning, scope, risks
    CTO = "cto"           # Tier 2: Technical strategy, architecture, NFRs
    PO = "po"             # Tier 2: Product outcomes, requirements, ACs
    DEV = "dev"           # Tier 3: Implementation, bug fixes, features
    RESEARCH = "research" # Tier 2: Investigation, evidence, risks
    MARKETING = "marketing"  # Tier 3: Messaging, positioning, docs


class AgentTier(Enum):
    """Agent hierarchy tiers."""
    ORCHESTRATOR = 1  # CEO, PM - Strategy and coordination
    SUPERVISOR = 2    # CTO, PO, RESEARCH - Domain expertise
    WORKER = 3        # DEV, MARKETING - Implementation


# Role-based session configuration
# Derived from opencode-agent-conversations + Gastown session model
ROLE_SESSION_CONFIG: Dict[str, Dict[str, Any]] = {
    "ceo": {
        "tier": AgentTier.ORCHESTRATOR,
        "ephemeral": False,
        "timeout": 7200,  # 2 hours
        "max_concurrent": 1,
        "tools": {"bd", "read"},
        "worktree": False,
        "description": "Strategic planning and prioritization",
    },
    "pm": {
        "tier": AgentTier.ORCHESTRATOR,
        "ephemeral": False,
        "timeout": 7200,  # 2 hours
        "max_concurrent": 1,
        "tools": {"bd", "read"},
        "worktree": False,
        "description": "Delivery planning and work decomposition",
    },
    "cto": {
        "tier": AgentTier.SUPERVISOR,
        "ephemeral": True,
        "timeout": 3600,  # 1 hour
        "max_concurrent": 1,
        "tools": {"read", "github", "sentry"},
        "worktree": False,
        "description": "Technical architecture and review",
    },
    "po": {
        "tier": AgentTier.SUPERVISOR,
        "ephemeral": True,
        "timeout": 3600,  # 1 hour
        "max_concurrent": 1,
        "tools": {"read", "bd"},
        "worktree": False,
        "description": "Product requirements and acceptance criteria",
    },
    "dev": {
        "tier": AgentTier.WORKER,
        "ephemeral": True,
        "timeout": 1800,  # 30 min
        "max_concurrent": 3,
        "tools": {"read", "write", "bash", "git", "github", "bd"},
        "worktree": True,
        "description": "Implementation and code changes",
    },
    "research": {
        "tier": AgentTier.SUPERVISOR,
        "ephemeral": True,
        "timeout": 2400,  # 40 min
        "max_concurrent": 1,
        "tools": {"read", "webfetch", "bd"},
        "worktree": False,
        "description": "Investigation and evidence gathering",
    },
    "marketing": {
        "tier": AgentTier.WORKER,
        "ephemeral": True,
        "timeout": 1800,  # 30 min
        "max_concurrent": 1,
        "tools": {"read", "write", "bd"},
        "worktree": False,
        "description": "Documentation and content creation",
    },
}


# Intent-based role assignment for beads
BEAD_INTENT_ROLE_MAPPING: Dict[str, str] = {
    # Labels/keywords -> Primary role for worker session
    "feature": "dev",
    "bug": "dev",
    "bugfix": "dev",
    "refactor": "dev",
    "test": "dev",
    "testing": "dev",
    "docs": "marketing",
    "documentation": "marketing",
    "copy": "marketing",
    "research": "research",
    "investigate": "research",
    "analysis": "research",
    "architecture": "cto",
    "design": "cto",
    "requirements": "po",
    "story": "po",
    "acceptance": "po",
}


@dataclass
class SessionConfig:
    """Configuration for a session."""
    timeout: int = SESSION_TIMEOUT
    max_retries: int = 2
    auto_close_on_complete: bool = True
    use_prompt_caching: bool = True
    model: str = "claude-sonnet-4-20250514"
    role: str = "dev"  # Default role
    tools: Set[str] = field(default_factory=lambda: {"read", "write", "bash", "git", "bd"})
    worktree: bool = True  # Use isolated git worktree


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class BeadSession:
    """Represents an active Claude session for a bead."""
    bead_id: str
    title: str
    description: str
    priority: int
    state: SessionState = SessionState.PENDING
    pid: Optional[int] = None
    created_at: datetime = field(default_factory=_utc_now)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    last_activity: datetime = field(default_factory=_utc_now)
    output_lines: int = 0
    error: Optional[str] = None
    config: SessionConfig = field(default_factory=SessionConfig)
    # Role-based fields (Issue #44: Agent Role Integration)
    role: str = "dev"  # Agent role (ceo, pm, cto, po, dev, research, marketing)
    tier: int = 3      # Agent tier (1=orchestrator, 2=supervisor, 3=worker)
    tools: Set[str] = field(default_factory=lambda: {"read", "write", "bash", "git", "bd"})
    persona_prompt: str = ""  # Loaded from .speckle/agents/{role}.md
    
    def to_dict(self) -> dict:
        return {
            "bead_id": self.bead_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "state": self.state.value,
            "pid": self.pid,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "last_activity": self.last_activity.isoformat(),
            "output_lines": self.output_lines,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            # Role-based fields
            "role": self.role,
            "tier": self.tier,
            "tools": list(self.tools),
        }
    
    @property
    def duration_seconds(self) -> float:
        """Get session duration in seconds."""
        if self.started_at:
            end = self.ended_at or datetime.now(timezone.utc)
            return (end - self.started_at).total_seconds()
        return 0
    
    @property
    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.state in (SessionState.SPAWNING, SessionState.RUNNING, SessionState.STUCK)


# === Role Management Functions ===

AGENTS_DIR = PROJECT_ROOT / ".speckle/agents"


def get_role_config(role: str) -> Dict[str, Any]:
    """Get configuration for a specific role."""
    role_lower = role.lower()
    if role_lower in ROLE_SESSION_CONFIG:
        return ROLE_SESSION_CONFIG[role_lower]
    # Default to DEV config
    return ROLE_SESSION_CONFIG["dev"]


def load_persona(role: str) -> str:
    """
    Load persona prompt from .speckle/agents/{role}.md
    
    Supports frontmatter format:
    ---
    role: dev
    tier: 3
    description: Implementation specialist
    tools: [read, write, bash, git]
    ---
    
    # Developer Agent
    You are a senior software developer...
    """
    role_lower = role.lower()
    persona_file = AGENTS_DIR / f"{role_lower}.md"
    
    if not persona_file.exists():
        # Return default persona based on role config
        config = get_role_config(role_lower)
        return f"""You are a {config.get('description', 'Speckle agent')}.

Your role: {role.upper()}
Tier: {config.get('tier', AgentTier.WORKER).value if isinstance(config.get('tier'), AgentTier) else config.get('tier', 3)}

Focus on your assigned task and use only the tools permitted for your role.
"""
    
    try:
        content = persona_file.read_text()
        
        # Parse frontmatter if present
        if content.startswith("---"):
            # Find end of frontmatter
            end_match = re.search(r'\n---\s*\n', content[3:])
            if end_match:
                # Return content after frontmatter
                return content[3 + end_match.end():].strip()
        
        return content.strip()
    except IOError:
        return ""


def parse_persona_frontmatter(role: str) -> Dict[str, Any]:
    """
    Parse frontmatter from persona file.
    
    Returns dict with role, tier, description, tools from frontmatter.
    """
    role_lower = role.lower()
    persona_file = AGENTS_DIR / f"{role_lower}.md"
    
    if not persona_file.exists():
        return {}
    
    try:
        content = persona_file.read_text()
        
        if not content.startswith("---"):
            return {}
        
        # Find frontmatter block
        end_match = re.search(r'\n---\s*\n', content[3:])
        if not end_match:
            return {}
        
        frontmatter = content[3:3 + end_match.start()]
        result = {}
        
        # Simple YAML-like parsing (key: value)
        for line in frontmatter.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Parse arrays [item1, item2]
                if value.startswith('[') and value.endswith(']'):
                    items = value[1:-1].split(',')
                    result[key] = [item.strip().strip('"\'') for item in items]
                # Parse numbers
                elif value.isdigit():
                    result[key] = int(value)
                # Strip quotes from strings
                else:
                    result[key] = value.strip('"\'')
        
        return result
    except IOError:
        return {}


def assign_worker_role(bead: Dict[str, Any]) -> str:
    """
    Determine which role should work on a bead based on intent.
    
    Analyzes bead labels and title to detect intent and assign appropriate role.
    """
    labels = [l.lower() for l in bead.get("labels", [])]
    title = bead.get("title", "").lower()
    description = bead.get("description", "").lower()
    
    # Check labels first (highest priority)
    for label in labels:
        if label in BEAD_INTENT_ROLE_MAPPING:
            return BEAD_INTENT_ROLE_MAPPING[label]
    
    # Check title and description keywords
    combined_text = f"{title} {description}"
    for keyword, role in BEAD_INTENT_ROLE_MAPPING.items():
        if keyword in combined_text:
            return role
    
    # Default to DEV for implementation work
    return "dev"


def detect_intent(text: str) -> str:
    """
    Detect the intent type from text.
    
    Returns: backend, design, marketing, roadmap, research, or mixed
    Based on opencode-agent-conversations detectIntent() logic.
    """
    text_lower = text.lower()
    
    # Intent keyword patterns
    intent_patterns = {
        "backend": ["api", "database", "backend", "server", "endpoint", "migration", "query"],
        "design": ["ui", "ux", "design", "frontend", "component", "style", "layout"],
        "marketing": ["docs", "documentation", "blog", "copy", "content", "readme"],
        "roadmap": ["plan", "milestone", "epic", "sprint", "schedule", "priority"],
        "research": ["research", "investigate", "analyze", "compare", "evaluate"],
    }
    
    intent_scores = {intent: 0 for intent in intent_patterns}
    
    for intent, keywords in intent_patterns.items():
        for keyword in keywords:
            if keyword in text_lower:
                intent_scores[intent] += 1
    
    # Find highest scoring intent
    max_score = max(intent_scores.values())
    if max_score == 0:
        return "mixed"
    
    # Check for tie (mixed)
    top_intents = [i for i, s in intent_scores.items() if s == max_score]
    if len(top_intents) > 1:
        return "mixed"
    
    return top_intents[0]


class BeadSessionManager:
    """
    Manages ephemeral Claude sessions for in-progress beads.
    
    Features:
    - Spawn session when bead goes to in_progress
    - Terminate session when bead is closed/blocked
    - Stream terminal output via WebSocket
    - Track session state and metrics
    """
    
    def __init__(self, config: Optional[SessionConfig] = None):
        self.config = config or SessionConfig()
        self.sessions: Dict[str, BeadSession] = {}
        self.lock = threading.Lock()
        self._status_callbacks: List[Callable] = []
        
        # Ensure directories exist
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load existing sessions
        self._load_sessions()
    
    def _load_sessions(self):
        """Load session state from disk."""
        if not SESSIONS_DIR.exists():
            return
            
        for session_dir in SESSIONS_DIR.iterdir():
            if session_dir.is_dir():
                session_file = session_dir / "session.json"
                if session_file.exists():
                    try:
                        with open(session_file) as f:
                            data = json.load(f)
                            session = self._session_from_dict(data)
                            
                            # Check if "running" sessions are actually still running
                            if session.state in (SessionState.RUNNING, SessionState.SPAWNING):
                                if session.pid and self._is_process_running(session.pid):
                                    # Still running
                                    pass
                                else:
                                    # Process exited, mark as completed
                                    session.state = SessionState.COMPLETED
                                    session.ended_at = datetime.now(timezone.utc)
                                    self._save_session(session)
                            
                            self.sessions[session.bead_id] = session
                    except (json.JSONDecodeError, IOError, KeyError) as e:
                        print(f"Warning: Could not load session from {session_file}: {e}")
    
    def _session_from_dict(self, data: Dict[str, Any]) -> BeadSession:
        """Create BeadSession from dict data."""
        # Parse tools - handle both list and set
        tools_data = data.get("tools", ["read", "write", "bash", "git", "bd"])
        tools = set(tools_data) if isinstance(tools_data, list) else tools_data
        
        return BeadSession(
            bead_id=data["bead_id"],
            title=data.get("title", "Untitled"),
            description=data.get("description", ""),
            priority=data.get("priority", 4),
            state=SessionState(data.get("state", "pending")),
            pid=data.get("pid"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else _utc_now(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            last_activity=datetime.fromisoformat(data["last_activity"]) if data.get("last_activity") else _utc_now(),
            output_lines=data.get("output_lines", 0),
            error=data.get("error"),
            # Role-based fields
            role=data.get("role", "dev"),
            tier=data.get("tier", 3),
            tools=tools,
        )
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is still running."""
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False
    
    def _save_session(self, session: BeadSession):
        """Save session state to disk."""
        session_dir = SESSIONS_DIR / session.bead_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        session_file = session_dir / "session.json"
        with open(session_file, "w") as f:
            json.dump(session.to_dict(), f, indent=2)
    
    def get_bead_details(self, bead_id: str) -> Optional[Dict[str, Any]]:
        """Fetch bead details using bd command."""
        try:
            result = subprocess.run(
                ["bd", "show", bead_id, "--json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                # bd show --json returns a list, get first item
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
                elif isinstance(data, dict):
                    return data
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass
        return None
    
    def get_progress_context(self) -> str:
        """Get learnings from progress.txt for context injection."""
        if PROGRESS_FILE.exists():
            try:
                content = PROGRESS_FILE.read_text()
                # Return last 50 lines to avoid context bloat
                lines = content.strip().split("\n")
                return "\n".join(lines[-50:])
            except IOError:
                pass
        return "No previous learnings recorded."
    
    def build_task_context(self, bead: Dict[str, Any], session: Optional[BeadSession] = None) -> str:
        """Build the task context to inject into the Claude session."""
        bead_id = bead.get("id", "unknown")
        title = bead.get("title", "Untitled")
        description = bead.get("description", "No description")
        priority = bead.get("priority", 4)
        labels = bead.get("labels", [])
        
        progress = self.get_progress_context()
        
        # Include persona if session has one
        persona_section = ""
        role_section = ""
        if session and session.persona_prompt:
            persona_section = f"""## Your Role

{session.persona_prompt}

"""
            role_section = f"""**Role:** {session.role.upper()} (Tier {session.tier})
**Permitted Tools:** {', '.join(sorted(session.tools))}
"""
        
        return f"""{persona_section}## Task Assignment

**Bead:** {bead_id}
**Title:** {title}
**Priority:** P{priority}
**Labels:** {', '.join(labels) if labels else 'None'}
{role_section}
### Description
{description}

### Previous Learnings
{progress}

### Definition of Done
1. Code compiles/runs without errors
2. Tests pass (if applicable)  
3. Changes committed to git with clear message
4. No secrets or credentials exposed
5. Update .speckle/progress.txt with learnings

### Instructions
1. Claim the task: `bd update {bead_id} --status in_progress`
2. Implement the solution step by step
3. Commit your changes with: `git add . && git commit -m "type(scope): description"`
4. When complete: `bd close {bead_id} --reason "Summary of what was done"`

### Important
- Focus ONLY on this task
- Stay within your role's permitted tools
- Ask for clarification if requirements are unclear
- If stuck, update status: `bd update {bead_id} --status blocked --reason "Why blocked"`
"""
    
    def spawn_session(self, bead_id: str, role: Optional[str] = None) -> Optional[BeadSession]:
        """
        Spawn a new Claude session for a bead.
        
        Args:
            bead_id: The bead identifier
            role: Agent role (ceo, pm, cto, po, dev, research, marketing).
                  If None, role is auto-assigned based on bead intent.
        
        Returns the session object or None if spawn failed.
        """
        with self.lock:
            # Check if session already exists
            if bead_id in self.sessions and self.sessions[bead_id].is_active:
                return self.sessions[bead_id]
        
        # Get bead details
        bead = self.get_bead_details(bead_id)
        if not bead:
            print(f"Error: Could not fetch bead details for {bead_id}")
            return None
        
        # Determine role (auto-assign if not specified)
        if role is None:
            role = assign_worker_role(bead)
        role = role.lower()
        
        # Get role configuration
        role_config = get_role_config(role)
        tier_value = role_config.get("tier", AgentTier.WORKER)
        tier = tier_value.value if isinstance(tier_value, AgentTier) else tier_value
        tools = role_config.get("tools", {"read", "write", "bash", "git", "bd"})
        timeout = role_config.get("timeout", SESSION_TIMEOUT)
        max_concurrent = role_config.get("max_concurrent", MAX_CONCURRENT_SESSIONS)
        
        with self.lock:
            # Check concurrent session limit for this role
            active_role_count = sum(1 for s in self.sessions.values() 
                                    if s.is_active and s.role == role)
            if active_role_count >= max_concurrent:
                print(f"Warning: Max concurrent {role.upper()} sessions ({max_concurrent}) reached")
                return None
            
            # Also check global limit
            active_count = sum(1 for s in self.sessions.values() if s.is_active)
            if active_count >= MAX_CONCURRENT_SESSIONS:
                print(f"Warning: Max concurrent sessions ({MAX_CONCURRENT_SESSIONS}) reached")
                return None
        
        # Load persona prompt
        persona_prompt = load_persona(role)
        
        # Create session config with role settings
        session_config = SessionConfig(
            timeout=timeout,
            max_retries=self.config.max_retries,
            auto_close_on_complete=self.config.auto_close_on_complete,
            use_prompt_caching=self.config.use_prompt_caching,
            model=self.config.model,
            role=role,
            tools=tools,
            worktree=role_config.get("worktree", False),
        )
        
        # Create session
        session = BeadSession(
            bead_id=bead_id,
            title=bead.get("title", "Untitled"),
            description=bead.get("description", ""),
            priority=bead.get("priority", 4),
            state=SessionState.SPAWNING,
            config=session_config,
            role=role,
            tier=tier,
            tools=tools,
            persona_prompt=persona_prompt,
        )
        
        with self.lock:
            self.sessions[bead_id] = session
        
        self._save_session(session)
        self._notify_status_change(session)
        
        # Build task context with role persona
        context = self.build_task_context(bead, session)
        
        # Save context for reference
        context_file = SESSIONS_DIR / bead_id / "context.md"
        context_file.write_text(context)
        
        # Start the Claude session
        try:
            self._start_claude_session(session, context)
            return session
        except Exception as e:
            session.state = SessionState.FAILED
            session.error = str(e)
            session.ended_at = datetime.now(timezone.utc)
            self._save_session(session)
            self._notify_status_change(session)
            return None
    
    def _start_claude_session(self, session: BeadSession, context: str):
        """Start the actual Claude CLI process."""
        session_dir = SESSIONS_DIR / session.bead_id
        output_log = session_dir / "output.log"
        
        # Build Claude command
        # Option 1: Use claude CLI if available
        claude_cmd = self._find_claude_cli()
        
        if claude_cmd:
            cmd = [
                claude_cmd,
                "--print",  # Non-interactive mode
                "-p", context,  # Pass context as prompt
            ]
        else:
            # Option 2: Fallback to a simple bash session for testing
            cmd = ["bash", "-c", f"echo 'Task: {session.title}'; echo 'Waiting for claude CLI...'; sleep 5"]
        
        # Use terminal server if available
        if HAS_TERMINAL_SERVER:
            terminal_session = spawn_with_terminal(session.bead_id, cmd)
            session.pid = terminal_session.pid
        else:
            # Fallback: run directly with output capture
            with open(output_log, "w") as log_file:
                process = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    cwd=os.getcwd(),
                    env={**os.environ, "SPECKLE_BEAD_ID": session.bead_id},
                )
                session.pid = process.pid
        
        session.state = SessionState.RUNNING
        session.started_at = datetime.now(timezone.utc)
        self._save_session(session)
        self._notify_status_change(session)
        
        # Start monitoring thread
        threading.Thread(
            target=self._monitor_session,
            args=(session.bead_id,),
            daemon=True,
            name=f"session-monitor-{session.bead_id}"
        ).start()
    
    def _find_claude_cli(self) -> Optional[str]:
        """Find the Claude CLI executable."""
        # Check common locations
        candidates = [
            "claude",
            os.path.expanduser("~/.claude/claude"),
            "/usr/local/bin/claude",
        ]
        
        for candidate in candidates:
            try:
                result = subprocess.run(
                    [candidate, "--version"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return candidate
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        return None
    
    def _monitor_session(self, bead_id: str):
        """Monitor a session for completion or timeout."""
        session = self.sessions.get(bead_id)
        if not session:
            return
        
        start_time = time.time()
        last_lines = 0
        stuck_count = 0
        
        while session.is_active:
            time.sleep(HEARTBEAT_INTERVAL)
            
            # Check if process is still running
            if session.pid:
                try:
                    os.kill(session.pid, 0)  # Check if process exists
                except ProcessLookupError:
                    # Process ended
                    session.state = SessionState.COMPLETED
                    session.ended_at = datetime.now(timezone.utc)
                    self._save_session(session)
                    self._notify_status_change(session)
                    
                    # Auto-close bead if configured
                    if session.config.auto_close_on_complete:
                        self._auto_close_bead(bead_id)
                    return
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > session.config.timeout:
                session.state = SessionState.FAILED
                session.error = f"Session timeout after {int(elapsed)}s"
                session.ended_at = datetime.now(timezone.utc)
                self.terminate_session(bead_id)
                return
            
            # Check for stuck session (no output for a while)
            output_log = SESSIONS_DIR / bead_id / "output.log"
            if output_log.exists():
                current_lines = sum(1 for _ in open(output_log))
                if current_lines == last_lines:
                    stuck_count += 1
                    if stuck_count > 12:  # 1 minute of no output
                        session.state = SessionState.STUCK
                        self._save_session(session)
                        self._notify_status_change(session)
                else:
                    stuck_count = 0
                    session.state = SessionState.RUNNING
                    session.last_activity = datetime.now(timezone.utc)
                last_lines = current_lines
                session.output_lines = current_lines
    
    def _auto_close_bead(self, bead_id: str):
        """Auto-close bead when session completes successfully."""
        try:
            subprocess.run(
                ["bd", "close", bead_id, "--reason", "Session completed automatically"],
                capture_output=True,
                timeout=10
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    def terminate_session(self, bead_id: str, force: bool = False) -> bool:
        """Terminate a running session."""
        session = self.sessions.get(bead_id)
        if not session:
            return False
        
        if not session.is_active:
            return True
        
        if session.pid:
            try:
                # Try graceful termination first
                os.kill(session.pid, signal.SIGTERM)
                
                if force:
                    time.sleep(1)
                    try:
                        os.kill(session.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            except ProcessLookupError:
                pass
        
        # Also terminate via terminal server if available
        if HAS_TERMINAL_SERVER:
            terminal_manager.terminate_session(bead_id)
        
        session.state = SessionState.TERMINATED
        session.ended_at = datetime.now(timezone.utc)
        self._save_session(session)
        self._notify_status_change(session)
        
        return True
    
    def get_session(self, bead_id: str) -> Optional[BeadSession]:
        """Get session by bead ID."""
        return self.sessions.get(bead_id)
    
    def list_sessions(self, active_only: bool = False) -> List[BeadSession]:
        """List all sessions."""
        sessions = list(self.sessions.values())
        if active_only:
            sessions = [s for s in sessions if s.is_active]
        return sorted(sessions, key=lambda s: s.created_at, reverse=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        sessions = list(self.sessions.values())
        active = [s for s in sessions if s.is_active]
        completed = [s for s in sessions if s.state == SessionState.COMPLETED]
        failed = [s for s in sessions if s.state == SessionState.FAILED]
        
        return {
            "total": len(sessions),
            "active": len(active),
            "completed": len(completed),
            "failed": len(failed),
            "avg_duration": sum(s.duration_seconds for s in completed) / len(completed) if completed else 0,
        }
    
    def on_status_change(self, callback: Callable[[BeadSession], None]):
        """Register a callback for session status changes."""
        self._status_callbacks.append(callback)
    
    def _notify_status_change(self, session: BeadSession):
        """Notify all registered callbacks of status change."""
        for callback in self._status_callbacks:
            try:
                callback(session)
            except Exception as e:
                print(f"Error in status callback: {e}")


# Global session manager instance
session_manager = BeadSessionManager()


# === CLI Interface ===

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Speckle Session Manager - Ephemeral Claude sessions for beads"
    )
    subparsers = parser.add_subparsers(dest="command")
    
    # Spawn command
    spawn_parser = subparsers.add_parser("spawn", help="Spawn session for bead")
    spawn_parser.add_argument("bead_id", help="Bead ID")
    spawn_parser.add_argument("--role", "-r", 
                              choices=["ceo", "pm", "cto", "po", "dev", "research", "marketing"],
                              help="Agent role (auto-detected from bead if not specified)")
    
    # Terminate command
    term_parser = subparsers.add_parser("terminate", help="Terminate session")
    term_parser.add_argument("bead_id", help="Bead ID")
    term_parser.add_argument("--force", action="store_true", help="Force kill")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List sessions")
    list_parser.add_argument("--active", action="store_true", help="Active only")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show session status")
    status_parser.add_argument("bead_id", help="Bead ID")
    
    # Stats command
    subparsers.add_parser("stats", help="Show session statistics")
    
    # Roles command
    subparsers.add_parser("roles", help="List available agent roles")
    
    args = parser.parse_args()
    
    if args.command == "spawn":
        session = session_manager.spawn_session(args.bead_id, role=args.role)
        if session:
            print(json.dumps(session.to_dict(), indent=2))
        else:
            print(f"Failed to spawn session for {args.bead_id}")
            sys.exit(1)
    
    elif args.command == "terminate":
        if session_manager.terminate_session(args.bead_id, args.force):
            print(f"✓ Terminated session: {args.bead_id}")
        else:
            print(f"✗ No session found: {args.bead_id}")
            sys.exit(1)
    
    elif args.command == "list":
        sessions = session_manager.list_sessions(args.active)
        for session in sessions:
            status_icon = {
                SessionState.RUNNING: "🟢",
                SessionState.SPAWNING: "🟡",
                SessionState.STUCK: "🟠",
                SessionState.COMPLETED: "✅",
                SessionState.FAILED: "❌",
                SessionState.TERMINATED: "⏹️",
            }.get(session.state, "⚪")
            
            role_badge = f"[{session.role.upper()}]" if hasattr(session, 'role') else ""
            print(f"{status_icon} {role_badge:12} {session.bead_id}: {session.title[:35]} ({session.state.value})")
    
    elif args.command == "status":
        session = session_manager.get_session(args.bead_id)
        if session:
            print(json.dumps(session.to_dict(), indent=2))
        else:
            print(f"No session found: {args.bead_id}")
            sys.exit(1)
    
    elif args.command == "stats":
        stats = session_manager.get_stats()
        print(json.dumps(stats, indent=2))
    
    elif args.command == "roles":
        print("\n📋 Available Agent Roles:\n")
        tier_names = {1: "Orchestrator", 2: "Supervisor", 3: "Worker"}
        for role, config in sorted(ROLE_SESSION_CONFIG.items(), 
                                   key=lambda x: x[1]["tier"].value if isinstance(x[1]["tier"], AgentTier) else x[1]["tier"]):
            tier = config["tier"]
            tier_val = tier.value if isinstance(tier, AgentTier) else tier
            tier_name = tier_names.get(tier_val, "Unknown")
            tools = ", ".join(sorted(config["tools"]))
            timeout_mins = config["timeout"] // 60
            ephemeral = "Yes" if config["ephemeral"] else "No"
            worktree = "Yes" if config.get("worktree") else "No"
            
            print(f"  {role.upper():12} Tier {tier_val} ({tier_name})")
            print(f"               {config['description']}")
            print(f"               Timeout: {timeout_mins}min | Ephemeral: {ephemeral} | Worktree: {worktree}")
            print(f"               Tools: {tools}")
            print()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
