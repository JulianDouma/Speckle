#!/usr/bin/env python3
"""
Speckle GitHub Integration

Provides bidirectional sync between beads issues and GitHub Issues.
Uses layered authentication: env var → gh CLI → config file.

Phase 2: Authentication (T008-T013)
Phase 3: Sync Operations (T014-T019)
"""

import os
import sys
import json
import subprocess
import argparse
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# === Configuration ===
GITHUB_API = "https://api.github.com"
LINKS_FILE = ".speckle/github-links.jsonl"
CONFIG_LOCATIONS = [
    Path.home() / ".speckle" / "config.toml",
    Path(".speckle") / "config.toml",
]


# === T014: Issue Linkage Data Model ===
@dataclass
class IssueLinkage:
    """Tracks relationship between beads and GitHub issues."""
    bead_id: str
    github_number: int
    github_url: str
    repo: str
    last_synced: str = ""
    sync_direction: str = "bead_to_gh"  # bead_to_gh | gh_to_bead
    
    def __post_init__(self):
        if not self.last_synced:
            self.last_synced = datetime.now(timezone.utc).isoformat()


# === T008: GitHub Authentication ===
@dataclass
class GitHubAuth:
    """Authentication credentials for GitHub API."""
    token: str
    source: str  # "env" | "gh_cli" | "config"
    
    def mask_token(self) -> str:
        """Return masked token for display."""
        if len(self.token) > 8:
            return f"{self.token[:4]}...{self.token[-4:]}"
        return "***"


class GitHubClient:
    """GitHub API client with layered authentication."""
    
    def __init__(self, auth: Optional[GitHubAuth] = None):
        self.auth = auth
        self._repo: Optional[str] = None
    
    @property
    def authenticated(self) -> bool:
        return self.auth is not None
    
    @property
    def repo(self) -> Optional[str]:
        """Get repository from config or git remote."""
        if self._repo:
            return self._repo
        
        # Try to detect from git remote
        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                # Parse github.com/owner/repo from various URL formats
                if 'github.com' in url:
                    # SSH: git@github.com:owner/repo.git
                    # HTTPS: https://github.com/owner/repo.git
                    parts = url.replace(':', '/').replace('.git', '').split('/')
                    if len(parts) >= 2:
                        self._repo = f"{parts[-2]}/{parts[-1]}"
                        return self._repo
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return None
    
    def api_request(self, endpoint: str, method: str = "GET", 
                    data: Optional[dict] = None) -> dict:
        """Make authenticated API request to GitHub."""
        if not self.auth:
            raise RuntimeError("Not authenticated")
        
        url = f"{GITHUB_API}{endpoint}"
        headers = {
            "Authorization": f"token {self.auth.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Speckle-GitHub-Integration",
        }
        
        body = json.dumps(data).encode() if data else None
        if body:
            headers["Content-Type"] = "application/json"
        
        req = Request(url, data=body, headers=headers, method=method)
        
        try:
            with urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            raise RuntimeError(f"GitHub API error {e.code}: {error_body}")
        except URLError as e:
            raise RuntimeError(f"Network error: {e.reason}")
    
    def get_issue(self, number: int) -> dict:
        """Fetch a single issue by number."""
        return self.api_request(f"/repos/{self.repo}/issues/{number}")
    
    def list_issues(self, state: str = "all", per_page: int = 100) -> List[Dict[str, Any]]:
        """List issues from the repository."""
        result = self.api_request(
            f"/repos/{self.repo}/issues?state={state}&per_page={per_page}"
        )
        return result if isinstance(result, list) else []
    
    def create_issue(self, title: str, body: str = "", 
                     labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a new issue."""
        data: Dict[str, Any] = {"title": title, "body": body}
        if labels:
            data["labels"] = labels
        return self.api_request(f"/repos/{self.repo}/issues", "POST", data)
    
    def update_issue(self, number: int, title: Optional[str] = None, 
                     body: Optional[str] = None, state: Optional[str] = None, 
                     labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Update an existing issue."""
        data: Dict[str, Any] = {}
        if title:
            data["title"] = title
        if body is not None:
            data["body"] = body
        if state:
            data["state"] = state
        if labels is not None:
            data["labels"] = labels
        return self.api_request(f"/repos/{self.repo}/issues/{number}", "PATCH", data)
    
    def get_rate_limit(self) -> dict:
        """Get current rate limit status."""
        return self.api_request("/rate_limit")


# === T009-T012: Layered Authentication ===
def get_token_from_env() -> Optional[GitHubAuth]:
    """T009: Get token from environment variable."""
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if token:
        return GitHubAuth(token=token, source="env")
    return None


def get_token_from_gh_cli() -> Optional[GitHubAuth]:
    """T010: Get token from gh CLI."""
    try:
        result = subprocess.run(
            ['gh', 'auth', 'token'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return GitHubAuth(token=result.stdout.strip(), source="gh_cli")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def get_token_from_config() -> Optional[GitHubAuth]:
    """T011: Get token from config file."""
    for config_path in CONFIG_LOCATIONS:
        if config_path.exists():
            try:
                content = config_path.read_text()
                # Simple TOML parsing for github.token
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('token') and '=' in line:
                        # token = "ghp_xxx" or token = 'ghp_xxx'
                        value = line.split('=', 1)[1].strip()
                        value = value.strip('"').strip("'")
                        if value.startswith('ghp_') or value.startswith('github_pat_'):
                            return GitHubAuth(token=value, source=f"config:{config_path}")
            except Exception:
                pass
    return None


def get_github_client() -> Optional[GitHubClient]:
    """T012: Get authenticated GitHub client using best available method."""
    # Try each auth method in priority order
    auth = get_token_from_env()
    if not auth:
        auth = get_token_from_gh_cli()
    if not auth:
        auth = get_token_from_config()
    
    if auth:
        return GitHubClient(auth=auth)
    return None


# === T014: Issue Linkage Storage ===
def load_links() -> Dict[str, IssueLinkage]:
    """Load issue linkages from JSONL file."""
    links = {}
    links_path = Path(LINKS_FILE)
    
    if links_path.exists():
        try:
            with open(links_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        link = IssueLinkage(**data)
                        links[link.bead_id] = link
        except (json.JSONDecodeError, TypeError):
            pass
    
    return links


def save_link(link: IssueLinkage):
    """Append a link to the JSONL file."""
    links_path = Path(LINKS_FILE)
    links_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(links_path, 'a') as f:
        f.write(json.dumps(asdict(link)) + '\n')


def find_link_by_github(number: int) -> Optional[IssueLinkage]:
    """Find linkage by GitHub issue number."""
    for link in load_links().values():
        if link.github_number == number:
            return link
    return None


# === T017: Label/Priority Mapping ===
DEFAULT_PRIORITY_LABELS = {
    0: "priority: critical",
    1: "priority: high", 
    2: "priority: medium",
    3: "priority: low",
    4: "",
}

DEFAULT_TYPE_LABELS = {
    "bug": "type: bug",
    "feature": "type: feature",
    "epic": "type: epic",
    "task": "",
}


def map_bead_to_github_labels(issue: dict) -> List[str]:
    """Map beads issue fields to GitHub labels."""
    labels = []
    
    # Priority label
    priority = issue.get('priority', 4)
    if priority in DEFAULT_PRIORITY_LABELS and DEFAULT_PRIORITY_LABELS[priority]:
        labels.append(DEFAULT_PRIORITY_LABELS[priority])
    
    # Type label
    issue_type = issue.get('issue_type', 'task')
    if issue_type in DEFAULT_TYPE_LABELS and DEFAULT_TYPE_LABELS[issue_type]:
        labels.append(DEFAULT_TYPE_LABELS[issue_type])
    
    # Existing labels (filter speckle- internal ones)
    for label in issue.get('labels', []):
        if not label.startswith('speckle') and not label.startswith('phase:'):
            labels.append(label)
    
    return labels


def extract_priority_from_labels(labels: List[dict]) -> int:
    """Extract priority from GitHub labels."""
    label_names = [l.get('name', '') for l in labels]
    
    for priority, label in DEFAULT_PRIORITY_LABELS.items():
        if label and label in label_names:
            return priority
    
    return 4  # Default priority


def extract_type_from_labels(labels: List[dict]) -> str:
    """Extract issue type from GitHub labels."""
    label_names = [l.get('name', '') for l in labels]
    
    for issue_type, label in DEFAULT_TYPE_LABELS.items():
        if label and label in label_names:
            return issue_type
    
    return "task"


# === T015-T016: Sync Operations ===
def format_issue_body(issue: dict) -> str:
    """Format beads issue as GitHub issue body."""
    lines = []
    
    if issue.get('description'):
        lines.append(issue['description'])
        lines.append("")
    
    lines.append("---")
    lines.append(f"*Synced from beads: `{issue.get('id', 'unknown')}`*")
    
    return "\n".join(lines)


def push_to_github(client: GitHubClient, issue: dict) -> int:
    """T015: Push beads issue to GitHub."""
    links = load_links()
    link = links.get(issue['id'])
    
    labels = map_bead_to_github_labels(issue)
    body = format_issue_body(issue)
    state = "closed" if issue.get('status') == 'closed' else "open"
    
    if link:
        # Update existing
        gh_issue = client.update_issue(
            link.github_number,
            title=issue.get('title', 'Untitled'),
            body=body,
            state=state,
            labels=labels
        )
        # Update link timestamp
        link.last_synced = datetime.now(timezone.utc).isoformat()
        return link.github_number
    else:
        # Create new
        gh_issue = client.create_issue(
            title=issue.get('title', 'Untitled'),
            body=body,
            labels=labels
        )
        
        # Save linkage
        new_link = IssueLinkage(
            bead_id=issue['id'],
            github_number=gh_issue['number'],
            github_url=gh_issue['html_url'],
            repo=client.repo or "",
            sync_direction="bead_to_gh"
        )
        save_link(new_link)
        
        # Close if needed (can't set state on create)
        if state == "closed":
            client.update_issue(gh_issue['number'], state="closed")
        
        return gh_issue['number']


def pull_from_github(client: GitHubClient, gh_issue: dict) -> Optional[str]:
    """T016: Pull GitHub issue to beads."""
    link = find_link_by_github(gh_issue['number'])
    
    title = gh_issue.get('title', 'Untitled')
    state = "closed" if gh_issue.get('state') == 'closed' else "open"
    priority = extract_priority_from_labels(gh_issue.get('labels', []))
    issue_type = extract_type_from_labels(gh_issue.get('labels', []))
    
    if link:
        # Update existing bead
        try:
            subprocess.run([
                'bd', 'update', link.bead_id,
                '--title', title,
                '--status', state,
                '--priority', str(priority),
            ], capture_output=True, timeout=10)
            return link.bead_id
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
    else:
        # Create new bead
        try:
            result = subprocess.run([
                'bd', 'create',
                '--title', title,
                '--type', issue_type,
                '--priority', str(priority),
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Parse bead ID from output
                for line in result.stdout.split('\n'):
                    if 'Created issue:' in line:
                        bead_id = line.split(':')[-1].strip()
                        
                        # Save linkage
                        new_link = IssueLinkage(
                            bead_id=bead_id,
                            github_number=gh_issue['number'],
                            github_url=gh_issue['html_url'],
                            repo=client.repo or "",
                            sync_direction="gh_to_bead"
                        )
                        save_link(new_link)
                        
                        # Close if needed
                        if state == "closed":
                            subprocess.run(['bd', 'close', bead_id], 
                                         capture_output=True, timeout=10)
                        
                        return bead_id
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    return None


# === T013: CLI Commands ===
def cmd_auth(args):
    """Show authentication status."""
    print("GitHub Authentication Status")
    print("=" * 40)
    
    # Check each method
    env_auth = get_token_from_env()
    cli_auth = get_token_from_gh_cli()
    config_auth = get_token_from_config()
    
    print(f"\n1. Environment (GITHUB_TOKEN/GH_TOKEN):")
    if env_auth:
        print(f"   ✓ Found: {env_auth.mask_token()}")
    else:
        print("   ✗ Not set")
    
    print(f"\n2. GitHub CLI (gh auth token):")
    if cli_auth:
        print(f"   ✓ Found: {cli_auth.mask_token()}")
    else:
        print("   ✗ Not available (gh not installed or not logged in)")
    
    print(f"\n3. Config file:")
    if config_auth:
        print(f"   ✓ Found: {config_auth.mask_token()} ({config_auth.source})")
    else:
        print(f"   ✗ Not found in: {', '.join(str(p) for p in CONFIG_LOCATIONS)}")
    
    # Active auth
    client = get_github_client()
    print("\n" + "=" * 40)
    if client and client.auth:
        print(f"✓ Active: {client.auth.source} ({client.auth.mask_token()})")
        if client.repo:
            print(f"✓ Repository: {client.repo}")
        
        # Test connection
        try:
            rate = client.get_rate_limit()
            remaining = rate.get('rate', {}).get('remaining', 0)
            limit = rate.get('rate', {}).get('limit', 0)
            print(f"✓ Rate limit: {remaining}/{limit} requests remaining")
        except Exception as e:
            print(f"⚠ Connection test failed: {e}")
    else:
        print("✗ No authentication available")
        print("\nTo authenticate, either:")
        print("  1. Set GITHUB_TOKEN environment variable")
        print("  2. Run: gh auth login")
        print("  3. Add token to ~/.speckle/config.toml")


def cmd_sync(args):
    """Bidirectional sync between beads and GitHub."""
    client = get_github_client()
    if not client:
        print("✗ Not authenticated. Run: speckle github auth")
        return 1
    
    if not client.repo:
        print("✗ Could not detect repository. Are you in a git repo?")
        return 1
    
    print(f"Syncing with {client.repo}...")
    print("=" * 40)
    
    pushed = 0
    pulled = 0
    errors = 0
    
    # Get existing links
    links = load_links()
    linked_gh_numbers = {l.github_number for l in links.values()}
    
    # Push local issues to GitHub
    print("\nPushing to GitHub...")
    try:
        result = subprocess.run(
            ['bd', 'list', '--all', '--json', '--limit', '0'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            issues = json.loads(result.stdout)
            for issue in issues:
                try:
                    gh_num = push_to_github(client, issue)
                    status = "updated" if issue['id'] in links else "created"
                    print(f"  ✓ {issue['id']} → #{gh_num} ({status})")
                    pushed += 1
                except Exception as e:
                    print(f"  ✗ {issue['id']}: {e}")
                    errors += 1
    except Exception as e:
        print(f"  ✗ Failed to list beads: {e}")
        errors += 1
    
    # Pull GitHub issues not yet linked
    print("\nPulling from GitHub...")
    try:
        gh_issues = client.list_issues(state="all")
        for gh_issue in gh_issues:
            if gh_issue['number'] not in linked_gh_numbers:
                # Skip pull requests
                if 'pull_request' in gh_issue:
                    continue
                try:
                    bead_id = pull_from_github(client, gh_issue)
                    if bead_id:
                        print(f"  ✓ #{gh_issue['number']} → {bead_id} (created)")
                        pulled += 1
                except Exception as e:
                    print(f"  ✗ #{gh_issue['number']}: {e}")
                    errors += 1
    except Exception as e:
        print(f"  ✗ Failed to list GitHub issues: {e}")
        errors += 1
    
    # Summary
    print("\n" + "=" * 40)
    print(f"✓ Pushed: {pushed} issues")
    print(f"✓ Pulled: {pulled} issues")
    if errors:
        print(f"✗ Errors: {errors}")
        return 1
    return 0


def cmd_push(args):
    """Push beads issues to GitHub."""
    client = get_github_client()
    if not client:
        print("✗ Not authenticated. Run: speckle github auth")
        return 1
    
    print(f"Pushing to {client.repo}...")
    
    try:
        result = subprocess.run(
            ['bd', 'list', '--all', '--json', '--limit', '0'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            issues = json.loads(result.stdout)
            links = load_links()
            
            for issue in issues:
                try:
                    gh_num = push_to_github(client, issue)
                    status = "updated" if issue['id'] in links else "created"
                    print(f"  ✓ {issue['id']} → #{gh_num} ({status})")
                except Exception as e:
                    print(f"  ✗ {issue['id']}: {e}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return 1
    
    return 0


def cmd_pull(args):
    """Pull GitHub issues to beads."""
    client = get_github_client()
    if not client:
        print("✗ Not authenticated. Run: speckle github auth")
        return 1
    
    print(f"Pulling from {client.repo}...")
    
    links = load_links()
    linked_gh_numbers = {l.github_number for l in links.values()}
    
    try:
        gh_issues = client.list_issues(state="all")
        for gh_issue in gh_issues:
            if 'pull_request' in gh_issue:
                continue
            try:
                bead_id = pull_from_github(client, gh_issue)
                if bead_id:
                    status = "updated" if gh_issue['number'] in linked_gh_numbers else "created"
                    print(f"  ✓ #{gh_issue['number']} → {bead_id} ({status})")
            except Exception as e:
                print(f"  ✗ #{gh_issue['number']}: {e}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return 1
    
    return 0


def cmd_status(args):
    """Show sync status."""
    client = get_github_client()
    links = load_links()
    
    print("GitHub Sync Status")
    print("=" * 40)
    
    if client and client.repo:
        print(f"Repository: {client.repo}")
    else:
        print("Repository: Not detected")
    
    print(f"Linked issues: {len(links)}")
    
    if links:
        print("\nRecent links:")
        sorted_links = sorted(links.values(), 
                             key=lambda x: x.last_synced, reverse=True)[:10]
        for link in sorted_links:
            print(f"  {link.bead_id} ↔ #{link.github_number}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Speckle GitHub Integration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Commands:
  auth     Show authentication status
  sync     Bidirectional sync with GitHub
  push     Push beads issues to GitHub
  pull     Pull GitHub issues to beads
  status   Show sync status
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # auth command
    subparsers.add_parser('auth', help='Show authentication status')
    
    # sync command
    subparsers.add_parser('sync', help='Bidirectional sync with GitHub')
    
    # push command
    subparsers.add_parser('push', help='Push beads issues to GitHub')
    
    # pull command
    subparsers.add_parser('pull', help='Pull GitHub issues to beads')
    
    # status command
    subparsers.add_parser('status', help='Show sync status')
    
    args = parser.parse_args()
    
    if args.command == 'auth':
        return cmd_auth(args)
    elif args.command == 'sync':
        return cmd_sync(args)
    elif args.command == 'push':
        return cmd_push(args)
    elif args.command == 'pull':
        return cmd_pull(args)
    elif args.command == 'status':
        return cmd_status(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
