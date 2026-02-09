#!/usr/bin/env python3
"""
Speckle Kanban Board Server
Lightweight visualization of beads issues with real-time terminal mirroring.

Phase 1: Foundation (T001-T005)
Phase 2: UI Polish (T006-T010)
Phase 3: Terminal Mirroring (WebSocket + xterm.js)
"""

import http.server
import json
import subprocess
import argparse
import urllib.parse
import webbrowser
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add scripts directory to path for imports
SCRIPTS_DIR = Path(__file__).parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Try to import session manager
try:
    from session_manager import session_manager, SessionState, BeadSession
    HAS_SESSION_MANAGER = True
except ImportError:
    HAS_SESSION_MANAGER = False
    session_manager = None
    SessionState = None

# === Configuration ===
DEFAULT_PORT = 8420
DEFAULT_REFRESH = 5
MAX_CLOSED = 15
TERMINAL_WS_PORT = 8421  # WebSocket port for terminal server
TERMINAL_DIR = Path(".speckle/terminals")
SESSIONS_DIR = Path(".speckle/sessions")


# === Terminal Session Detection ===
def get_active_terminals() -> Dict[str, Dict[str, Any]]:
    """Get active terminal sessions from .speckle/terminals/*.json"""
    terminals = {}
    if TERMINAL_DIR.exists():
        for json_file in TERMINAL_DIR.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    bead_id = data.get("bead_id", json_file.stem)
                    terminals[bead_id] = data
            except (json.JSONDecodeError, IOError):
                pass
    return terminals


# === Session Management ===
def get_sessions_info() -> Dict[str, Dict[str, Any]]:
    """Get session info from session manager or session files."""
    sessions = {}
    
    # Try session manager first
    if HAS_SESSION_MANAGER and session_manager:
        for session in session_manager.list_sessions():
            sessions[session.bead_id] = {
                "state": session.state.value,
                "pid": session.pid,
                "duration": session.duration_seconds,
                "output_lines": session.output_lines,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "is_active": session.is_active,
            }
    else:
        # Fallback: read from session files
        if SESSIONS_DIR.exists():
            for session_dir in SESSIONS_DIR.iterdir():
                if session_dir.is_dir():
                    session_file = session_dir / "session.json"
                    if session_file.exists():
                        try:
                            with open(session_file) as f:
                                data = json.load(f)
                                bead_id = data.get("bead_id", session_dir.name)
                                sessions[bead_id] = {
                                    "state": data.get("state", "unknown"),
                                    "pid": data.get("pid"),
                                    "duration": data.get("duration_seconds", 0),
                                    "output_lines": data.get("output_lines", 0),
                                    "started_at": data.get("started_at"),
                                    "is_active": data.get("state") in ("running", "spawning", "stuck"),
                                }
                        except (json.JSONDecodeError, IOError):
                            pass
    
    return sessions


def spawn_session(bead_id: str) -> Dict[str, Any]:
    """Spawn a new session for a bead."""
    if not HAS_SESSION_MANAGER or not session_manager:
        return {"error": "Session manager not available"}
    
    session = session_manager.spawn_session(bead_id)
    if session:
        return {
            "success": True,
            "bead_id": bead_id,
            "state": session.state.value,
            "pid": session.pid,
        }
    return {"error": f"Failed to spawn session for {bead_id}"}


def terminate_session(bead_id: str) -> Dict[str, Any]:
    """Terminate a session for a bead."""
    if not HAS_SESSION_MANAGER or not session_manager:
        return {"error": "Session manager not available"}
    
    if session_manager.terminate_session(bead_id):
        return {"success": True, "bead_id": bead_id}
    return {"error": f"Failed to terminate session for {bead_id}"}


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        mins = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds / 3600)
        mins = int((seconds % 3600) / 60)
        return f"{hours}h {mins}m"


# === T002: Beads JSON Fetching ===
def get_issues(label_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch issues from beads via bd list --json."""
    cmd = ['bd', 'list', '--all', '--json', '--limit', '0']
    if label_filter:
        cmd.extend(['--label', label_filter])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return []


# === T005: Group Issues by Status ===
def group_by_status(issues: List[Dict[str, Any]], max_closed: int = MAX_CLOSED) -> Dict[str, List]:
    """Group issues into kanban columns based on status."""
    columns = {
        'open': [],
        'in_progress': [],
        'blocked': [],
        'closed': []
    }
    
    for issue in issues:
        status = issue.get('status', 'open')
        if status == 'deferred':
            status = 'blocked'
        if status in columns:
            columns[status].append(issue)
    
    for status in ['open', 'in_progress', 'blocked']:
        columns[status].sort(key=lambda x: (x.get('priority', 4), x.get('created_at', '')))
    
    columns['closed'].sort(key=lambda x: x.get('closed_at', ''), reverse=True)
    columns['closed'] = columns['closed'][:max_closed]
    
    return columns


# === T008: Time Ago Formatting ===
def time_ago(timestamp: str) -> str:
    """Convert timestamp to human-readable 'X ago' format."""
    if not timestamp:
        return ''
    
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = now - dt
        
        seconds = delta.total_seconds()
        if seconds < 60:
            return 'just now'
        elif seconds < 3600:
            mins = int(seconds / 60)
            return f'{mins}m ago'
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f'{hours}h ago'
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f'{days}d ago'
        else:
            weeks = int(seconds / 604800)
            return f'{weeks}w ago'
    except (ValueError, TypeError):
        return ''


# === T003 + T006 + T007 + T009 + T010: Enhanced HTML Template ===
# === Updated with T001-T007: System Color Mode Support ===
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="{refresh}">
    <title>Speckle Board</title>
    <style>
        /* === T001: Light theme (default) === */
        :root {{
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --header-gradient: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            
            /* Column backgrounds */
            --backlog: #f1f5f9;
            --progress: #dbeafe;
            --blocked: #fee2e2;
            --done: #d1fae5;
            
            /* Priority colors */
            --p0: #dc2626;
            --p1: #ea580c;
            --p2: #f59e0b;
            --p3: #10b981;
            --p4: #6b7280;
            
            /* Shadows */
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.1);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
            --shadow-header: 0 2px 4px rgba(0,0,0,0.1);
            
            /* Badge backgrounds (light mode) */
            --badge-p0-bg: #fef2f2;
            --badge-p0-text: #dc2626;
            --badge-p2-bg: #fffbeb;
            --badge-p2-text: #b45309;
            --badge-p3-bg: #f0fdf4;
            --badge-p3-text: #15803d;
            --type-bg: #f1f5f9;
            --type-bug-bg: #fef2f2;
            --type-bug-text: #b91c1c;
            --type-feature-bg: #f5f3ff;
            --type-feature-text: #6d28d9;
            --type-epic-bg: #fff7ed;
            --type-epic-text: #c2410c;
            --label-bg: #e0e7ff;
            --label-text: #3730a3;
            
            /* Column header border */
            --column-border: rgba(0,0,0,0.1);
        }}
        
        /* === T001: Dark theme via data attribute === */
        /* Midnight black theme - true dark mode */
        [data-theme="dark"] {{
            --bg: #000000;
            --card-bg: #0a0a0a;
            --text: #f1f5f9;
            --text-muted: #a1a1aa;
            --border: #27272a;
            --header-gradient: linear-gradient(135deg, #3730a3 0%, #581c87 100%);
            
            /* Column backgrounds - near black with subtle color hints */
            --backlog: #0a0a0a;
            --progress: #0a1628;
            --blocked: #1a0a0a;
            --done: #0a1a0a;
            
            /* Shadows - subtle glow effect */
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.5);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.6);
            --shadow-header: 0 2px 8px rgba(0,0,0,0.5);
            
            /* Badge backgrounds (dark mode - vibrant on black) */
            --badge-p0-bg: #2a0a0a;
            --badge-p0-text: #f87171;
            --badge-p2-bg: #2a1a03;
            --badge-p2-text: #fbbf24;
            --badge-p3-bg: #052e16;
            --badge-p3-text: #4ade80;
            --type-bg: #18181b;
            --type-bug-bg: #2a0a0a;
            --type-bug-text: #f87171;
            --type-feature-bg: #1e1033;
            --type-feature-text: #a78bfa;
            --type-epic-bg: #2a1407;
            --type-epic-text: #fb923c;
            --label-bg: #1e1b4b;
            --label-text: #a5b4fc;
            
            /* Column header border */
            --column-border: rgba(255,255,255,0.1);
        }}
        
        /* === T002: System preference detection (when no explicit choice) === */
        /* Midnight black theme - matches [data-theme="dark"] */
        @media (prefers-color-scheme: dark) {{
            :root:not([data-theme]) {{
                --bg: #000000;
                --card-bg: #0a0a0a;
                --text: #f1f5f9;
                --text-muted: #a1a1aa;
                --border: #27272a;
                --header-gradient: linear-gradient(135deg, #3730a3 0%, #581c87 100%);
                --backlog: #0a0a0a;
                --progress: #0a1628;
                --blocked: #1a0a0a;
                --done: #0a1a0a;
                --shadow-sm: 0 1px 3px rgba(0,0,0,0.5);
                --shadow-md: 0 4px 6px rgba(0,0,0,0.6);
                --shadow-header: 0 2px 8px rgba(0,0,0,0.5);
                --badge-p0-bg: #2a0a0a;
                --badge-p0-text: #f87171;
                --badge-p2-bg: #2a1a03;
                --badge-p2-text: #fbbf24;
                --badge-p3-bg: #052e16;
                --badge-p3-text: #4ade80;
                --type-bg: #18181b;
                --type-bug-bg: #2a0a0a;
                --type-bug-text: #f87171;
                --type-feature-bg: #1e1033;
                --type-feature-text: #a78bfa;
                --type-epic-bg: #2a1407;
                --type-epic-text: #fb923c;
                --label-bg: #1e1b4b;
                --label-text: #a5b4fc;
                --column-border: rgba(255,255,255,0.08);
            }}
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        /* === T006: Smooth transitions === */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            transition: background-color 0.2s ease, color 0.2s ease;
        }}
        
        header {{
            background: transparent;
            color: var(--text);
            padding: 1rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
        }}
        
        header h1 {{
            font-size: 1.25rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .controls {{
            display: flex;
            align-items: center;
            gap: 1rem;
            font-size: 0.875rem;
        }}
        
        /* === T004: Theme toggle button === */
        .theme-toggle {{
            background: var(--column-border);
            border: none;
            font-size: 1.1rem;
            cursor: pointer;
            padding: 0.25rem 0.5rem;
            border-radius: 0.375rem;
            transition: background 0.2s;
            line-height: 1;
        }}
        
        .theme-toggle:hover {{
            background: var(--border);
        }}
        
        .refresh-badge {{
            background: var(--column-border);
            color: var(--text-muted);
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.75rem;
        }}
        
        .filter-select {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            cursor: pointer;
        }}
        
        .filter-select option {{
            background: var(--card-bg);
            color: var(--text);
        }}
        
        .board {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            padding: 1rem;
            max-width: 1600px;
            margin: 0 auto;
            min-height: calc(100vh - 120px);
        }}
        
        /* Responsive layout */
        @media (max-width: 1024px) {{
            .board {{ grid-template-columns: repeat(2, 1fr); }}
        }}
        
        @media (max-width: 640px) {{
            .board {{ grid-template-columns: 1fr; }}
        }}
        
        .column {{
            background: var(--backlog);
            border-radius: 0.5rem;
            padding: 0.75rem;
            display: flex;
            flex-direction: column;
            min-height: 200px;
            transition: background-color 0.2s ease;
        }}
        
        .column.in_progress {{ background: var(--progress); }}
        .column.blocked {{ background: var(--blocked); }}
        .column.closed {{ background: var(--done); }}
        
        .column-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--column-border);
        }}
        
        .column-title {{
            font-weight: 600;
            font-size: 0.875rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .column-count {{
            background: var(--column-border);
            padding: 0.125rem 0.5rem;
            border-radius: 1rem;
            font-size: 0.75rem;
        }}
        
        .cards {{
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}
        
        /* Priority-colored cards */
        .card {{
            background: var(--card-bg);
            border-radius: 0.375rem;
            padding: 0.75rem;
            box-shadow: var(--shadow-sm);
            border-left: 3px solid var(--p3);
            transition: transform 0.1s, box-shadow 0.1s, background-color 0.2s ease;
        }}
        
        .card:hover {{
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }}
        
        .card.p0, .card.p1 {{ border-left-color: var(--p0); }}
        .card.p2 {{ border-left-color: var(--p2); }}
        .card.p3 {{ border-left-color: var(--p3); }}
        .card.p4 {{ border-left-color: var(--p4); }}
        
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 0.5rem;
        }}
        
        .card-id {{
            font-family: monospace;
            font-size: 0.7rem;
            color: var(--text-muted);
        }}
        
        .priority-badge {{
            font-size: 0.65rem;
            padding: 0.125rem 0.375rem;
            border-radius: 0.25rem;
            font-weight: 600;
            transition: background-color 0.2s ease, color 0.2s ease;
        }}
        
        .priority-badge.p0, .priority-badge.p1 {{
            background: var(--badge-p0-bg);
            color: var(--badge-p0-text);
        }}
        .priority-badge.p2 {{
            background: var(--badge-p2-bg);
            color: var(--badge-p2-text);
        }}
        .priority-badge.p3, .priority-badge.p4 {{
            background: var(--badge-p3-bg);
            color: var(--badge-p3-text);
        }}
        
        .card-title {{
            font-size: 0.8125rem;
            font-weight: 500;
            line-height: 1.4;
            margin-bottom: 0.5rem;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        
        .card-meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.7rem;
            color: var(--text-muted);
        }}
        
        /* Type badges */
        .type-badge {{
            background: var(--type-bg);
            padding: 0.125rem 0.375rem;
            border-radius: 0.25rem;
            transition: background-color 0.2s ease, color 0.2s ease;
        }}
        
        .type-badge.bug {{ background: var(--type-bug-bg); color: var(--type-bug-text); }}
        .type-badge.feature {{ background: var(--type-feature-bg); color: var(--type-feature-text); }}
        .type-badge.epic {{ background: var(--type-epic-bg); color: var(--type-epic-text); }}
        
        /* Labels */
        .labels {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.25rem;
            margin-top: 0.5rem;
        }}
        
        .label {{
            background: var(--label-bg);
            color: var(--label-text);
            font-size: 0.625rem;
            padding: 0.125rem 0.375rem;
            border-radius: 0.25rem;
            transition: background-color 0.2s ease, color 0.2s ease;
        }}
        
        .empty {{
            color: var(--text-muted);
            text-align: center;
            padding: 2rem;
            font-size: 0.875rem;
        }}
        
        /* === T020-T024: GitHub Integration Styles === */
        .card-actions {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .github-link {{
            color: var(--text-muted);
            text-decoration: none;
            display: flex;
            align-items: center;
            transition: color 0.2s ease;
        }}
        
        .github-link:hover {{
            color: var(--text);
        }}
        
        .github-icon {{
            width: 14px;
            height: 14px;
        }}
        
        footer {{
            text-align: center;
            padding: 1rem;
            color: var(--text-muted);
            font-size: 0.75rem;
            transition: color 0.2s ease;
        }}
        
        /* === Terminal Mirroring Styles === */
        .terminal-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            font-size: 0.65rem;
            padding: 0.125rem 0.375rem;
            border-radius: 0.25rem;
            background: var(--progress);
            color: var(--text);
            cursor: pointer;
            transition: background 0.2s;
        }}
        
        .terminal-indicator:hover {{
            background: var(--border);
        }}
        
        .terminal-indicator .pulse {{
            width: 6px;
            height: 6px;
            background: #22c55e;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        .terminal-drawer {{
            display: none;
            margin-top: 0.75rem;
            border-top: 1px solid var(--border);
            padding-top: 0.75rem;
        }}
        
        .terminal-drawer.open {{
            display: block;
        }}
        
        .terminal-container {{
            background: #000;
            border-radius: 0.375rem;
            padding: 0.5rem;
            height: 300px;
            overflow: hidden;
            position: relative;
        }}
        
        .terminal-container .xterm {{
            height: 100%;
        }}
        
        .terminal-controls {{
            display: flex;
            gap: 0.5rem;
            margin-top: 0.5rem;
            flex-wrap: wrap;
        }}
        
        .terminal-btn {{
            font-size: 0.7rem;
            padding: 0.25rem 0.5rem;
            border: 1px solid var(--border);
            background: var(--card-bg);
            color: var(--text);
            border-radius: 0.25rem;
            cursor: pointer;
            transition: background 0.2s, border-color 0.2s;
        }}
        
        .terminal-btn:hover {{
            background: var(--border);
        }}
        
        .terminal-btn.danger {{
            border-color: var(--p0);
            color: var(--p0);
        }}
        
        .terminal-btn.danger:hover {{
            background: var(--badge-p0-bg);
        }}
        
        .terminal-status {{
            font-size: 0.65rem;
            color: var(--text-muted);
            margin-left: auto;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }}
        
        .terminal-status.connected {{
            color: #22c55e;
        }}
        
        .terminal-status.disconnected {{
            color: var(--p0);
        }}
        
        /* === Session Status Styles === */
        .session-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            font-size: 0.65rem;
            padding: 0.125rem 0.375rem;
            border-radius: 0.25rem;
            transition: background 0.2s;
        }}
        
        .session-indicator.running {{
            background: #052e16;
            color: #4ade80;
        }}
        
        .session-indicator.stuck {{
            background: #2a1a03;
            color: #fbbf24;
        }}
        
        .session-indicator.spawning {{
            background: #0a1628;
            color: #60a5fa;
        }}
        
        .session-indicator.completed {{
            background: var(--badge-p3-bg);
            color: var(--badge-p3-text);
        }}
        
        .session-indicator.failed {{
            background: var(--badge-p0-bg);
            color: var(--badge-p0-text);
        }}
        
        .session-duration {{
            font-family: monospace;
            font-size: 0.65rem;
            color: var(--text-muted);
            margin-left: 0.25rem;
        }}
        
        .session-actions {{
            display: flex;
            gap: 0.375rem;
            margin-top: 0.5rem;
            flex-wrap: wrap;
        }}
        
        .session-btn {{
            font-size: 0.65rem;
            padding: 0.25rem 0.5rem;
            border: 1px solid var(--border);
            background: var(--card-bg);
            color: var(--text);
            border-radius: 0.25rem;
            cursor: pointer;
            transition: background 0.2s, border-color 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
        }}
        
        .session-btn:hover {{
            background: var(--border);
        }}
        
        .session-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        
        .session-btn.primary {{
            background: #3b82f6;
            border-color: #3b82f6;
            color: white;
        }}
        
        .session-btn.primary:hover {{
            background: #2563eb;
        }}
        
        .session-btn.danger {{
            border-color: var(--p0);
            color: var(--p0);
        }}
        
        .session-btn.danger:hover {{
            background: var(--badge-p0-bg);
        }}
        
        .session-info {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-top: 0.5rem;
            padding-top: 0.5rem;
            border-top: 1px dashed var(--border);
        }}
        
        /* Modal overlay for full-screen terminal */
        .terminal-modal {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.9);
            z-index: 1000;
            padding: 1rem;
        }}
        
        .terminal-modal.open {{
            display: flex;
            flex-direction: column;
        }}
        
        .terminal-modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem;
            color: #fff;
            margin-bottom: 0.5rem;
        }}
        
        .terminal-modal-content {{
            flex: 1;
            background: #000;
            border-radius: 0.5rem;
            overflow: hidden;
        }}
        
        .terminal-modal .xterm {{
            height: 100%;
        }}
    </style>
    
    <!-- xterm.js from CDN -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css">
    <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xterm-addon-web-links@0.9.0/lib/xterm-addon-web-links.min.js"></script>
    <!-- === T003: ThemeController - runs before body to prevent flash === -->
    <script>
        const ThemeController = {{
            STORAGE_KEY: 'speckle-theme',
            
            init() {{
                // Apply saved theme immediately (before render)
                const saved = localStorage.getItem(this.STORAGE_KEY);
                if (saved && saved !== 'system') {{
                    document.documentElement.setAttribute('data-theme', saved);
                }}
            }},
            
            apply(theme) {{
                if (theme === 'system') {{
                    document.documentElement.removeAttribute('data-theme');
                    localStorage.removeItem(this.STORAGE_KEY);
                }} else {{
                    document.documentElement.setAttribute('data-theme', theme);
                    localStorage.setItem(this.STORAGE_KEY, theme);
                }}
                this.updateToggleUI();
            }},
            
            toggle() {{
                const current = this.getCurrent();
                const next = current === 'dark' ? 'light' : 'dark';
                this.apply(next);
            }},
            
            getCurrent() {{
                const explicit = document.documentElement.getAttribute('data-theme');
                if (explicit) return explicit;
                return window.matchMedia('(prefers-color-scheme: dark)').matches 
                    ? 'dark' : 'light';
            }},
            
            updateToggleUI() {{
                const btn = document.querySelector('.theme-toggle');
                if (btn) {{
                    const isDark = this.getCurrent() === 'dark';
                    btn.textContent = isDark ? '☀️' : '🌙';
                    btn.title = isDark ? 'Switch to light mode' : 'Switch to dark mode';
                }}
            }}
        }};
        
        // Initialize immediately to prevent flash
        ThemeController.init();
    </script>
</head>
<body>
    <header>
        <h1>🔮 Speckle Board</h1>
        <div class="controls">
            <button class="theme-toggle" onclick="ThemeController.toggle()" title="Toggle theme">🌙</button>
            {filter_html}
            <span class="refresh-badge">⟳ {refresh}s</span>
        </div>
    </header>
    
    <main class="board">
        {columns_html}
    </main>
    
    <footer>
        {issue_count} issues • Last updated: {timestamp}
    </footer>
    
    <!-- Full-screen terminal modal -->
    <div id="terminal-modal" class="terminal-modal">
        <div class="terminal-modal-header">
            <span id="modal-title">Terminal: <span id="modal-bead-id"></span></span>
            <div style="display: flex; gap: 0.5rem;">
                <button class="terminal-btn" onclick="TerminalController.sendSignal(TerminalController.modalBeadId, 'SIGINT')">Send Ctrl+C</button>
                <button class="terminal-btn danger" onclick="TerminalController.terminate(TerminalController.modalBeadId)">Terminate</button>
                <button class="terminal-btn" onclick="TerminalController.closeModal()">Close (Esc)</button>
            </div>
        </div>
        <div class="terminal-modal-content" id="modal-terminal-container"></div>
    </div>
    
    <script>
        // === Session Controller ===
        const SessionController = {{
            async spawn(beadId) {{
                const btn = document.querySelector(`#spawn-btn-${{beadId}}`);
                if (btn) {{
                    btn.disabled = true;
                    btn.textContent = 'Starting...';
                }}
                
                try {{
                    const response = await fetch(`/api/sessions/${{beadId}}/spawn`, {{
                        method: 'POST'
                    }});
                    const data = await response.json();
                    
                    if (data.success) {{
                        // Reload to show updated state
                        window.location.reload();
                    }} else {{
                        alert(data.error || 'Failed to start session');
                        if (btn) {{
                            btn.disabled = false;
                            btn.textContent = '▶ Start Session';
                        }}
                    }}
                }} catch (e) {{
                    alert('Error starting session: ' + e.message);
                    if (btn) {{
                        btn.disabled = false;
                        btn.textContent = '▶ Start Session';
                    }}
                }}
            }},
            
            async terminate(beadId) {{
                if (!confirm(`Stop session for ${{beadId}}?`)) return;
                
                try {{
                    const response = await fetch(`/api/sessions/${{beadId}}/terminate`, {{
                        method: 'POST'
                    }});
                    const data = await response.json();
                    
                    if (data.success) {{
                        window.location.reload();
                    }} else {{
                        alert(data.error || 'Failed to stop session');
                    }}
                }} catch (e) {{
                    alert('Error stopping session: ' + e.message);
                }}
            }},
            
            updateDurations() {{
                document.querySelectorAll('[data-session-started]').forEach(el => {{
                    const started = new Date(el.dataset.sessionStarted);
                    const elapsed = (Date.now() - started.getTime()) / 1000;
                    el.textContent = this.formatDuration(elapsed);
                }});
            }},
            
            formatDuration(seconds) {{
                if (seconds < 60) return Math.floor(seconds) + 's';
                if (seconds < 3600) {{
                    const mins = Math.floor(seconds / 60);
                    const secs = Math.floor(seconds % 60);
                    return `${{mins}}m ${{secs}}s`;
                }}
                const hours = Math.floor(seconds / 3600);
                const mins = Math.floor((seconds % 3600) / 60);
                return `${{hours}}h ${{mins}}m`;
            }}
        }};
        
        // Update session durations every second
        setInterval(() => SessionController.updateDurations(), 1000);
        
        // === Terminal Controller ===
        const TerminalController = {{
            WS_PORT: {ws_port},
            socket: null,
            terminals: {{}},
            fitAddons: {{}},
            connected: false,
            modalBeadId: null,
            modalTerminal: null,
            modalFitAddon: null,
            
            init() {{
                this.connect();
                this.setupModalHandlers();
            }},
            
            connect() {{
                if (this.socket && this.socket.readyState === WebSocket.OPEN) return;
                
                try {{
                    this.socket = new WebSocket(`ws://localhost:${{this.WS_PORT}}`);
                    
                    this.socket.onopen = () => {{
                        console.log('Terminal WebSocket connected');
                        this.connected = true;
                        this.updateAllStatus();
                        // Subscribe to all visible terminals
                        document.querySelectorAll('[data-terminal-bead]').forEach(el => {{
                            const beadId = el.dataset.terminalBead;
                            this.subscribe(beadId);
                        }});
                    }};
                    
                    this.socket.onmessage = (event) => {{
                        const data = JSON.parse(event.data);
                        this.handleMessage(data);
                    }};
                    
                    this.socket.onclose = () => {{
                        console.log('Terminal WebSocket disconnected');
                        this.connected = false;
                        this.updateAllStatus();
                        // Attempt reconnect after 5s
                        setTimeout(() => this.connect(), 5000);
                    }};
                    
                    this.socket.onerror = (err) => {{
                        console.log('Terminal WebSocket error (server may not be running)');
                    }};
                }} catch (e) {{
                    console.log('Could not connect to terminal server');
                }}
            }},
            
            handleMessage(data) {{
                const beadId = data.bead_id;
                
                switch (data.type) {{
                    case 'buffer':
                    case 'output':
                        // Write to inline terminal
                        if (this.terminals[beadId]) {{
                            this.terminals[beadId].write(data.data);
                        }}
                        // Write to modal terminal if open
                        if (this.modalBeadId === beadId && this.modalTerminal) {{
                            this.modalTerminal.write(data.data);
                        }}
                        break;
                        
                    case 'subscribed':
                        console.log(`Subscribed to terminal: ${{beadId}}`);
                        this.updateStatus(beadId, true);
                        break;
                        
                    case 'terminated':
                        console.log(`Terminal terminated: ${{beadId}}`);
                        this.updateStatus(beadId, false);
                        if (this.terminals[beadId]) {{
                            this.terminals[beadId].write('\\r\\n\\x1b[31m[Terminal session ended]\\x1b[0m\\r\\n');
                        }}
                        break;
                        
                    case 'error':
                        console.error('Terminal error:', data.message);
                        break;
                }}
            }},
            
            subscribe(beadId) {{
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {{
                    this.socket.send(JSON.stringify({{
                        type: 'subscribe',
                        bead_id: beadId
                    }}));
                }}
            }},
            
            unsubscribe(beadId) {{
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {{
                    this.socket.send(JSON.stringify({{
                        type: 'unsubscribe',
                        bead_id: beadId
                    }}));
                }}
            }},
            
            sendInput(beadId, data) {{
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {{
                    this.socket.send(JSON.stringify({{
                        type: 'input',
                        bead_id: beadId,
                        data: data
                    }}));
                }}
            }},
            
            sendSignal(beadId, signal) {{
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {{
                    this.socket.send(JSON.stringify({{
                        type: 'signal',
                        bead_id: beadId,
                        signal: signal
                    }}));
                }}
            }},
            
            terminate(beadId) {{
                if (confirm(`Terminate agent process for ${{beadId}}?`)) {{
                    if (this.socket && this.socket.readyState === WebSocket.OPEN) {{
                        this.socket.send(JSON.stringify({{
                            type: 'terminate',
                            bead_id: beadId
                        }}));
                    }}
                }}
            }},
            
            resize(beadId, rows, cols) {{
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {{
                    this.socket.send(JSON.stringify({{
                        type: 'resize',
                        bead_id: beadId,
                        rows: rows,
                        cols: cols
                    }}));
                }}
            }},
            
            toggleDrawer(beadId) {{
                const drawer = document.getElementById(`terminal-drawer-${{beadId}}`);
                if (!drawer) return;
                
                const isOpen = drawer.classList.toggle('open');
                
                if (isOpen) {{
                    this.initTerminal(beadId);
                    this.subscribe(beadId);
                }}
            }},
            
            initTerminal(beadId) {{
                const containerId = `terminal-${{beadId}}`;
                const container = document.getElementById(containerId);
                if (!container || this.terminals[beadId]) return;
                
                const term = new Terminal({{
                    theme: {{
                        background: '#000000',
                        foreground: '#f1f5f9',
                        cursor: '#f1f5f9',
                        cursorAccent: '#000000',
                    }},
                    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
                    fontSize: 12,
                    cursorBlink: true,
                    scrollback: 5000,
                }});
                
                const fitAddon = new FitAddon.FitAddon();
                const webLinksAddon = new WebLinksAddon.WebLinksAddon();
                
                term.loadAddon(fitAddon);
                term.loadAddon(webLinksAddon);
                term.open(container);
                fitAddon.fit();
                
                // Handle user input
                term.onData(data => {{
                    this.sendInput(beadId, data);
                }});
                
                // Handle resize
                const resizeObserver = new ResizeObserver(() => {{
                    fitAddon.fit();
                    this.resize(beadId, term.rows, term.cols);
                }});
                resizeObserver.observe(container);
                
                this.terminals[beadId] = term;
                this.fitAddons[beadId] = fitAddon;
            }},
            
            openModal(beadId) {{
                const modal = document.getElementById('terminal-modal');
                const container = document.getElementById('modal-terminal-container');
                const beadIdSpan = document.getElementById('modal-bead-id');
                
                this.modalBeadId = beadId;
                beadIdSpan.textContent = beadId;
                modal.classList.add('open');
                
                // Create modal terminal
                if (this.modalTerminal) {{
                    this.modalTerminal.dispose();
                }}
                
                container.innerHTML = '';
                
                this.modalTerminal = new Terminal({{
                    theme: {{
                        background: '#000000',
                        foreground: '#f1f5f9',
                        cursor: '#f1f5f9',
                    }},
                    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
                    fontSize: 14,
                    cursorBlink: true,
                    scrollback: 10000,
                }});
                
                this.modalFitAddon = new FitAddon.FitAddon();
                this.modalTerminal.loadAddon(this.modalFitAddon);
                this.modalTerminal.loadAddon(new WebLinksAddon.WebLinksAddon());
                this.modalTerminal.open(container);
                
                setTimeout(() => {{
                    this.modalFitAddon.fit();
                    this.resize(beadId, this.modalTerminal.rows, this.modalTerminal.cols);
                }}, 100);
                
                // Handle input
                this.modalTerminal.onData(data => {{
                    this.sendInput(beadId, data);
                }});
                
                // Copy buffer from inline terminal if exists
                if (this.terminals[beadId]) {{
                    // Request full buffer
                    if (this.socket && this.socket.readyState === WebSocket.OPEN) {{
                        this.socket.send(JSON.stringify({{
                            type: 'history',
                            bead_id: beadId
                        }}));
                    }}
                }}
                
                // Handle resize
                window.addEventListener('resize', this.handleModalResize);
            }},
            
            handleModalResize: function() {{
                if (TerminalController.modalFitAddon) {{
                    TerminalController.modalFitAddon.fit();
                    if (TerminalController.modalTerminal && TerminalController.modalBeadId) {{
                        TerminalController.resize(
                            TerminalController.modalBeadId,
                            TerminalController.modalTerminal.rows,
                            TerminalController.modalTerminal.cols
                        );
                    }}
                }}
            }},
            
            closeModal() {{
                const modal = document.getElementById('terminal-modal');
                modal.classList.remove('open');
                window.removeEventListener('resize', this.handleModalResize);
                this.modalBeadId = null;
            }},
            
            setupModalHandlers() {{
                // Close on Escape
                document.addEventListener('keydown', (e) => {{
                    if (e.key === 'Escape' && this.modalBeadId) {{
                        this.closeModal();
                    }}
                }});
            }},
            
            updateStatus(beadId, connected) {{
                const status = document.querySelector(`#terminal-status-${{beadId}}`);
                if (status) {{
                    status.className = `terminal-status ${{connected ? 'connected' : 'disconnected'}}`;
                    status.innerHTML = connected 
                        ? '<span class="pulse"></span> Connected'
                        : '○ Disconnected';
                }}
            }},
            
            updateAllStatus() {{
                document.querySelectorAll('[data-terminal-bead]').forEach(el => {{
                    const beadId = el.dataset.terminalBead;
                    this.updateStatus(beadId, this.connected);
                }});
            }}
        }};
        
        // Update toggle UI after DOM is ready
        document.addEventListener('DOMContentLoaded', () => {{
            ThemeController.updateToggleUI();
            // Initialize terminal controller if any terminals are present
            if (document.querySelector('[data-terminal-bead]')) {{
                TerminalController.init();
            }}
        }});
        
        // Listen for system preference changes
        window.matchMedia('(prefers-color-scheme: dark)')
            .addEventListener('change', () => ThemeController.updateToggleUI());
        
        // Filter change handler
        const filterSelect = document.querySelector('.filter-select');
        if (filterSelect) {{
            filterSelect.addEventListener('change', (e) => {{
                const filter = e.target.value;
                const url = new URL(window.location);
                if (filter) {{
                    url.searchParams.set('filter', filter);
                }} else {{
                    url.searchParams.delete('filter');
                }}
                window.location = url;
            }});
        }}
    </script>
</body>
</html>'''


def get_all_labels(issues: List[Dict[str, Any]]) -> List[str]:
    """Extract unique labels from issues for filter dropdown."""
    labels = set()
    for issue in issues:
        for label in issue.get('labels', []):
            labels.add(label)
    return sorted(labels)


# GitHub icon SVG (T020)
GITHUB_ICON = '''<svg class="github-icon" viewBox="0 0 16 16" width="14" height="14">
<path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
</svg>'''


def render_card(issue: Dict[str, Any], terminals: Optional[Dict[str, Any]] = None,
                sessions: Optional[Dict[str, Any]] = None) -> str:
    """Render a single issue card with priority, type, time, labels, GitHub link, session status, and terminal."""
    issue_id = issue.get('id', 'unknown')
    title = issue.get('title', 'Untitled')
    priority = issue.get('priority', 4)
    issue_type = issue.get('issue_type', 'task')
    labels = issue.get('labels', [])
    created_at = issue.get('created_at', '')
    github_url = issue.get('github_url', '')
    status = issue.get('status', 'open')
    
    terminals = terminals or {}
    sessions = sessions or {}
    
    # Priority class
    p_class = f'p{min(priority, 4)}'
    
    # Priority label
    p_labels = {0: 'P0', 1: 'P1', 2: 'P2', 3: 'P3', 4: 'P4'}
    p_label = p_labels.get(priority, 'P4')
    
    # Type badge class
    type_class = issue_type if issue_type in ('bug', 'feature', 'epic') else ''
    
    # T010: Labels HTML (max 3, filter internal ones)
    labels_html = ''
    if labels:
        visible_labels = [l for l in labels[:3] if not l.startswith('speckle')]
        if visible_labels:
            labels_html = '<div class="labels">' + ''.join(
                f'<span class="label">{l}</span>' for l in visible_labels
            ) + '</div>'
    
    # T008: Time ago
    age = time_ago(created_at)
    
    # T020-T021: GitHub link
    github_html = ''
    if github_url:
        github_html = f'''<a href="{github_url}" target="_blank" class="github-link" 
           title="View on GitHub">{GITHUB_ICON}</a>'''
    
    # Session info
    session_info = sessions.get(issue_id, {})
    session_state = session_info.get('state', '')
    session_active = session_info.get('is_active', False)
    session_started = session_info.get('started_at', '')
    session_duration = session_info.get('duration', 0)
    
    # Session status HTML
    session_html = ''
    
    # For in_progress cards
    if status == 'in_progress':
        if session_active:
            # Active session - show status, duration, and controls
            state_labels = {
                'running': ('🟢', 'Running'),
                'spawning': ('🔵', 'Starting...'),
                'stuck': ('🟡', 'Stuck'),
            }
            state_icon, state_label = state_labels.get(session_state, ('⚪', session_state))
            
            duration_html = ''
            if session_started:
                duration_html = f'<span class="session-duration" data-session-started="{session_started}">{format_duration(session_duration)}</span>'
            
            session_html = f'''
        <div class="session-info">
            <span class="session-indicator {session_state}" title="Session {session_state}">
                {state_icon} {state_label}
            </span>
            {duration_html}
        </div>
        <div class="session-actions">
            <button class="session-btn danger" onclick="SessionController.terminate('{issue_id}')" title="Stop session">
                ⏹ Stop
            </button>
        </div>'''
        else:
            # No active session - show start button
            session_html = f'''
        <div class="session-actions">
            <button id="spawn-btn-{issue_id}" class="session-btn primary" onclick="SessionController.spawn('{issue_id}')" title="Start Claude session">
                ▶ Start Session
            </button>
        </div>'''
    
    # For open/backlog cards - optionally show start button
    elif status == 'open' and priority <= 2:
        # Show start button for high-priority backlog items
        session_html = f'''
        <div class="session-actions" style="margin-top: 0.5rem;">
            <button id="spawn-btn-{issue_id}" class="session-btn" onclick="SessionController.spawn('{issue_id}')" title="Start Claude session (will set to in_progress)">
                ▶ Start
            </button>
        </div>'''
    
    # Terminal drawer for in_progress cards with active terminal
    terminal_html = ''
    has_terminal = issue_id in terminals
    
    if status == 'in_progress':
        if has_terminal or session_active:
            terminal_html = f'''
        <div class="terminal-section" data-terminal-bead="{issue_id}">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-top: 0.5rem;">
                <span class="terminal-indicator" onclick="TerminalController.toggleDrawer('{issue_id}')" title="Toggle terminal">
                    <span class="pulse"></span>
                    Terminal
                </span>
                <button class="terminal-btn" onclick="TerminalController.openModal('{issue_id}')" title="Full screen">⛶</button>
            </div>
            <div id="terminal-drawer-{issue_id}" class="terminal-drawer">
                <div class="terminal-container" id="terminal-{issue_id}"></div>
                <div class="terminal-controls">
                    <button class="terminal-btn" onclick="TerminalController.sendSignal('{issue_id}', 'SIGINT')">Send Ctrl+C</button>
                    <button class="terminal-btn danger" onclick="TerminalController.terminate('{issue_id}')">Terminate</button>
                    <button class="terminal-btn" onclick="TerminalController.openModal('{issue_id}')">Full Screen</button>
                    <span id="terminal-status-{issue_id}" class="terminal-status disconnected">○ Connecting...</span>
                </div>
            </div>
        </div>'''
    
    return f'''
    <div class="card {p_class}">
        <div class="card-header">
            <span class="card-id">{issue_id}</span>
            <div class="card-actions">
                {github_html}
                <span class="priority-badge {p_class}">{p_label}</span>
            </div>
        </div>
        <div class="card-title">{title}</div>
        <div class="card-meta">
            <span class="type-badge {type_class}">{issue_type}</span>
            <span>{age}</span>
        </div>
        {labels_html}
        {session_html}
        {terminal_html}
    </div>
    '''


def render_column(status: str, issues: List[Dict[str, Any]], terminals: Optional[Dict[str, Any]] = None,
                  sessions: Optional[Dict[str, Any]] = None) -> str:
    """Render a kanban column as HTML."""
    terminals = terminals or {}
    sessions = sessions or {}
    
    icons = {
        'open': '📋',
        'in_progress': '🔄',
        'blocked': '🚫',
        'closed': '✅'
    }
    titles = {
        'open': 'BACKLOG',
        'in_progress': 'IN PROGRESS',
        'blocked': 'BLOCKED',
        'closed': 'DONE'
    }
    
    icon = icons.get(status, '📋')
    title = titles.get(status, status.upper())
    count = len(issues)
    
    if issues:
        cards_html = ''.join(render_card(issue, terminals, sessions) for issue in issues)
    else:
        cards_html = '<div class="empty">No issues</div>'
    
    return f'''
    <div class="column {status}">
        <div class="column-header">
            <span class="column-title">{icon} {title}</span>
            <span class="column-count">{count}</span>
        </div>
        <div class="cards">
            {cards_html}
        </div>
    </div>
    '''


def render_board(issues: List[Dict[str, Any]], label_filter: Optional[str] = None,
                 refresh: int = DEFAULT_REFRESH, ws_port: int = TERMINAL_WS_PORT) -> str:
    """Render the full board as HTML."""
    columns = group_by_status(issues)
    all_labels = get_all_labels(issues)
    
    # Get active terminal sessions
    terminals = get_active_terminals()
    
    # Get Claude session info
    sessions = get_sessions_info()
    
    # Build columns HTML
    columns_html = ''
    for status in ['open', 'in_progress', 'blocked', 'closed']:
        columns_html += render_column(status, columns[status], terminals, sessions)
    
    # Filter dropdown
    filter_options = '<option value="">All issues</option>'
    for label in all_labels:
        selected = 'selected' if label == label_filter else ''
        filter_options += f'<option value="{label}" {selected}>{label}</option>'
    
    filter_html = f'<select class="filter-select">{filter_options}</select>' if all_labels else ''
    
    # Metadata
    timestamp = datetime.now().strftime('%H:%M:%S')
    issue_count = sum(len(v) for v in columns.values())
    
    return HTML_TEMPLATE.format(
        columns_html=columns_html,
        filter_html=filter_html,
        refresh=refresh,
        timestamp=timestamp,
        issue_count=issue_count,
        ws_port=ws_port
    )


class BoardHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for the kanban board."""
    
    label_filter: Optional[str] = None
    refresh: int = DEFAULT_REFRESH
    show_github: bool = False
    ws_port: int = TERMINAL_WS_PORT
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        
        if parsed.path == '/':
            # Get filter from query string or class default
            label_filter = query.get('filter', [self.label_filter])[0]
            if label_filter == '':
                label_filter = None
            
            issues = get_issues(label_filter)
            
            # T023: Merge GitHub links if enabled
            if self.show_github:
                github_links = load_github_links()
                issues = merge_github_links(issues, github_links)
            
            html = render_board(issues, label_filter, self.refresh, self.ws_port)
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            
        elif parsed.path == '/api/issues':
            label_filter = query.get('filter', [None])[0]
            issues = get_issues(label_filter)
            
            # T023: Include GitHub links in API response if enabled
            if self.show_github:
                github_links = load_github_links()
                issues = merge_github_links(issues, github_links)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(issues).encode('utf-8'))
        
        elif parsed.path == '/api/terminals':
            # Return active terminal sessions
            terminals = get_active_terminals()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(terminals).encode('utf-8'))
            
        elif parsed.path == '/api/sessions':
            # Return all sessions info
            sessions = get_sessions_info()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(sessions).encode('utf-8'))
            
        elif parsed.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            
        else:
            self.send_error(404)
    
    def do_POST(self):
        """Handle POST requests for session control."""
        parsed = urllib.parse.urlparse(self.path)
        
        # Session spawn: POST /api/sessions/{bead_id}/spawn
        if parsed.path.startswith('/api/sessions/') and parsed.path.endswith('/spawn'):
            bead_id = parsed.path.split('/')[3]
            result = spawn_session(bead_id)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        
        # Session terminate: POST /api/sessions/{bead_id}/terminate
        elif parsed.path.startswith('/api/sessions/') and parsed.path.endswith('/terminate'):
            bead_id = parsed.path.split('/')[3]
            result = terminate_session(bead_id)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        
        else:
            self.send_error(404)


# === T023: GitHub Links Loading ===
GITHUB_LINKS_FILE = '.speckle/github-links.jsonl'


def load_github_links() -> Dict[str, str]:
    """Load GitHub links from JSONL file, returning {bead_id: github_url}."""
    links = {}
    try:
        with open(GITHUB_LINKS_FILE) as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    links[data.get('bead_id', '')] = data.get('github_url', '')
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return links


def merge_github_links(issues: List[Dict[str, Any]], links: Dict[str, str]) -> List[Dict[str, Any]]:
    """Merge GitHub URLs into issue dicts."""
    for issue in issues:
        issue_id = issue.get('id', '')
        if issue_id in links:
            issue['github_url'] = links[issue_id]
    return issues


def main():
    """Entry point - start the HTTP server."""
    parser = argparse.ArgumentParser(description='Speckle Kanban Board Server')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                        help=f'Port to listen on (default: {DEFAULT_PORT})')
    parser.add_argument('--refresh', type=int, default=DEFAULT_REFRESH,
                        help=f'Auto-refresh interval in seconds (default: {DEFAULT_REFRESH})')
    parser.add_argument('--filter', type=str, default=None,
                        help='Filter by label')
    parser.add_argument('--no-browser', action='store_true',
                        help="Don't auto-open browser")
    parser.add_argument('--github', action='store_true',
                        help='Show GitHub links on cards (loads from .speckle/github-links.jsonl)')
    parser.add_argument('--ws-port', type=int, default=TERMINAL_WS_PORT,
                        help=f'WebSocket port for terminal server (default: {TERMINAL_WS_PORT})')
    args = parser.parse_args()
    
    # Configure handler
    BoardHandler.label_filter = args.filter
    BoardHandler.refresh = args.refresh
    BoardHandler.show_github = args.github
    BoardHandler.ws_port = args.ws_port
    
    # Start server
    server = http.server.HTTPServer(('localhost', args.port), BoardHandler)
    
    url = f'http://localhost:{args.port}'
    if args.filter:
        url += f'?filter={urllib.parse.quote(args.filter)}'
    
    github_status = '✓ enabled' if args.github else '(disabled)'
    
    # Check if terminal server is available
    terminals = get_active_terminals()
    terminal_count = len(terminals)
    
    print(f'''
🔮 Speckle Board
════════════════════════════════════════
   URL:       {url}
   Refresh:   {args.refresh}s
   Filter:    {args.filter or '(none)'}
   GitHub:    {github_status}
   
   Terminal Mirroring:
   WebSocket: ws://localhost:{args.ws_port}
   Active:    {terminal_count} session(s)
════════════════════════════════════════
   💡 Start terminal server:
   python .speckle/scripts/terminal_server.py server

   Press Ctrl+C to stop
''')
    
    # T015: Auto-open browser
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass  # Silently fail if browser can't open
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n👋 Board stopped')
        server.shutdown()


if __name__ == '__main__':
    main()
