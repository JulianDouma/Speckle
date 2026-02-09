# Speckle Board Enhancements - Deep Analysis

## Overview

This document analyzes two major enhancements for the Speckle Kanban Board:

1. **System Color Mode** - Automatic dark/light theme detection with user override
2. **GitHub Issue Integration** - Link and sync with GitHub Issues using `ghp_` tokens

---

## Feature 1: System Color Mode

### Problem Statement

The current board has a fixed light theme that:
- Causes eye strain in low-light environments
- Doesn't respect user OS preferences
- Looks inconsistent with other dev tools (VS Code, terminals often in dark mode)
- No manual override for users who prefer opposite of system setting

### Best Practices Research

#### 1. CSS `prefers-color-scheme` Media Query
```css
@media (prefers-color-scheme: dark) {
    :root {
        --bg: #0f172a;
        --text: #e2e8f0;
    }
}
```
**Pros:** Zero JavaScript, automatic, battery-efficient
**Cons:** No user override, no persistence

#### 2. CSS Custom Properties with JavaScript Toggle
```javascript
document.documentElement.setAttribute('data-theme', 'dark');
```
```css
[data-theme="dark"] {
    --bg: #0f172a;
}
```
**Pros:** User control, can combine with system detection
**Cons:** Flash of incorrect theme on load

#### 3. Server-Side Theme via Cookie/Query Parameter
```python
theme = request.cookies.get('theme', 'system')
```
**Pros:** No flash, works without JavaScript
**Cons:** Requires server roundtrip to change

### Recommended Approach: Hybrid System

Combine all three approaches for best UX:

```
Priority Order:
1. User preference (localStorage/cookie)
2. Query parameter (?theme=dark)
3. System preference (prefers-color-scheme)
4. Default (light)
```

### Implementation Design

#### A. CSS Architecture

```css
:root {
    /* Light theme (default) */
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
    
    /* Priority colors - accessible in both modes */
    --p0: #dc2626;
    --p1: #ea580c;
    --p2: #f59e0b;
    --p3: #10b981;
    --p4: #6b7280;
    
    /* Shadows */
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.1);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
}

/* Dark theme via attribute */
[data-theme="dark"] {
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
    
    /* Shadows - more subtle in dark mode */
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.3);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.4);
}

/* System preference detection (when no explicit choice) */
@media (prefers-color-scheme: dark) {
    :root:not([data-theme]) {
        /* Dark theme variables */
    }
}
```

#### B. JavaScript Theme Controller

```javascript
const ThemeController = {
    STORAGE_KEY: 'speckle-theme',
    
    init() {
        const saved = localStorage.getItem(this.STORAGE_KEY);
        if (saved) {
            this.apply(saved);
        }
        this.updateToggleUI();
    },
    
    apply(theme) {
        if (theme === 'system') {
            document.documentElement.removeAttribute('data-theme');
        } else {
            document.documentElement.setAttribute('data-theme', theme);
        }
        localStorage.setItem(this.STORAGE_KEY, theme);
        this.updateToggleUI();
    },
    
    toggle() {
        const current = this.getCurrent();
        const next = current === 'dark' ? 'light' : 'dark';
        this.apply(next);
    },
    
    getCurrent() {
        const explicit = document.documentElement.getAttribute('data-theme');
        if (explicit) return explicit;
        return window.matchMedia('(prefers-color-scheme: dark)').matches 
            ? 'dark' : 'light';
    },
    
    updateToggleUI() {
        const btn = document.querySelector('.theme-toggle');
        if (btn) {
            const isDark = this.getCurrent() === 'dark';
            btn.innerHTML = isDark ? '☀️' : '🌙';
            btn.title = isDark ? 'Switch to light mode' : 'Switch to dark mode';
        }
    }
};

// Initialize on load
document.addEventListener('DOMContentLoaded', () => ThemeController.init());

// Listen for system preference changes
window.matchMedia('(prefers-color-scheme: dark)')
    .addEventListener('change', () => ThemeController.updateToggleUI());
```

#### C. UI Toggle Button

```html
<div class="controls">
    <button class="theme-toggle" onclick="ThemeController.toggle()" 
            title="Toggle dark/light mode">🌙</button>
    {filter_html}
    <span class="refresh-badge">⟳ {refresh}s</span>
</div>
```

```css
.theme-toggle {
    background: rgba(255,255,255,0.2);
    border: none;
    font-size: 1.25rem;
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    border-radius: 0.375rem;
    transition: background 0.2s;
}

.theme-toggle:hover {
    background: rgba(255,255,255,0.3);
}
```

### Color Accessibility

Both themes must meet WCAG 2.1 AA contrast requirements (4.5:1 for normal text):

| Element | Light Mode | Dark Mode | Contrast |
|---------|------------|-----------|----------|
| Body text | #1e293b on #f8fafc | #e2e8f0 on #0f172a | 12.6:1 / 11.5:1 |
| Muted text | #64748b on #ffffff | #94a3b8 on #1e293b | 4.7:1 / 5.1:1 |
| P0 badge | #dc2626 on #fef2f2 | #fca5a5 on #451a1a | 5.8:1 / 5.2:1 |

### Testing Matrix

| Scenario | Expected Behavior |
|----------|-------------------|
| First visit, system=light | Light theme |
| First visit, system=dark | Dark theme |
| Toggle to dark, refresh | Dark theme persists |
| Toggle to light, system=dark | Light theme (user override) |
| Clear localStorage | Revert to system preference |
| ?theme=dark query param | Dark theme (one-time) |

---

## Feature 2: GitHub Issue Integration

### Problem Statement

Currently, Speckle manages issues via beads (local JSONL), but teams often need:
- GitHub Issues for public visibility and collaboration
- Integration with GitHub Projects
- Cross-referencing PRs and commits
- Issue templates and labels from GitHub
- Notifications via GitHub's infrastructure

### Authentication Options

#### Option A: Personal Access Token (ghp_)

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
```

**Scopes required:**
- `repo` - Full repository access (for private repos)
- `public_repo` - Only public repos
- `project` - For GitHub Projects integration

**Pros:**
- Simple to implement
- Works in CI/CD
- Fine-grained tokens available (2023+)

**Cons:**
- User must generate and manage token
- Token rotation responsibility on user
- Can't use OAuth flows

#### Option B: GitHub CLI (`gh`) Authentication

```bash
gh auth status  # Check current auth
gh auth login   # Interactive login
```

**Pros:**
- Already installed for many developers
- Handles token storage securely
- OAuth flow available

**Cons:**
- Requires gh CLI installed
- Interactive login not suitable for CI

#### Option C: GitHub App

```yaml
app_id: 12345
installation_id: 67890
private_key: /path/to/key.pem
```

**Pros:**
- Higher rate limits
- Can act on behalf of organization
- Granular permissions

**Cons:**
- Complex setup
- Overkill for personal use

### Recommended Approach: Layered Authentication

```python
def get_github_client():
    """Get authenticated GitHub client using best available method."""
    
    # 1. Environment variable (CI/CD, explicit config)
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if token:
        return Github(token)
    
    # 2. gh CLI (if installed and authenticated)
    try:
        result = subprocess.run(
            ['gh', 'auth', 'token'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return Github(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # 3. Config file (~/.speckle/config.toml or .speckle/config.toml)
    config_token = load_config().get('github', {}).get('token')
    if config_token:
        return Github(config_token)
    
    # 4. No authentication available
    return None
```

### Integration Architecture

#### A. Configuration Schema

```toml
# .speckle/config.toml
[github]
enabled = true
repo = "owner/repo"           # Auto-detect from git remote if not set
sync_mode = "bidirectional"   # "bidirectional" | "push" | "pull" | "manual"
label_prefix = "speckle:"     # Prefix for Speckle-managed labels

[github.mapping]
# Map beads status to GitHub
status.open = "open"
status.in_progress = "open"   # GitHub has no "in progress" state
status.blocked = "open"
status.closed = "closed"

# Map beads priority to GitHub labels
priority.0 = "priority: critical"
priority.1 = "priority: high"
priority.2 = "priority: medium"
priority.3 = "priority: low"
priority.4 = ""               # No label for default priority

# Map beads issue_type to GitHub labels
type.bug = "type: bug"
type.feature = "type: feature"
type.epic = "type: epic"
type.task = ""
```

#### B. Data Model: Beads ↔ GitHub Mapping

```python
@dataclass
class IssueLinkage:
    """Tracks relationship between beads and GitHub issues."""
    bead_id: str              # e.g., "speckle-42f"
    github_number: int        # e.g., 123
    github_url: str           # e.g., "https://github.com/owner/repo/issues/123"
    last_synced: datetime
    sync_direction: str       # "bead_to_gh" | "gh_to_bead" | "conflict"
    
# Stored in .speckle/github-links.jsonl
```

#### C. Sync Operations

```python
class GitHubSync:
    """Bidirectional sync between beads and GitHub Issues."""
    
    def __init__(self, github: Github, repo_name: str, config: dict):
        self.gh = github
        self.repo = github.get_repo(repo_name)
        self.config = config
        self.links = self._load_links()
    
    def push_to_github(self, bead_issue: dict) -> int:
        """Create or update GitHub issue from beads issue."""
        link = self.links.get(bead_issue['id'])
        
        labels = self._map_labels(bead_issue)
        body = self._format_body(bead_issue)
        
        if link:
            # Update existing
            gh_issue = self.repo.get_issue(link.github_number)
            gh_issue.edit(
                title=bead_issue['title'],
                body=body,
                labels=labels,
                state='closed' if bead_issue['status'] == 'closed' else 'open'
            )
            return link.github_number
        else:
            # Create new
            gh_issue = self.repo.create_issue(
                title=bead_issue['title'],
                body=body,
                labels=labels
            )
            self._save_link(bead_issue['id'], gh_issue.number, gh_issue.html_url)
            return gh_issue.number
    
    def pull_from_github(self, gh_issue) -> dict:
        """Create or update beads issue from GitHub issue."""
        link = self._find_link_by_github(gh_issue.number)
        
        bead_data = {
            'title': gh_issue.title,
            'status': 'closed' if gh_issue.state == 'closed' else 'open',
            'priority': self._extract_priority(gh_issue.labels),
            'issue_type': self._extract_type(gh_issue.labels),
            'labels': [l.name for l in gh_issue.labels],
            'github_url': gh_issue.html_url,
        }
        
        if link:
            # Update existing bead
            subprocess.run(['bd', 'update', link.bead_id, '--json', json.dumps(bead_data)])
        else:
            # Create new bead
            result = subprocess.run(
                ['bd', 'create', '--title', bead_data['title'], '--json'],
                capture_output=True, text=True
            )
            bead_id = json.loads(result.stdout)['id']
            self._save_link(bead_id, gh_issue.number, gh_issue.html_url)
        
        return bead_data
    
    def sync_all(self):
        """Full bidirectional sync."""
        # 1. Push local changes to GitHub
        local_issues = json.loads(
            subprocess.run(['bd', 'list', '--all', '--json'], capture_output=True, text=True).stdout
        )
        for issue in local_issues:
            if self._needs_push(issue):
                self.push_to_github(issue)
        
        # 2. Pull remote changes from GitHub
        for gh_issue in self.repo.get_issues(state='all'):
            if self._needs_pull(gh_issue):
                self.pull_from_github(gh_issue)
```

#### D. Board UI Integration

Add GitHub link to cards:

```python
def render_card(issue: Dict[str, Any]) -> str:
    """Render card with optional GitHub link."""
    github_url = issue.get('github_url')
    
    # GitHub icon/link if linked
    github_html = ''
    if github_url:
        github_html = f'''
        <a href="{github_url}" target="_blank" class="github-link" 
           title="View on GitHub">
            <svg class="github-icon" viewBox="0 0 16 16" width="14" height="14">
                <path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
            </svg>
        </a>
        '''
    
    return f'''
    <div class="card {p_class}">
        <div class="card-header">
            <span class="card-id">{issue_id}</span>
            <div class="card-actions">
                {github_html}
                <span class="priority-badge {p_class}">{p_label}</span>
            </div>
        </div>
        ...
    </div>
    '''
```

### Security Best Practices

#### Token Storage

```
NEVER store tokens in:
- Source code
- .speckle/config.toml (if committed)
- Environment in docker-compose.yml

DO store tokens in:
- Environment variables
- ~/.speckle/config.toml (user home, not repo)
- System keychain (via keyring library)
- gh auth (uses system credential store)
```

#### Token Scopes (Principle of Least Privilege)

```
For public repos only:
  - public_repo

For private repos:
  - repo (unfortunately required for full access)

Fine-grained tokens (recommended):
  - Contents: Read
  - Issues: Read and write
  - Pull requests: Read (for cross-referencing)
  - Metadata: Read
```

#### Rate Limiting

```python
def with_rate_limit_handling(func):
    """Decorator to handle GitHub API rate limits."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RateLimitExceededException as e:
            reset_time = datetime.fromtimestamp(e.headers.get('X-RateLimit-Reset', 0))
            wait_seconds = (reset_time - datetime.now()).total_seconds()
            print(f"Rate limited. Resets at {reset_time}. Waiting {wait_seconds:.0f}s...")
            time.sleep(max(wait_seconds, 0) + 1)
            return func(*args, **kwargs)
    return wrapper
```

### CLI Commands

```bash
# Setup
speckle github auth              # Interactive auth setup
speckle github auth --token      # Set token directly
speckle github status            # Show auth status and sync state

# Sync operations
speckle github sync              # Bidirectional sync
speckle github push              # Push local changes to GitHub
speckle github pull              # Pull GitHub changes to local

# Issue operations
speckle github link <bead-id> <gh-number>  # Manually link issues
speckle github unlink <bead-id>            # Remove linkage
speckle github open <bead-id>              # Open linked issue in browser

# Board integration
speckle board --github           # Show GitHub status on cards
```

---

## Implementation Phases

### Phase 1: System Color Mode (Estimated: 2-3 hours)

| Task | Description | Priority |
|------|-------------|----------|
| T001 | Define CSS custom properties for dark theme | High |
| T002 | Add `prefers-color-scheme` media query | High |
| T003 | Implement JavaScript theme controller | High |
| T004 | Add theme toggle button to header | High |
| T005 | Persist preference in localStorage | Medium |
| T006 | Test accessibility contrast ratios | High |
| T007 | Add smooth transition animations | Low |

### Phase 2: GitHub Integration Foundation (Estimated: 4-6 hours)

| Task | Description | Priority |
|------|-------------|----------|
| T008 | Implement layered authentication | High |
| T009 | Create config schema in config.toml | High |
| T010 | Add github-links.jsonl storage | High |
| T011 | Implement push_to_github function | High |
| T012 | Implement pull_from_github function | High |
| T013 | Add `speckle github auth` command | High |
| T014 | Add `speckle github sync` command | High |

### Phase 3: Board Integration (Estimated: 2-3 hours)

| Task | Description | Priority |
|------|-------------|----------|
| T015 | Add GitHub icon/link to cards | Medium |
| T016 | Show sync status in board footer | Medium |
| T017 | Add "Open in GitHub" context action | Medium |
| T018 | Real-time sync status indicator | Low |

### Phase 4: Polish & Documentation (Estimated: 1-2 hours)

| Task | Description | Priority |
|------|-------------|----------|
| T019 | Document GitHub integration setup | High |
| T020 | Add error handling and user feedback | High |
| T021 | Handle offline/rate-limited scenarios | Medium |
| T022 | Add integration tests | Medium |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Token exposure in logs | High | Never log tokens; use `***` masking |
| Rate limiting | Medium | Implement backoff; cache API responses |
| Sync conflicts | Medium | Use last-modified timestamps; prefer local |
| PyGithub dependency | Low | Use gh CLI as fallback; keep stdlib option |
| Color accessibility | Medium | Test with WCAG tools; provide high-contrast option |

---

## Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| Use CSS custom properties | Maximum browser support, no build step | 2026-02-09 |
| Prefer gh CLI over direct API | Already installed for most devs; secure token storage | 2026-02-09 |
| Store links in JSONL | Consistent with beads; easy to debug | 2026-02-09 |
| Bidirectional sync default | Matches user expectations from other tools | 2026-02-09 |

---

## References

- [CSS prefers-color-scheme](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme)
- [WCAG 2.1 Contrast Requirements](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)
- [GitHub REST API](https://docs.github.com/en/rest)
- [GitHub Fine-grained PATs](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [PyGithub Documentation](https://pygithub.readthedocs.io/)
- [gh CLI Manual](https://cli.github.com/manual/)
