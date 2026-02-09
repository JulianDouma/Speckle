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


# === Epic View Mode: Hierarchical Task Visualization (gh-59) ===

def calculate_epic_progress(children: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate progress statistics for an epic based on its children."""
    if not children:
        return {'total': 0, 'closed': 0, 'in_progress': 0, 'percent': 0}
    
    total = len(children)
    closed = sum(1 for c in children if c.get('status') == 'closed')
    in_progress = sum(1 for c in children if c.get('status') == 'in_progress')
    blocked = sum(1 for c in children if c.get('status') in ('blocked', 'deferred'))
    
    percent = int((closed / total) * 100) if total > 0 else 0
    
    return {
        'total': total,
        'closed': closed,
        'in_progress': in_progress,
        'blocked': blocked,
        'open': total - closed - in_progress - blocked,
        'percent': percent
    }


def should_expand_epic(epic: Dict[str, Any], children: List[Dict[str, Any]]) -> bool:
    """Determine if an epic should be auto-expanded in the UI."""
    # Always expand if has in-progress children (active work)
    if any(c.get('status') == 'in_progress' for c in children):
        return True
    
    # Expand if has blocked children (needs attention)
    if any(c.get('status') in ('blocked', 'deferred') for c in children):
        return True
    
    # Expand if recently updated (within 24 hours)
    try:
        updated = epic.get('updated_at', '')
        if updated:
            dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            if age_hours < 24:
                return True
    except (ValueError, TypeError):
        pass
    
    # Expand if epic itself is in progress
    if epic.get('status') == 'in_progress':
        return True
    
    return False


def get_issues_with_hierarchy(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Organize issues into a hierarchy of epics and their children.
    
    Returns:
        {
            'epics': {
                'epic-id': {
                    ...epic_data,
                    'children': [...],
                    'progress': {...},
                    'expanded': bool
                }
            },
            'orphans': [...],  # Tasks without parent epic
            'flat_issues': [...]  # All issues for flat view
        }
    """
    # Identify epics and build parent-child map
    epics = {}
    children_map = {}  # parent_id -> [children]
    orphans = []
    
    for issue in issues:
        issue_type = issue.get('issue_type', 'task')
        
        # Extract parent from dependencies array (beads format)
        parent_id = issue.get('parent', '')
        if not parent_id:
            for dep in issue.get('dependencies', []):
                if dep.get('type') == 'parent-child':
                    parent_id = dep.get('depends_on_id', '')
                    break
        
        if issue_type == 'epic':
            epics[issue['id']] = {
                **issue,
                'children': [],
                'progress': {'total': 0, 'closed': 0, 'percent': 0},
                'expanded': False
            }
        elif parent_id:
            # Has a parent - add to children map
            if parent_id not in children_map:
                children_map[parent_id] = []
            children_map[parent_id].append(issue)
        else:
            # No parent and not an epic - orphan
            if issue_type != 'epic':
                orphans.append(issue)
    
    # Attach children to their epics and calculate progress
    for epic_id, epic in epics.items():
        children = children_map.get(epic_id, [])
        epic['children'] = sorted(children, key=lambda x: (x.get('priority', 4), x.get('created_at', '')))
        epic['progress'] = calculate_epic_progress(children)
        epic['expanded'] = should_expand_epic(epic, children)
    
    # Sort epics by priority then name
    sorted_epics = dict(sorted(
        epics.items(),
        key=lambda x: (x[1].get('priority', 4), x[1].get('title', ''))
    ))
    
    # Sort orphans
    orphans.sort(key=lambda x: (x.get('priority', 4), x.get('created_at', '')))
    
    return {
        'epics': sorted_epics,
        'orphans': orphans,
        'flat_issues': issues  # Keep original flat list
    }


def group_by_status_hierarchical(hierarchy: Dict[str, Any], max_closed: int = MAX_CLOSED) -> Dict[str, Dict]:
    """
    Group hierarchical issues by status, preserving epic structure.
    
    Returns columns where each contains either:
    - Epics with their children
    - Orphan tasks
    """
    columns = {
        'open': {'epics': [], 'orphans': []},
        'in_progress': {'epics': [], 'orphans': []},
        'blocked': {'epics': [], 'orphans': []},
        'closed': {'epics': [], 'orphans': []}
    }
    
    # Group epics by their status
    for epic_id, epic in hierarchy['epics'].items():
        status = epic.get('status', 'open')
        if status == 'deferred':
            status = 'blocked'
        if status in columns:
            columns[status]['epics'].append(epic)
    
    # Group orphans by their status
    for orphan in hierarchy['orphans']:
        status = orphan.get('status', 'open')
        if status == 'deferred':
            status = 'blocked'
        if status in columns:
            columns[status]['orphans'].append(orphan)
    
    # Limit closed items
    columns['closed']['epics'] = columns['closed']['epics'][:max_closed]
    columns['closed']['orphans'] = columns['closed']['orphans'][:max_closed - len(columns['closed']['epics'])]
    
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
    <!-- Auto-refresh disabled when terminal is open - handled by JavaScript -->
    <title>Speckle Board</title>
    <style>
        /* ============================================================
           FLUENT 1 DESIGN SYSTEM - Microsoft Office/365 Style
           Based on Syncfusion Fluent Theme & Office UI Fabric
           ============================================================ */
        
        /* === DESIGN TOKENS === */
        :root {{
            /* Fluent 1 Primary - Microsoft Blue */
            --fluent-primary: #0078d4;
            --fluent-primary-dark: #106ebe;
            --fluent-primary-darker: #005a9e;
            --fluent-primary-light: #2b88d8;
            --fluent-primary-lighter: #c7e0f4;
            
            /* Semantic Colors */
            --fluent-red: #d13438;
            --fluent-orange: #ca5010;
            --fluent-yellow: #ffb900;
            --fluent-green: #107c10;
            --fluent-cyan: #038387;
            --fluent-purple: #8764b8;
            
            /* Gray Scale (Light Theme) */
            --fluent-gray-10: #faf9f8;
            --fluent-gray-20: #f3f2f1;
            --fluent-gray-30: #edebe9;
            --fluent-gray-40: #e1dfdd;
            --fluent-gray-50: #d2d0ce;
            --fluent-gray-60: #c8c6c4;
            --fluent-gray-90: #a19f9d;
            --fluent-gray-110: #8a8886;
            --fluent-gray-130: #605e5c;
            --fluent-gray-150: #3b3a39;
            --fluent-gray-160: #323130;
            --fluent-gray-190: #201f1e;
            
            /* Semantic Mappings */
            --bg: var(--fluent-gray-10);
            --card-bg: #ffffff;
            --text: var(--fluent-gray-190);
            --text-muted: var(--fluent-gray-130);
            --border: var(--fluent-gray-40);
            --border-strong: var(--fluent-gray-60);
            
            /* Column backgrounds - subtle tints */
            --backlog: var(--fluent-gray-20);
            --progress: #deecf9;
            --blocked: #fed9cc;
            --done: #dff6dd;
            
            /* Priority colors */
            --p0: var(--fluent-red);
            --p1: var(--fluent-red);
            --p2: var(--fluent-orange);
            --p3: var(--fluent-green);
            --p4: var(--fluent-gray-110);
            
            /* Fluent Shadows */
            --shadow-4: 0 1.6px 3.6px 0 rgba(0,0,0,0.132), 0 0.3px 0.9px 0 rgba(0,0,0,0.108);
            --shadow-8: 0 3.2px 7.2px 0 rgba(0,0,0,0.132), 0 0.6px 1.8px 0 rgba(0,0,0,0.108);
            --shadow-16: 0 6.4px 14.4px 0 rgba(0,0,0,0.132), 0 1.2px 3.6px 0 rgba(0,0,0,0.108);
            --shadow-64: 0 25.6px 57.6px 0 rgba(0,0,0,0.22), 0 4.8px 14.4px 0 rgba(0,0,0,0.18);
            
            /* Legacy shadow mappings */
            --shadow-sm: var(--shadow-4);
            --shadow-md: var(--shadow-8);
            
            /* Badge backgrounds */
            --badge-p0-bg: rgba(209, 52, 56, 0.15);
            --badge-p0-text: var(--fluent-red);
            --badge-p2-bg: rgba(202, 80, 16, 0.15);
            --badge-p2-text: #a33d10;
            --badge-p3-bg: rgba(16, 124, 16, 0.15);
            --badge-p3-text: #0b6a0b;
            
            /* Type badges */
            --type-bg: var(--fluent-gray-30);
            --type-bug-bg: rgba(209, 52, 56, 0.15);
            --type-bug-text: var(--fluent-red);
            --type-feature-bg: rgba(0, 120, 212, 0.15);
            --type-feature-text: var(--fluent-primary);
            --type-epic-bg: rgba(135, 100, 184, 0.15);
            --type-epic-text: var(--fluent-purple);
            
            /* Label badges */
            --label-bg: var(--fluent-gray-30);
            --label-text: var(--fluent-gray-160);
            
            /* Column header accent */
            --column-border: var(--fluent-gray-50);
            
            /* Motion */
            --ease-1: cubic-bezier(0.1, 0.9, 0.2, 1);
            --duration-1: 100ms;
            --duration-2: 200ms;
        }}
        
        /* === DARK THEME === */
        [data-theme="dark"] {{
            --fluent-gray-10: #1b1a19;
            --fluent-gray-20: #252423;
            --fluent-gray-30: #292827;
            --fluent-gray-40: #323130;
            --fluent-gray-50: #3b3a39;
            --fluent-gray-60: #484644;
            --fluent-gray-90: #797775;
            --fluent-gray-110: #979593;
            --fluent-gray-130: #b3b0ad;
            --fluent-gray-150: #d2d0ce;
            --fluent-gray-160: #e1dfdd;
            --fluent-gray-190: #f3f2f1;
            
            --fluent-primary: #2899f5;
            --fluent-primary-dark: #0078d4;
            --fluent-primary-light: #6cb8f6;
            
            --bg: #1b1a19;
            --card-bg: #252423;
            --text: #f3f2f1;
            --text-muted: #b3b0ad;
            --border: #484644;
            --border-strong: #605e5c;
            
            --backlog: #252423;
            --progress: #0a3d62;
            --blocked: #4a1e1b;
            --done: #1a3d1a;
            
            --shadow-4: 0 1.6px 3.6px 0 rgba(0,0,0,0.4), 0 0.3px 0.9px 0 rgba(0,0,0,0.32);
            --shadow-8: 0 3.2px 7.2px 0 rgba(0,0,0,0.4), 0 0.6px 1.8px 0 rgba(0,0,0,0.32);
            --shadow-16: 0 6.4px 14.4px 0 rgba(0,0,0,0.4), 0 1.2px 3.6px 0 rgba(0,0,0,0.32);
            
            --badge-p0-bg: rgba(243, 135, 135, 0.2);
            --badge-p0-text: #f38787;
            --badge-p2-bg: rgba(255, 185, 0, 0.2);
            --badge-p2-text: #ffb900;
            --badge-p3-bg: rgba(146, 195, 83, 0.2);
            --badge-p3-text: #92c353;
            
            --type-bg: #3b3a39;
            --type-bug-bg: rgba(243, 135, 135, 0.2);
            --type-bug-text: #f38787;
            --type-feature-bg: rgba(40, 153, 245, 0.2);
            --type-feature-text: #6cb8f6;
            --type-epic-bg: rgba(177, 151, 252, 0.2);
            --type-epic-text: #b197fc;
            
            --label-bg: #3b3a39;
            --label-text: #d2d0ce;
            
            --column-border: #484644;
        }}
        
        /* === SYSTEM PREFERENCE === */
        @media (prefers-color-scheme: dark) {{
            :root:not([data-theme]) {{
                --fluent-gray-10: #1b1a19;
                --fluent-gray-20: #252423;
                --fluent-gray-30: #292827;
                --fluent-gray-40: #323130;
                --fluent-gray-50: #3b3a39;
                --fluent-gray-60: #484644;
                --fluent-gray-90: #797775;
                --fluent-gray-110: #979593;
                --fluent-gray-130: #b3b0ad;
                --fluent-gray-150: #d2d0ce;
                --fluent-gray-160: #e1dfdd;
                --fluent-gray-190: #f3f2f1;
                --fluent-primary: #2899f5;
                --fluent-primary-dark: #0078d4;
                --fluent-primary-light: #6cb8f6;
                --bg: #1b1a19;
                --card-bg: #252423;
                --text: #f3f2f1;
                --text-muted: #b3b0ad;
                --border: #484644;
                --border-strong: #605e5c;
                --backlog: #252423;
                --progress: #0a3d62;
                --blocked: #4a1e1b;
                --done: #1a3d1a;
                --shadow-4: 0 1.6px 3.6px 0 rgba(0,0,0,0.4), 0 0.3px 0.9px 0 rgba(0,0,0,0.32);
                --shadow-8: 0 3.2px 7.2px 0 rgba(0,0,0,0.4), 0 0.6px 1.8px 0 rgba(0,0,0,0.32);
                --shadow-16: 0 6.4px 14.4px 0 rgba(0,0,0,0.4), 0 1.2px 3.6px 0 rgba(0,0,0,0.32);
                --badge-p0-bg: rgba(243, 135, 135, 0.2);
                --badge-p0-text: #f38787;
                --badge-p2-bg: rgba(255, 185, 0, 0.2);
                --badge-p2-text: #ffb900;
                --badge-p3-bg: rgba(146, 195, 83, 0.2);
                --badge-p3-text: #92c353;
                --type-bg: #3b3a39;
                --type-bug-bg: rgba(243, 135, 135, 0.2);
                --type-bug-text: #f38787;
                --type-feature-bg: rgba(40, 153, 245, 0.2);
                --type-feature-text: #6cb8f6;
                --type-epic-bg: rgba(177, 151, 252, 0.2);
                --type-epic-text: #b197fc;
                --label-bg: #3b3a39;
                --label-text: #d2d0ce;
                --column-border: #484644;
            }}
        }}
        
        /* === BASE STYLES === */
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: "Segoe UI", "Segoe UI Web (West European)", -apple-system, BlinkMacSystemFont, Roboto, "Helvetica Neue", sans-serif;
            font-size: 14px;
            line-height: 20px;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            transition: background-color var(--duration-2) var(--ease-1), color var(--duration-2) var(--ease-1);
        }}
        
        /* === HEADER (Fluent CommandBar) === */
        header {{
            background: var(--card-bg);
            color: var(--text);
            padding: 0 16px;
            height: 44px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            box-shadow: var(--shadow-4);
        }}
        
        header h1 {{
            font-size: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .controls {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        /* === THEME TOGGLE (Fluent Toggle) === */
        .theme-toggle {{
            position: relative;
            width: 40px;
            height: 20px;
            background: var(--fluent-gray-90);
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: background var(--duration-1) var(--ease-1);
            padding: 0;
        }}
        
        .theme-toggle::after {{
            content: '';
            position: absolute;
            top: 2px;
            left: 2px;
            width: 16px;
            height: 16px;
            background: #ffffff;
            border-radius: 50%;
            box-shadow: var(--shadow-4);
            transition: transform var(--duration-1) var(--ease-1);
        }}
        
        .theme-toggle:hover {{
            background: var(--fluent-gray-110);
        }}
        
        .theme-toggle[data-active="true"] {{
            background: var(--fluent-primary);
        }}
        
        .theme-toggle[data-active="true"]::after {{
            transform: translateX(20px);
        }}
        
        /* === REFRESH BADGE === */
        .refresh-badge {{
            background: var(--fluent-gray-30);
            color: var(--text-muted);
            padding: 4px 12px;
            border-radius: 2px;
            font-size: 12px;
            font-weight: 400;
        }}
        
        /* === FILTER SELECT (Fluent Dropdown) === */
        .filter-select {{
            appearance: none;
            background: var(--card-bg);
            border: 1px solid var(--border-strong);
            color: var(--text);
            padding: 0 28px 0 8px;
            height: 32px;
            border-radius: 2px;
            font-size: 14px;
            font-family: inherit;
            cursor: pointer;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23605e5c' d='M2.5 4.5L6 8l3.5-3.5z'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 8px center;
            transition: border-color var(--duration-1) var(--ease-1);
        }}
        
        .filter-select:hover {{
            border-color: var(--fluent-gray-130);
        }}
        
        .filter-select:focus {{
            outline: none;
            border-color: var(--fluent-primary);
        }}
        
        .filter-select option {{
            background: var(--card-bg);
            color: var(--text);
        }}
        
        /* === BOARD LAYOUT === */
        .board {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            padding: 16px;
            max-width: 1600px;
            margin: 0 auto;
            min-height: calc(100vh - 108px);
        }}
        
        @media (max-width: 1024px) {{
            .board {{ grid-template-columns: repeat(2, 1fr); }}
        }}
        
        @media (max-width: 640px) {{
            .board {{ grid-template-columns: 1fr; }}
        }}
        
        /* === COLUMNS (Fluent Surface) === */
        .column {{
            background: var(--backlog);
            border: 1px solid var(--border);
            border-radius: 4px;
            display: flex;
            flex-direction: column;
            min-height: 200px;
            overflow: hidden;
        }}
        
        .column.in_progress {{ background: var(--progress); }}
        .column.blocked {{ background: var(--blocked); }}
        .column.closed {{ background: var(--done); }}
        
        .column-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            background: var(--card-bg);
            border-bottom: 1px solid var(--border);
        }}
        
        /* Status accent on column headers */
        .column.open .column-header {{ border-left: 3px solid var(--fluent-gray-110); }}
        .column.in_progress .column-header {{ border-left: 3px solid var(--fluent-primary); }}
        .column.blocked .column-header {{ border-left: 3px solid var(--fluent-red); }}
        .column.closed .column-header {{ border-left: 3px solid var(--fluent-green); }}
        
        .column-title {{
            font-weight: 600;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text);
        }}
        
        .column-count {{
            background: var(--fluent-gray-30);
            color: var(--text-muted);
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 600;
        }}
        
        .cards {{
            flex: 1;
            overflow-y: auto;
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        
        /* === CARDS (Fluent DocumentCard) === */
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 12px;
            border-left: 3px solid var(--fluent-gray-110);
            transition: box-shadow var(--duration-2) var(--ease-1), 
                        border-color var(--duration-1) var(--ease-1),
                        transform var(--duration-2) var(--ease-1);
        }}
        
        .card:hover {{
            box-shadow: var(--shadow-8);
            border-color: var(--border-strong);
            transform: translateY(-2px);
        }}
        
        .card.p0, .card.p1 {{ border-left-color: var(--fluent-red); }}
        .card.p2 {{ border-left-color: var(--fluent-orange); }}
        .card.p3 {{ border-left-color: var(--fluent-green); }}
        .card.p4 {{ border-left-color: var(--fluent-gray-110); }}
        
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }}
        
        .card-id {{
            font-family: "Consolas", "Courier New", monospace;
            font-size: 11px;
            color: var(--text-muted);
        }}
        
        /* === BADGES (Fluent Tag) === */
        .priority-badge {{
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 2px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
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
            font-size: 14px;
            font-weight: 600;
            line-height: 20px;
            margin-bottom: 8px;
            color: var(--text);
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        
        .card-meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
            color: var(--text-muted);
        }}
        
        /* === TYPE BADGES === */
        .type-badge {{
            background: var(--type-bg);
            color: var(--text-muted);
            padding: 2px 6px;
            border-radius: 2px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .type-badge.bug {{ background: var(--type-bug-bg); color: var(--type-bug-text); }}
        .type-badge.feature {{ background: var(--type-feature-bg); color: var(--type-feature-text); }}
        .type-badge.epic {{ background: var(--type-epic-bg); color: var(--type-epic-text); }}
        
        /* === LABELS === */
        .labels {{
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            margin-top: 8px;
        }}
        
        .label {{
            background: var(--label-bg);
            color: var(--label-text);
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 2px;
        }}
        
        .empty {{
            color: var(--text-muted);
            text-align: center;
            padding: 32px;
            font-size: 14px;
        }}
        
        /* === GITHUB LINK === */
        .card-actions {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .github-link {{
            color: var(--text-muted);
            text-decoration: none;
            display: flex;
            align-items: center;
            transition: color var(--duration-1) var(--ease-1);
        }}
        
        .github-link:hover {{
            color: var(--text);
        }}
        
        .github-icon {{
            width: 14px;
            height: 14px;
        }}
        
        /* === FOOTER === */
        footer {{
            text-align: center;
            padding: 16px;
            color: var(--text-muted);
            font-size: 12px;
            border-top: 1px solid var(--border);
        }}
        
        /* === EPIC VIEW MODE (gh-59) === */
        .epic-card {{
            background: var(--card-bg);
            border-radius: 4px;
            box-shadow: var(--shadow-sm);
            margin-bottom: 12px;
            border-left: 3px solid var(--fluent-purple);
            overflow: hidden;
        }}
        
        .epic-card.p0, .epic-card.p1 {{ border-left-color: var(--fluent-red); }}
        .epic-card.p2 {{ border-left-color: var(--fluent-orange); }}
        .epic-card.p3, .epic-card.p4 {{ border-left-color: var(--fluent-green); }}
        
        .epic-header {{
            display: flex;
            align-items: center;
            padding: 12px;
            cursor: pointer;
            gap: 10px;
            transition: background var(--duration-1) var(--ease-1);
        }}
        
        .epic-header:hover {{
            background: var(--fluent-gray-20);
        }}
        
        .expand-icon {{
            font-size: 10px;
            color: var(--text-muted);
            width: 16px;
            flex-shrink: 0;
            transition: transform var(--duration-1) var(--ease-1);
        }}
        
        .epic-info {{
            flex: 1;
            min-width: 0;
        }}
        
        .epic-title {{
            font-weight: 600;
            font-size: 13px;
            color: var(--text);
            display: block;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        
        .epic-meta {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 4px;
            font-size: 11px;
            color: var(--text-muted);
        }}
        
        .epic-count {{
            font-weight: 500;
        }}
        
        .epic-status-badge {{
            font-size: 10px;
            padding: 1px 6px;
            border-radius: 2px;
        }}
        
        .epic-status-badge.in-progress {{
            background: rgba(0, 120, 212, 0.15);
            color: var(--fluent-primary);
        }}
        
        .epic-status-badge.blocked {{
            background: rgba(209, 52, 56, 0.15);
            color: var(--fluent-red);
        }}
        
        .epic-progress {{
            width: 80px;
            flex-shrink: 0;
        }}
        
        /* Progress Bar */
        .progress-bar {{
            height: 6px;
            background: var(--fluent-gray-30);
            border-radius: 3px;
            overflow: hidden;
            position: relative;
        }}
        
        .progress-fill {{
            height: 100%;
            background: var(--fluent-primary);
            border-radius: 3px;
            transition: width var(--duration-2) var(--ease-1);
        }}
        
        .progress-bar.progress-complete .progress-fill {{
            background: var(--fluent-green);
        }}
        
        .progress-bar.progress-partial .progress-fill {{
            background: var(--fluent-orange);
        }}
        
        .progress-bar.progress-none .progress-fill {{
            background: var(--fluent-gray-50);
        }}
        
        .progress-text {{
            position: absolute;
            right: 0;
            top: -16px;
            font-size: 10px;
            color: var(--text-muted);
        }}
        
        /* Epic Children */
        .epic-children {{
            border-top: 1px solid var(--border);
            padding: 8px 12px 12px 32px;
            background: var(--fluent-gray-10);
        }}
        
        .epic-children.collapsed {{
            display: none;
        }}
        
        .epic-children .card {{
            margin-bottom: 8px;
            font-size: 12px;
        }}
        
        .epic-children .card:last-child {{
            margin-bottom: 0;
        }}
        
        .epic-children .card-title {{
            font-size: 12px;
            -webkit-line-clamp: 1;
        }}
        
        /* Orphans Section */
        .orphans-section {{
            background: var(--card-bg);
            border-radius: 4px;
            box-shadow: var(--shadow-sm);
            margin-bottom: 12px;
            border-left: 3px solid var(--fluent-gray-90);
            overflow: hidden;
        }}
        
        .orphans-header {{
            display: flex;
            align-items: center;
            padding: 10px 12px;
            cursor: pointer;
            gap: 10px;
            font-size: 12px;
            color: var(--text-muted);
            transition: background var(--duration-1) var(--ease-1);
        }}
        
        .orphans-header:hover {{
            background: var(--fluent-gray-20);
        }}
        
        .orphans-title {{
            font-weight: 500;
            flex: 1;
        }}
        
        .orphans-count {{
            font-size: 11px;
        }}
        
        .orphans-children {{
            border-top: 1px solid var(--border);
            padding: 8px 12px 12px 32px;
            background: var(--fluent-gray-10);
        }}
        
        .orphans-children.collapsed {{
            display: none;
        }}
        
        /* View Toggle */
        .view-toggle {{
            display: flex;
            align-items: center;
            gap: 4px;
            margin-left: 12px;
        }}
        
        .view-btn {{
            padding: 6px 12px;
            border: 1px solid var(--border);
            background: var(--card-bg);
            color: var(--text-muted);
            font-size: 12px;
            cursor: pointer;
            transition: all var(--duration-1) var(--ease-1);
        }}
        
        .view-btn:first-child {{
            border-radius: 4px 0 0 4px;
        }}
        
        .view-btn:last-child {{
            border-radius: 0 4px 4px 0;
            border-left: none;
        }}
        
        .view-btn.active {{
            background: var(--fluent-primary);
            border-color: var(--fluent-primary);
            color: white;
        }}
        
        .view-btn:hover:not(.active) {{
            background: var(--fluent-gray-20);
            color: var(--text);
        }}
        
        .terminal-btn, .session-btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
            padding: 0 12px;
            height: 28px;
            font-size: 12px;
            font-weight: 600;
            font-family: inherit;
            border-radius: 2px;
            border: 1px solid var(--border-strong);
            background: var(--card-bg);
            color: var(--text);
            cursor: pointer;
            transition: background var(--duration-1) var(--ease-1), 
                        border-color var(--duration-1) var(--ease-1);
        }}
        
        .terminal-btn:hover, .session-btn:hover {{
            background: var(--fluent-gray-20);
        }}
        
        .terminal-btn.danger, .session-btn.danger {{
            border-color: var(--fluent-red);
            color: var(--fluent-red);
        }}
        
        .terminal-btn.danger:hover, .session-btn.danger:hover {{
            background: rgba(209, 52, 56, 0.1);
        }}
        
        .session-btn.primary {{
            background: var(--fluent-primary);
            border-color: var(--fluent-primary);
            color: #ffffff;
        }}
        
        .session-btn.primary:hover {{
            background: var(--fluent-primary-dark);
            border-color: var(--fluent-primary-dark);
        }}
        
        .session-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        
        /* === TERMINAL STYLES === */
        .terminal-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 2px;
            background: var(--fluent-primary-lighter);
            color: var(--fluent-primary-darker);
            cursor: pointer;
            transition: background var(--duration-1) var(--ease-1);
        }}
        
        [data-theme="dark"] .terminal-indicator {{
            background: rgba(40, 153, 245, 0.2);
            color: var(--fluent-primary-light);
        }}
        
        .terminal-indicator:hover {{
            background: var(--fluent-gray-40);
        }}
        
        .terminal-indicator .pulse {{
            width: 6px;
            height: 6px;
            background: var(--fluent-green);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.4; }}
        }}
        
        .terminal-drawer {{
            display: none;
            margin-top: 12px;
            border-top: 1px solid var(--border);
            padding-top: 12px;
        }}
        
        .terminal-drawer.open {{
            display: block;
        }}
        
        .terminal-container {{
            background: #000000;
            border-radius: 4px;
            padding: 8px;
            height: 300px;
            overflow: hidden;
            position: relative;
        }}
        
        .terminal-container .xterm {{
            height: 100%;
        }}
        
        .terminal-controls {{
            display: flex;
            gap: 8px;
            margin-top: 8px;
            flex-wrap: wrap;
        }}
        
        .terminal-status {{
            font-size: 11px;
            color: var(--text-muted);
            margin-left: auto;
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        
        .terminal-status.connected {{
            color: var(--fluent-green);
        }}
        
        .terminal-status.disconnected {{
            color: var(--fluent-red);
        }}
        
        /* === SESSION STATUS === */
        .session-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 2px;
        }}
        
        .session-indicator.running {{
            background: rgba(16, 124, 16, 0.15);
            color: var(--fluent-green);
        }}
        
        .session-indicator.stuck {{
            background: rgba(255, 185, 0, 0.15);
            color: var(--fluent-yellow);
        }}
        
        .session-indicator.spawning {{
            background: rgba(0, 120, 212, 0.15);
            color: var(--fluent-primary);
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
            font-family: "Consolas", "Courier New", monospace;
            font-size: 11px;
            color: var(--text-muted);
            margin-left: 4px;
        }}
        
        .session-actions {{
            display: flex;
            gap: 6px;
            margin-top: 8px;
            flex-wrap: wrap;
        }}
        
        .session-info {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px dashed var(--border);
        }}
        
        /* === MODAL === */
        .terminal-modal {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.85);
            z-index: 1000;
            padding: 16px;
        }}
        
        .terminal-modal.open {{
            display: flex;
            flex-direction: column;
        }}
        
        .terminal-modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px;
            color: #ffffff;
            margin-bottom: 8px;
        }}
        
        .terminal-modal-content {{
            flex: 1;
            background: #000000;
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .terminal-modal .xterm {{
            height: 100%;
        }}
        
        /* === FOCUS STYLES (Accessibility) === */
        :focus-visible {{
            outline: none;
            box-shadow: 0 0 0 2px var(--card-bg), 0 0 0 4px var(--fluent-primary);
        }}
        
        /* === REDUCED MOTION === */
        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{
                animation-duration: 0.01ms !important;
                transition-duration: 0.01ms !important;
            }}
        }}
        
        /* === HIGH CONTRAST === */
        @media (prefers-contrast: high) {{
            .card, .column {{
                border-width: 2px;
            }}
            .terminal-btn, .session-btn {{
                border-width: 2px;
            }}
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
                    btn.setAttribute('data-active', isDark);
                    btn.title = isDark ? 'Switch to light mode' : 'Switch to dark mode';
                    btn.setAttribute('aria-pressed', isDark);
                }}
            }}
        }};
        
        // Initialize immediately to prevent flash
        ThemeController.init();
    </script>
</head>
<body>
    <header>
        <h1>◇ Speckle Board</h1>
        <div class="controls">
            <div class="view-toggle">
                <button class="view-btn" id="view-flat" onclick="setViewMode('flat')" title="Flat view">☰ Flat</button>
                <button class="view-btn" id="view-epic" onclick="setViewMode('epic')" title="Epic view">◇ Epics</button>
            </div>
            {filter_html}
            <span class="refresh-badge">↻ {refresh}s</span>
            <button class="theme-toggle" onclick="ThemeController.toggle()" title="Toggle dark mode" aria-label="Toggle dark mode"></button>
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
        
        // === Smart Auto-Refresh ===
        // Only refresh when no terminal drawer is open and no modal is showing
        const AutoRefresh = {{
            interval: {refresh} * 1000,
            timer: null,
            
            start() {{
                this.stop();
                this.timer = setTimeout(() => this.refresh(), this.interval);
            }},
            
            stop() {{
                if (this.timer) {{
                    clearTimeout(this.timer);
                    this.timer = null;
                }}
            }},
            
            refresh() {{
                // Don't refresh if terminal drawer is open
                const openDrawer = document.querySelector('.terminal-drawer.open');
                if (openDrawer) {{
                    console.log('Auto-refresh paused: terminal drawer open');
                    this.start(); // Schedule next check
                    return;
                }}
                
                // Don't refresh if modal is open
                const openModal = document.querySelector('.terminal-modal.open');
                if (openModal) {{
                    console.log('Auto-refresh paused: terminal modal open');
                    this.start();
                    return;
                }}
                
                // Don't refresh if WebSocket is connected with active data
                if (TerminalController.connected && Object.keys(TerminalController.terminals).length > 0) {{
                    console.log('Auto-refresh paused: terminal connected');
                    this.start();
                    return;
                }}
                
                // Safe to refresh
                window.location.reload();
            }}
        }};
        
        // Start auto-refresh after page load
        document.addEventListener('DOMContentLoaded', () => {{
            AutoRefresh.start();
        }});
        
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
        
        // === Epic View Controller ===
        const EpicController = {{
            STORAGE_KEY: 'speckle-view-mode',
            EXPANDED_KEY: 'speckle-expanded-epics',
            
            getViewMode() {{
                // URL param takes priority
                const url = new URL(window.location);
                const urlView = url.searchParams.get('view');
                if (urlView) return urlView;
                // Fall back to localStorage
                return localStorage.getItem(this.STORAGE_KEY) || 'flat';
            }},
            
            setViewMode(mode) {{
                localStorage.setItem(this.STORAGE_KEY, mode);
                const url = new URL(window.location);
                if (mode === 'flat') {{
                    url.searchParams.delete('view');
                }} else {{
                    url.searchParams.set('view', mode);
                }}
                window.location = url;
            }},
            
            getExpandedEpics() {{
                try {{
                    const stored = localStorage.getItem(this.EXPANDED_KEY);
                    return stored ? JSON.parse(stored) : {{}};
                }} catch {{
                    return {{}};
                }}
            }},
            
            setEpicExpanded(epicId, expanded) {{
                const state = this.getExpandedEpics();
                state[epicId] = expanded;
                localStorage.setItem(this.EXPANDED_KEY, JSON.stringify(state));
            }},
            
            toggleEpic(epicId) {{
                const card = document.querySelector(`[data-epic-id="${{epicId}}"]`);
                if (!card) return;
                
                const isExpanded = card.classList.toggle('expanded');
                this.setEpicExpanded(epicId, isExpanded);
                
                // Update chevron
                const chevron = card.querySelector('.expand-icon');
                if (chevron) {{
                    chevron.textContent = isExpanded ? '▼' : '▶';
                }}
                
                // Toggle children visibility
                const children = card.querySelector('.epic-children');
                if (children) {{
                    children.classList.toggle('collapsed', !isExpanded);
                    children.classList.toggle('expanded', isExpanded);
                }}
            }},
            
            toggleOrphans() {{
                const section = document.querySelector('.orphans-section');
                if (!section) return;
                
                const isExpanded = section.classList.toggle('expanded');
                localStorage.setItem('speckle-orphans-expanded', isExpanded);
                
                // Update chevron
                const chevron = section.querySelector('.expand-icon');
                if (chevron) {{
                    chevron.textContent = isExpanded ? '▼' : '▶';
                }}
                
                // Toggle children visibility
                const children = section.querySelector('.orphans-children');
                if (children) {{
                    children.classList.toggle('collapsed', !isExpanded);
                    children.classList.toggle('expanded', isExpanded);
                }}
            }},
            
            initViewMode() {{
                const mode = this.getViewMode();
                
                // Update button states
                const flatBtn = document.getElementById('view-flat');
                const epicBtn = document.getElementById('view-epic');
                
                if (flatBtn) flatBtn.classList.toggle('active', mode === 'flat');
                if (epicBtn) epicBtn.classList.toggle('active', mode === 'epic');
                
                // Restore expanded state for epics
                const expandedEpics = this.getExpandedEpics();
                document.querySelectorAll('[data-epic-id]').forEach(card => {{
                    const epicId = card.dataset.epicId;
                    if (expandedEpics[epicId]) {{
                        card.classList.add('expanded');
                        const chevron = card.querySelector('.expand-icon');
                        if (chevron) chevron.textContent = '▼';
                        const children = card.querySelector('.epic-children');
                        if (children) {{
                            children.classList.remove('collapsed');
                            children.classList.add('expanded');
                        }}
                    }}
                }});
                
                // Restore orphans expanded state
                const orphansExpanded = localStorage.getItem('speckle-orphans-expanded') === 'true';
                const orphansSection = document.querySelector('.orphans-section');
                if (orphansSection && orphansExpanded) {{
                    orphansSection.classList.add('expanded');
                    const chevron = orphansSection.querySelector('.expand-icon');
                    if (chevron) chevron.textContent = '▼';
                    const children = orphansSection.querySelector('.orphans-children');
                    if (children) {{
                        children.classList.remove('collapsed');
                        children.classList.add('expanded');
                    }}
                }}
            }}
        }};
        
        // Global functions for onclick handlers
        function setViewMode(mode) {{
            EpicController.setViewMode(mode);
        }}
        
        function toggleEpic(epicId) {{
            EpicController.toggleEpic(epicId);
        }}
        
        function toggleOrphans() {{
            EpicController.toggleOrphans();
        }}
        
        // Initialize Epic View on page load
        document.addEventListener('DOMContentLoaded', () => {{
            EpicController.initViewMode();
        }});
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
            # No active session - sessions auto-start via daemon when bead goes in_progress
            session_html = '''
        <div style="margin-top: 0.5rem; font-size: 0.65rem; color: var(--text-muted);">
            No active session
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
    
    # Fluent-style titles (no emoji icons - using left border accent instead)
    titles = {
        'open': 'Backlog',
        'in_progress': 'In Progress',
        'blocked': 'Blocked',
        'closed': 'Done'
    }
    
    title = titles.get(status, status.replace('_', ' ').title())
    count = len(issues)
    
    if issues:
        cards_html = ''.join(render_card(issue, terminals, sessions) for issue in issues)
    else:
        cards_html = '<div class="empty">No issues</div>'
    
    return f'''
    <div class="column {status}">
        <div class="column-header">
            <span class="column-title">{title}</span>
            <span class="column-count">{count}</span>
        </div>
        <div class="cards">
            {cards_html}
        </div>
    </div>
    '''


# === Epic View Mode Rendering (gh-59) ===

def render_progress_bar(percent: int, size: str = 'normal') -> str:
    """Render a progress bar with percentage."""
    filled = int(percent / 10)
    empty = 10 - filled
    
    bar_class = 'progress-bar' if size == 'normal' else 'progress-bar-small'
    
    # Color based on progress
    if percent == 100:
        color_class = 'progress-complete'
    elif percent >= 50:
        color_class = 'progress-good'
    elif percent > 0:
        color_class = 'progress-partial'
    else:
        color_class = 'progress-none'
    
    return f'''<div class="{bar_class} {color_class}">
        <div class="progress-fill" style="width: {percent}%"></div>
        <span class="progress-text">{percent}%</span>
    </div>'''


def render_epic_card(epic: Dict[str, Any], terminals: Dict[str, Any], sessions: Dict[str, Any]) -> str:
    """Render an epic card with collapsible children."""
    epic_id = epic.get('id', 'unknown')
    title = epic.get('title', 'Untitled').replace('Epic: ', '')
    progress = epic.get('progress', {})
    children = epic.get('children', [])
    expanded = epic.get('expanded', False)
    priority = epic.get('priority', 4)
    
    # Priority styling
    p_class = f'p{priority}' if priority <= 4 else 'p4'
    
    # Progress stats
    total = progress.get('total', 0)
    closed = progress.get('closed', 0)
    percent = progress.get('percent', 0)
    in_progress_count = progress.get('in_progress', 0)
    blocked_count = progress.get('blocked', 0)
    
    # Expand/collapse state
    expand_icon = '▼' if expanded else '▶'
    expanded_class = 'expanded' if expanded else 'collapsed'
    
    # Status indicators
    status_badges = []
    if in_progress_count > 0:
        status_badges.append(f'<span class="epic-status-badge in-progress">{in_progress_count} active</span>')
    if blocked_count > 0:
        status_badges.append(f'<span class="epic-status-badge blocked">{blocked_count} blocked</span>')
    status_html = ' '.join(status_badges)
    
    # Render children cards
    children_html = ''
    if children:
        for child in children:
            children_html += render_card(child, terminals, sessions)
    else:
        children_html = '<div class="empty">No tasks</div>'
    
    return f'''
    <div class="epic-card {p_class}" data-epic-id="{epic_id}">
        <div class="epic-header" onclick="toggleEpic('{epic_id}')">
            <span class="expand-icon">{expand_icon}</span>
            <div class="epic-info">
                <span class="epic-title">{title}</span>
                <div class="epic-meta">
                    <span class="epic-count">{closed}/{total} tasks</span>
                    {status_html}
                </div>
            </div>
            <div class="epic-progress">
                {render_progress_bar(percent)}
            </div>
        </div>
        <div class="epic-children {expanded_class}" id="epic-children-{epic_id}">
            {children_html}
        </div>
    </div>
    '''


def render_orphans_section(orphans: List[Dict[str, Any]], terminals: Dict[str, Any], sessions: Dict[str, Any]) -> str:
    """Render the uncategorized/orphan tasks section."""
    if not orphans:
        return ''
    
    count = len(orphans)
    cards_html = ''.join(render_card(orphan, terminals, sessions) for orphan in orphans)
    
    return f'''
    <div class="orphans-section">
        <div class="orphans-header" onclick="toggleOrphans()">
            <span class="expand-icon" id="orphans-expand-icon">▶</span>
            <span class="orphans-title">Uncategorized</span>
            <span class="orphans-count">{count} tasks</span>
        </div>
        <div class="orphans-children collapsed" id="orphans-children">
            {cards_html}
        </div>
    </div>
    '''


def render_column_epic_view(status: str, column_data: Dict[str, List], 
                            terminals: Dict[str, Any], sessions: Dict[str, Any]) -> str:
    """Render a kanban column in epic view mode."""
    titles = {
        'open': 'Backlog',
        'in_progress': 'In Progress',
        'blocked': 'Blocked',
        'closed': 'Done'
    }
    
    title = titles.get(status, status.replace('_', ' ').title())
    epics = column_data.get('epics', [])
    orphans = column_data.get('orphans', [])
    
    # Count total items (epics + orphans)
    count = len(epics) + len(orphans)
    
    # Render epic cards
    epics_html = ''
    for epic in epics:
        epics_html += render_epic_card(epic, terminals, sessions)
    
    # Render orphans section
    orphans_html = render_orphans_section(orphans, terminals, sessions) if orphans else ''
    
    if not epics_html and not orphans_html:
        content_html = '<div class="empty">No issues</div>'
    else:
        content_html = epics_html + orphans_html
    
    return f'''
    <div class="column {status}">
        <div class="column-header">
            <span class="column-title">{title}</span>
            <span class="column-count">{count}</span>
        </div>
        <div class="cards epic-view">
            {content_html}
        </div>
    </div>
    '''


def render_board(issues: List[Dict[str, Any]], label_filter: Optional[str] = None,
                 refresh: int = DEFAULT_REFRESH, ws_port: int = TERMINAL_WS_PORT,
                 epic_view: bool = False) -> str:
    """Render the full board as HTML.
    
    Args:
        issues: List of issue dictionaries
        label_filter: Optional label to filter by
        refresh: Auto-refresh interval in seconds
        ws_port: WebSocket port for terminal server
        epic_view: If True, render in epic/hierarchy view mode
    """
    all_labels = get_all_labels(issues)
    
    # Get active terminal sessions
    terminals = get_active_terminals()
    
    # Get Claude session info
    sessions = get_sessions_info()
    
    # Build columns HTML based on view mode
    columns_html = ''
    
    if epic_view:
        # Epic view: group by hierarchy
        hierarchy = get_issues_with_hierarchy(issues)
        columns = group_by_status_hierarchical(hierarchy)
        for status in ['open', 'in_progress', 'blocked', 'closed']:
            columns_html += render_column_epic_view(status, columns[status], terminals, sessions)
    else:
        # Flat view: traditional kanban
        columns = group_by_status(issues)
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
    if epic_view:
        hierarchy = get_issues_with_hierarchy(issues)
        issue_count = len(hierarchy['epics']) + len(hierarchy['orphans'])
    else:
        issue_count = len(issues)
    
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
            
            # Check for epic view mode
            epic_view = query.get('view', ['flat'])[0] == 'epic'
            
            issues = get_issues(label_filter)
            
            # T023: Merge GitHub links if enabled
            if self.show_github:
                github_links = load_github_links()
                issues = merge_github_links(issues, github_links)
            
            html = render_board(issues, label_filter, self.refresh, self.ws_port, epic_view)
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        
        elif parsed.path == '/api/epics':
            # Return epics with hierarchy and progress (gh-59)
            issues = get_issues()
            hierarchy = get_issues_with_hierarchy(issues)
            
            # Format epics for API response
            epics_response = []
            for epic_id, epic in hierarchy['epics'].items():
                epics_response.append({
                    'id': epic_id,
                    'title': epic.get('title', ''),
                    'status': epic.get('status', 'open'),
                    'priority': epic.get('priority', 4),
                    'progress': epic.get('progress', {}),
                    'children_count': len(epic.get('children', [])),
                    'expanded': epic.get('expanded', False)
                })
            
            response = {
                'epics': epics_response,
                'orphan_count': len(hierarchy['orphans'])
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
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


def start_terminal_server(ws_port: int) -> Optional[subprocess.Popen]:
    """Start terminal server as background process."""
    import socket
    
    # Check if port is already in use
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('localhost', ws_port))
        sock.close()
    except OSError:
        # Port in use - server might already be running
        return None
    
    # Find terminal_server.py
    terminal_server = SCRIPTS_DIR / "terminal_server.py"
    if not terminal_server.exists():
        return None
    
    # Check if websockets is available
    try:
        import websockets
    except ImportError:
        return None
    
    # Start server in background
    try:
        proc = subprocess.Popen(
            [sys.executable, str(terminal_server), "server", "--port", str(ws_port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        # Give it a moment to start
        import time
        time.sleep(0.3)
        if proc.poll() is None:
            return proc
    except Exception:
        pass
    
    return None


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
    parser.add_argument('--no-terminal-server', action='store_true',
                        help="Don't auto-start terminal server")
    args = parser.parse_args()
    
    # Configure handler
    BoardHandler.label_filter = args.filter
    BoardHandler.refresh = args.refresh
    BoardHandler.show_github = args.github
    BoardHandler.ws_port = args.ws_port
    
    # Auto-start terminal server
    terminal_proc = None
    terminal_status = "disabled"
    if not args.no_terminal_server:
        terminal_proc = start_terminal_server(args.ws_port)
        if terminal_proc:
            terminal_status = "✓ auto-started"
        else:
            # Check if already running by trying to connect
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect(('localhost', args.ws_port))
                sock.close()
                terminal_status = "✓ already running"
            except (ConnectionRefusedError, OSError):
                terminal_status = "✗ unavailable (install websockets)"
    
    # Start server
    server = http.server.HTTPServer(('localhost', args.port), BoardHandler)
    
    url = f'http://localhost:{args.port}'
    if args.filter:
        url += f'?filter={urllib.parse.quote(args.filter)}'
    
    github_status = '✓ enabled' if args.github else '(disabled)'
    
    # Check active terminals
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
   Server:    {terminal_status}
   Active:    {terminal_count} session(s)
════════════════════════════════════════
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
        # Stop terminal server if we started it
        if terminal_proc and terminal_proc.poll() is None:
            terminal_proc.terminate()
            try:
                terminal_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                terminal_proc.kill()


if __name__ == '__main__':
    main()
