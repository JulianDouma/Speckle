#!/usr/bin/env python3
"""
Speckle Session Daemon

Watches for bead status changes and automatically:
- Spawns sessions when beads go to in_progress
- Terminates sessions when beads are closed/blocked

Run: python session_daemon.py [--watch] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Set, Optional, Any

# Import session manager
from session_manager import (
    session_manager,
    SessionState,
    PROJECT_ROOT,
    SESSIONS_DIR,
)


# Configuration
ISSUES_FILE = PROJECT_ROOT / ".beads/issues.jsonl"
WATCH_INTERVAL = 2  # seconds
AUTO_SPAWN_ENABLED = True
AUTO_TERMINATE_ENABLED = True


def load_issues() -> Dict[str, Dict[str, Any]]:
    """Load all issues from issues.jsonl."""
    issues = {}
    if not ISSUES_FILE.exists():
        return issues
    
    try:
        with open(ISSUES_FILE) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        issue = json.loads(line)
                        issue_id = issue.get("id")
                        if issue_id:
                            issues[issue_id] = issue
                    except json.JSONDecodeError:
                        continue
    except IOError as e:
        print(f"Error reading issues file: {e}")
    
    return issues


def get_in_progress_beads(issues: Dict[str, Dict[str, Any]]) -> Set[str]:
    """Get IDs of beads with in_progress status."""
    return {
        issue_id
        for issue_id, issue in issues.items()
        if issue.get("status") == "in_progress"
    }


def get_closed_beads(issues: Dict[str, Dict[str, Any]]) -> Set[str]:
    """Get IDs of beads with closed/done/blocked/blocking status."""
    closed_statuses = {"closed", "done", "blocked", "blocking", "cancelled", "wontfix"}
    return {
        issue_id
        for issue_id, issue in issues.items()
        if issue.get("status") in closed_statuses
    }


def sync_sessions(dry_run: bool = False, verbose: bool = True) -> Dict[str, str]:
    """
    Sync sessions with current bead statuses.
    
    Returns dict of actions taken: {bead_id: action}
    """
    actions = {}
    issues = load_issues()
    
    in_progress = get_in_progress_beads(issues)
    closed = get_closed_beads(issues)
    
    # Get current sessions
    active_sessions = {s.bead_id for s in session_manager.list_sessions(active_only=True)}
    
    # Spawn sessions for in_progress beads without sessions
    if AUTO_SPAWN_ENABLED:
        need_spawn = in_progress - active_sessions
        for bead_id in need_spawn:
            issue = issues.get(bead_id, {})
            title = issue.get("title", "Unknown")
            
            if verbose:
                print(f"  → Spawning session for {bead_id}: {title[:50]}")
            
            if not dry_run:
                session = session_manager.spawn_session(bead_id)
                if session:
                    actions[bead_id] = "spawned"
                else:
                    actions[bead_id] = "spawn_failed"
            else:
                actions[bead_id] = "would_spawn"
    
    # Terminate sessions for closed/blocked beads
    if AUTO_TERMINATE_ENABLED:
        need_terminate = active_sessions & closed
        for bead_id in need_terminate:
            if verbose:
                print(f"  ← Terminating session for {bead_id}")
            
            if not dry_run:
                if session_manager.terminate_session(bead_id):
                    actions[bead_id] = "terminated"
                else:
                    actions[bead_id] = "terminate_failed"
            else:
                actions[bead_id] = "would_terminate"
    
    return actions


def watch_loop(dry_run: bool = False, verbose: bool = True):
    """Watch for changes and sync sessions."""
    print(f"🔄 Session daemon started (watching every {WATCH_INTERVAL}s)")
    print(f"   Project root: {PROJECT_ROOT}")
    print(f"   Issues file: {ISSUES_FILE}")
    print(f"   Sessions dir: {SESSIONS_DIR}")
    print(f"   Dry run: {dry_run}")
    print()
    
    last_mtime = 0
    
    try:
        while True:
            # Check if issues file changed
            if ISSUES_FILE.exists():
                mtime = ISSUES_FILE.stat().st_mtime
                if mtime > last_mtime:
                    if last_mtime > 0:  # Not first run
                        print(f"\n[{datetime.now(timezone.utc).isoformat()}] Issues file changed")
                    
                    actions = sync_sessions(dry_run=dry_run, verbose=verbose)
                    
                    if actions:
                        print(f"   Actions: {len(actions)}")
                    
                    last_mtime = mtime
            
            time.sleep(WATCH_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n✓ Session daemon stopped")


def one_shot(dry_run: bool = False, verbose: bool = True):
    """Run sync once and exit."""
    print("📋 Running one-shot session sync")
    print()
    
    actions = sync_sessions(dry_run=dry_run, verbose=verbose)
    
    if actions:
        print()
        print("Summary:")
        for bead_id, action in sorted(actions.items()):
            print(f"  {bead_id}: {action}")
    else:
        print("  No actions needed")
    
    return len(actions)


def status_report():
    """Print current status of sessions and beads."""
    print("📊 Session Status Report")
    print()
    
    # Load issues
    issues = load_issues()
    in_progress = get_in_progress_beads(issues)
    
    print(f"In-progress beads: {len(in_progress)}")
    for bead_id in sorted(in_progress):
        issue = issues.get(bead_id, {})
        title = issue.get("title", "Unknown")
        print(f"  ◐ {bead_id}: {title[:50]}")
    
    print()
    
    # Sessions
    sessions = session_manager.list_sessions()
    active = [s for s in sessions if s.is_active]
    completed = [s for s in sessions if s.state == SessionState.COMPLETED]
    failed = [s for s in sessions if s.state == SessionState.FAILED]
    
    print(f"Active sessions: {len(active)}")
    for s in active:
        status_icon = "🟢" if s.state == SessionState.RUNNING else "🟡"
        print(f"  {status_icon} {s.bead_id}: {s.title[:40]} (pid: {s.pid})")
    
    print()
    print(f"Completed sessions: {len(completed)}")
    print(f"Failed sessions: {len(failed)}")
    
    # Check sync status
    print()
    active_ids = {s.bead_id for s in active}
    missing = in_progress - active_ids
    orphaned = active_ids - in_progress
    
    if missing:
        print(f"⚠️  Missing sessions (in_progress without session):")
        for bead_id in missing:
            print(f"     {bead_id}")
    
    if orphaned:
        print(f"⚠️  Orphaned sessions (session without in_progress bead):")
        for bead_id in orphaned:
            print(f"     {bead_id}")
    
    if not missing and not orphaned:
        print("✓ Sessions are in sync")


def main():
    parser = argparse.ArgumentParser(
        description="Speckle Session Daemon - auto-spawn/terminate Claude sessions"
    )
    subparsers = parser.add_subparsers(dest="command")
    
    # Watch command (continuous monitoring)
    watch_parser = subparsers.add_parser("watch", help="Watch for changes continuously")
    watch_parser.add_argument("--dry-run", action="store_true", help="Don't actually spawn/terminate")
    watch_parser.add_argument("--quiet", action="store_true", help="Less verbose output")
    
    # Sync command (one-shot)
    sync_parser = subparsers.add_parser("sync", help="Sync sessions once and exit")
    sync_parser.add_argument("--dry-run", action="store_true", help="Don't actually spawn/terminate")
    sync_parser.add_argument("--quiet", action="store_true", help="Less verbose output")
    
    # Status command
    subparsers.add_parser("status", help="Show current session status")
    
    args = parser.parse_args()
    
    if args.command == "watch":
        watch_loop(dry_run=args.dry_run, verbose=not args.quiet)
    
    elif args.command == "sync":
        actions = one_shot(dry_run=args.dry_run, verbose=not args.quiet)
        sys.exit(0 if actions >= 0 else 1)
    
    elif args.command == "status":
        status_report()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
