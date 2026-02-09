#!/usr/bin/env python3
"""
Speckle CLI - Unified command-line interface for Speckle tools

Usage:
    speckle board [--port PORT]     Start kanban board server
    speckle doctor [--fix]          Run diagnostic checks
    speckle gh [--all] [--limit N]  List GitHub issues (epic colors, priority icons)
    speckle status                  Show feature progress (via bd)
    speckle sync                    Sync beads with git (via bd)
    speckle --help                  Show this help message
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def get_speckle_root() -> Path:
    """Find the .speckle directory, searching up from cwd or using script location."""
    # First, try searching up from current directory
    current = Path.cwd()
    while current != current.parent:
        if (current / '.speckle').is_dir():
            return current / '.speckle'
        current = current.parent
    
    # Fallback: use the directory containing this script (cli.py is in .speckle/)
    script_dir = Path(__file__).resolve().parent
    if script_dir.name == '.speckle' or (script_dir / 'scripts').is_dir():
        return script_dir
    
    # Last resort: maybe script is in .speckle/scripts/
    if script_dir.parent.name == '.speckle':
        return script_dir.parent
    
    # Give up - return cwd/.speckle and let the caller handle the error
    return Path.cwd() / '.speckle'


def cmd_board(args):
    """Start the kanban board server."""
    speckle_root = get_speckle_root()
    board_script = speckle_root / 'scripts' / 'board.py'
    
    if not board_script.exists():
        print(f"Error: board.py not found at {board_script}", file=sys.stderr)
        return 1
    
    cmd = [sys.executable, str(board_script)]
    if args.port:
        cmd.extend(['--port', str(args.port)])
    if args.no_browser:
        cmd.append('--no-browser')
    
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        # board.py already printed goodbye message
        return 0


def cmd_doctor(args):
    """Run diagnostic checks."""
    speckle_root = get_speckle_root()
    doctor_script = speckle_root / 'scripts' / 'doctor.py'
    
    if not doctor_script.exists():
        print(f"Error: doctor.py not found at {doctor_script}", file=sys.stderr)
        return 1
    
    cmd = [sys.executable, str(doctor_script)]
    if args.fix:
        cmd.append('--fix')
    if args.verbose:
        cmd.append('--verbose')
    
    return subprocess.call(cmd)


def cmd_status(args):
    """Show feature progress via beads."""
    cmd = ['bd', 'list']
    if args.all:
        cmd.append('--all')
    return subprocess.call(cmd)


def cmd_sync(args):
    """Sync beads with git."""
    return subprocess.call(['bd', 'sync'])


def cmd_ready(args):
    """Show ready work items."""
    return subprocess.call(['bd', 'ready'])


def cmd_version(args):
    """Show version information."""
    speckle_root = get_speckle_root()
    # Check in .speckle/ first, then parent directory
    version_file = speckle_root / 'VERSION'
    if not version_file.exists():
        version_file = speckle_root.parent / 'VERSION'
    
    if version_file.exists():
        version = version_file.read_text().strip()
    else:
        version = "1.5.0"  # Default
    print(f"speckle {version}")
    return 0


def cmd_gh(args):
    """List GitHub issues with epic colors and priority icons."""
    import json
    
    # Priority icons (not colors)
    PRIORITY_ICONS = {
        'critical': '🔥',  # P0
        'high': '⚡',      # P1  
        'medium': '📌',    # P2
        'low': '📎',       # P3
    }
    
    # Epic colors (ANSI escape codes)
    EPIC_COLORS = [
        '\033[38;5;33m',   # Blue
        '\033[38;5;166m',  # Orange
        '\033[38;5;128m',  # Purple
        '\033[38;5;36m',   # Teal
        '\033[38;5;196m',  # Red
        '\033[38;5;220m',  # Yellow
        '\033[38;5;46m',   # Green
        '\033[38;5;201m',  # Magenta
    ]
    RESET = '\033[0m'
    DIM = '\033[2m'
    
    # Fetch issues from GitHub
    cmd = ['gh', 'issue', 'list', '--json', 'number,title,labels,state', '--limit', str(args.limit)]
    if args.all:
        cmd.extend(['--state', 'all'])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        issues = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error fetching issues: {e.stderr}", file=sys.stderr)
        return 1
    except json.JSONDecodeError:
        print("Error parsing GitHub response", file=sys.stderr)
        return 1
    
    if not issues:
        print("No issues found")
        return 0
    
    # Build epic color mapping
    epic_color_map = {}
    color_index = 0
    
    for issue in issues:
        for label in issue.get('labels', []):
            name = label.get('name', '')
            if name.startswith('epic:'):
                epic = name[5:]  # Remove 'epic:' prefix
                if epic not in epic_color_map:
                    epic_color_map[epic] = EPIC_COLORS[color_index % len(EPIC_COLORS)]
                    color_index += 1
    
    # Display issues
    print()
    for issue in issues:
        num = issue['number']
        title = issue['title']
        state = issue['state']
        labels = issue.get('labels', [])
        
        # Find epic and priority
        epic = None
        priority = None
        priority_icon = '  '  # Default: no icon (2 spaces for alignment)
        
        for label in labels:
            name = label.get('name', '')
            if name.startswith('epic:'):
                epic = name[5:]
            elif name.startswith('priority:'):
                priority = name[9:]
            elif name in ('critical', 'high', 'medium', 'low'):
                priority = name
            elif name.startswith('severity:'):
                priority = name[9:]
        
        # Get priority icon
        if priority and priority in PRIORITY_ICONS:
            priority_icon = PRIORITY_ICONS[priority]
        
        # Get epic color
        if epic and epic in epic_color_map:
            color = epic_color_map[epic]
        else:
            color = DIM  # No epic = dimmed
        
        # State indicator
        state_icon = '○' if state == 'OPEN' else '●'
        
        # Format output
        print(f"  {priority_icon} {color}#{num:<4}{RESET} {state_icon} {color}{title}{RESET}")
    
    # Legend
    if epic_color_map and not args.no_legend:
        print()
        print(f"  {DIM}─── Epics ───{RESET}")
        for epic, color in epic_color_map.items():
            print(f"  {color}■{RESET} {epic}")
        print()
        print(f"  {DIM}─── Priority ───{RESET}")
        for name, icon in PRIORITY_ICONS.items():
            print(f"  {icon} {name}")
    
    print()
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog='speckle',
        description='Speckle - AI-powered development workflow tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Commands:
  board       Start the kanban board web interface
  doctor      Run diagnostic checks on your Speckle installation
  gh          List GitHub issues (colored by epic, priority icons)
  status      Show current work status (via beads)
  sync        Sync beads issues with git
  ready       Show available work items
  version     Show version information

Examples:
  speckle board                    # Start board on default port 8420
  speckle board --port 3000        # Start board on port 3000
  speckle doctor --fix             # Run diagnostics and fix issues
  speckle gh                       # List GitHub issues with epic colors
  speckle gh --all --limit 50      # Show all issues including closed
  speckle status --all             # Show all issues including closed

For Claude commands, use:
  /speckle.implement               # Implement next task
  /speckle.progress "note"         # Add progress note
'''
    )
    
    parser.add_argument('--version', '-v', action='store_true', 
                        help='Show version and exit')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # board subcommand
    board_parser = subparsers.add_parser('board', help='Start kanban board server')
    board_parser.add_argument('--port', '-p', type=int, default=8420,
                              help='Port to run server on (default: 8420)')
    board_parser.add_argument('--no-browser', action='store_true',
                              help='Do not open browser automatically')
    board_parser.set_defaults(func=cmd_board)
    
    # doctor subcommand
    doctor_parser = subparsers.add_parser('doctor', help='Run diagnostic checks')
    doctor_parser.add_argument('--fix', '-f', action='store_true',
                               help='Attempt to fix issues automatically')
    doctor_parser.add_argument('--verbose', '-v', action='store_true',
                               help='Show detailed output')
    doctor_parser.set_defaults(func=cmd_doctor)
    
    # status subcommand
    status_parser = subparsers.add_parser('status', help='Show work status')
    status_parser.add_argument('--all', '-a', action='store_true',
                               help='Show all issues including closed')
    status_parser.set_defaults(func=cmd_status)
    
    # sync subcommand
    sync_parser = subparsers.add_parser('sync', help='Sync beads with git')
    sync_parser.set_defaults(func=cmd_sync)
    
    # ready subcommand
    ready_parser = subparsers.add_parser('ready', help='Show available work')
    ready_parser.set_defaults(func=cmd_ready)
    
    # version subcommand
    version_parser = subparsers.add_parser('version', help='Show version')
    version_parser.set_defaults(func=cmd_version)
    
    # gh subcommand
    gh_parser = subparsers.add_parser('gh', help='List GitHub issues (epic colors, priority icons)')
    gh_parser.add_argument('--all', '-a', action='store_true',
                           help='Show all issues including closed')
    gh_parser.add_argument('--limit', '-l', type=int, default=20,
                           help='Maximum issues to show (default: 20)')
    gh_parser.add_argument('--no-legend', action='store_true',
                           help='Hide the legend')
    gh_parser.set_defaults(func=cmd_gh)
    
    args = parser.parse_args()
    
    if args.version:
        return cmd_version(args)
    
    if not args.command:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        sys.exit(0)
