#!/usr/bin/env python3
"""
Speckle Kanban Board Server
Lightweight visualization of beads issues

Phase 1: Foundation (T001-T005)
Phase 2: UI Polish (T006-T010)
"""

import http.server
import json
import subprocess
import argparse
import urllib.parse
import webbrowser
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# === Configuration ===
DEFAULT_PORT = 8420
DEFAULT_REFRESH = 5
MAX_CLOSED = 15


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
        [data-theme="dark"] {{
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text: #e2e8f0;
            --text-muted: #94a3b8;
            --border: #334155;
            --header-gradient: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            
            /* Column backgrounds - darker variants */
            --backlog: #1e293b;
            --progress: #1e3a5f;
            --blocked: #451a1a;
            --done: #14532d;
            
            /* Shadows - more pronounced in dark mode */
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.3);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.4);
            --shadow-header: 0 2px 4px rgba(0,0,0,0.3);
            
            /* Badge backgrounds (dark mode - more contrast) */
            --badge-p0-bg: #450a0a;
            --badge-p0-text: #fca5a5;
            --badge-p2-bg: #451a03;
            --badge-p2-text: #fcd34d;
            --badge-p3-bg: #052e16;
            --badge-p3-text: #86efac;
            --type-bg: #334155;
            --type-bug-bg: #450a0a;
            --type-bug-text: #fca5a5;
            --type-feature-bg: #2e1065;
            --type-feature-text: #c4b5fd;
            --type-epic-bg: #431407;
            --type-epic-text: #fdba74;
            --label-bg: #312e81;
            --label-text: #c7d2fe;
            
            /* Column header border */
            --column-border: rgba(255,255,255,0.1);
        }}
        
        /* === T002: System preference detection (when no explicit choice) === */
        @media (prefers-color-scheme: dark) {{
            :root:not([data-theme]) {{
                --bg: #0f172a;
                --card-bg: #1e293b;
                --text: #e2e8f0;
                --text-muted: #94a3b8;
                --border: #334155;
                --header-gradient: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
                --backlog: #1e293b;
                --progress: #1e3a5f;
                --blocked: #451a1a;
                --done: #14532d;
                --shadow-sm: 0 1px 3px rgba(0,0,0,0.3);
                --shadow-md: 0 4px 6px rgba(0,0,0,0.4);
                --shadow-header: 0 2px 4px rgba(0,0,0,0.3);
                --badge-p0-bg: #450a0a;
                --badge-p0-text: #fca5a5;
                --badge-p2-bg: #451a03;
                --badge-p2-text: #fcd34d;
                --badge-p3-bg: #052e16;
                --badge-p3-text: #86efac;
                --type-bg: #334155;
                --type-bug-bg: #450a0a;
                --type-bug-text: #fca5a5;
                --type-feature-bg: #2e1065;
                --type-feature-text: #c4b5fd;
                --type-epic-bg: #431407;
                --type-epic-text: #fdba74;
                --label-bg: #312e81;
                --label-text: #c7d2fe;
                --column-border: rgba(255,255,255,0.1);
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
            background: var(--header-gradient);
            color: white;
            padding: 1rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: var(--shadow-header);
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
            background: rgba(255,255,255,0.2);
            border: none;
            font-size: 1.1rem;
            cursor: pointer;
            padding: 0.25rem 0.5rem;
            border-radius: 0.375rem;
            transition: background 0.2s;
            line-height: 1;
        }}
        
        .theme-toggle:hover {{
            background: rgba(255,255,255,0.3);
        }}
        
        .refresh-badge {{
            background: rgba(255,255,255,0.2);
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.75rem;
        }}
        
        .filter-select {{
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
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
    </style>
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
    
    <script>
        // Update toggle UI after DOM is ready
        document.addEventListener('DOMContentLoaded', () => {{
            ThemeController.updateToggleUI();
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


def render_card(issue: Dict[str, Any]) -> str:
    """Render a single issue card with priority, type, time, labels, and GitHub link."""
    issue_id = issue.get('id', 'unknown')
    title = issue.get('title', 'Untitled')
    priority = issue.get('priority', 4)
    issue_type = issue.get('issue_type', 'task')
    labels = issue.get('labels', [])
    created_at = issue.get('created_at', '')
    github_url = issue.get('github_url', '')
    
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
    </div>
    '''


def render_column(status: str, issues: List[Dict[str, Any]]) -> str:
    """Render a kanban column as HTML."""
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
        cards_html = ''.join(render_card(issue) for issue in issues)
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
                 refresh: int = DEFAULT_REFRESH) -> str:
    """Render the full board as HTML."""
    columns = group_by_status(issues)
    all_labels = get_all_labels(issues)
    
    # Build columns HTML
    columns_html = ''
    for status in ['open', 'in_progress', 'blocked', 'closed']:
        columns_html += render_column(status, columns[status])
    
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
        issue_count=issue_count
    )


class BoardHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for the kanban board."""
    
    label_filter: Optional[str] = None
    refresh: int = DEFAULT_REFRESH
    show_github: bool = False
    
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
            
            html = render_board(issues, label_filter, self.refresh)
            
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
            
        elif parsed.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            
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
    args = parser.parse_args()
    
    # Configure handler
    BoardHandler.label_filter = args.filter
    BoardHandler.refresh = args.refresh
    BoardHandler.show_github = args.github
    
    # Start server
    server = http.server.HTTPServer(('localhost', args.port), BoardHandler)
    
    url = f'http://localhost:{args.port}'
    if args.filter:
        url += f'?filter={urllib.parse.quote(args.filter)}'
    
    github_status = '✓ enabled' if args.github else '(disabled)'
    
    print(f'''
🔮 Speckle Board
════════════════════════════════════════
   URL:     {url}
   Refresh: {args.refresh}s
   Filter:  {args.filter or '(none)'}
   GitHub:  {github_status}
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


if __name__ == '__main__':
    main()
