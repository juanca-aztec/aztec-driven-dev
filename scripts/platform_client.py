#!/usr/bin/env python3
"""
Aztec Plataforma REST API client — for HDD harness integration.
Uses only stdlib (no pip dependencies).

Usage:
  python scripts/platform_client.py get AZT-1
  python scripts/platform_client.py create "Title" ["Description"]
  python scripts/platform_client.py move AZT-1 "En curso"
  python scripts/platform_client.py comment AZT-1 "Evidence message"
  python scripts/platform_client.py list [--column "En curso"]
"""
import os
import sys
import json
import urllib.request
import urllib.error


def _load_env():
    """Load all variables from .env file (project .env takes priority)."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()
    return env_vars


def _get_config():
    """Load config from .env file first, then environment."""
    env_vars = _load_env()

    api_key = env_vars.get("PLATFORM_API_KEY") or os.environ.get("PLATFORM_API_KEY")
    base_url = env_vars.get("PLATFORM_BASE_URL") or os.environ.get("PLATFORM_BASE_URL")
    project_id = env_vars.get("PLATFORM_PROJECT_ID") or os.environ.get("PLATFORM_PROJECT_ID")

    if not api_key:
        print("ERROR: PLATFORM_API_KEY not set. Add it to .env or export it.", file=sys.stderr)
        sys.exit(1)
    if not base_url:
        print("ERROR: PLATFORM_BASE_URL not set. Add it to .env or export it.", file=sys.stderr)
        sys.exit(1)
    if not project_id:
        print("ERROR: PLATFORM_PROJECT_ID not set. Add it to .env or export it.", file=sys.stderr)
        sys.exit(1)

    return api_key, base_url.rstrip("/"), project_id


def _request(method, path, body=None):
    """Make an authenticated REST request to the platform API."""
    api_key, base_url, _ = _get_config()
    url = f"{base_url}/api-gateway/{path.lstrip('/')}"

    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        print(f"HTTP {e.code} on {method} {url}: {body_text}", file=sys.stderr)
        sys.exit(1)


# ── Column helpers ──

_column_cache = None


def _get_columns():
    """Fetch and cache the global columns list."""
    global _column_cache
    if _column_cache is None:
        _column_cache = _request("GET", "columns")
    return _column_cache


def _find_column_id(column_name):
    """Return column UUID by name. Exits if not found."""
    columns = _get_columns()
    match = next((c for c in columns if c["name"].lower() == column_name.lower()), None)
    if not match:
        names = [c["name"] for c in columns]
        print(f"Column '{column_name}' not found. Available: {names}", file=sys.stderr)
        sys.exit(1)
    return match["id"]


def _find_column_name(column_id):
    """Return column name by UUID."""
    columns = _get_columns()
    match = next((c for c in columns if c["id"] == column_id), None)
    return match["name"] if match else "?"


# ── Public API ──

def get_task(task_key):
    """Get task by short key (e.g., 'AZT-1'). Returns dict or None."""
    try:
        return _request("GET", f"tasks/by-key/{task_key}")
    except SystemExit:
        return None


def move_task(task_key, column_name):
    """Move task to a column by name (e.g., 'En curso'). Returns True/False."""
    task = get_task(task_key)
    if not task:
        print(f"Task {task_key} not found.", file=sys.stderr)
        return False

    column_id = _find_column_id(column_name)
    _request("PATCH", f"tasks/{task['id']}/move", {"column_id": column_id})
    return True


def add_comment(task_key, body):
    """Add a comment to a task (for evidence logging). Returns True/False."""
    task = get_task(task_key)
    if not task:
        print(f"Task {task_key} not found.", file=sys.stderr)
        return False

    _request("POST", f"tasks/{task['id']}/comments", {"body": body})
    return True


def list_tasks(column_name=None):
    """List tasks in the configured project, optionally filtered by column name."""
    _, _, project_id = _get_config()
    tasks = _request("GET", f"tasks?project_id={project_id}")

    if column_name:
        column_id = _find_column_id(column_name)
        tasks = [t for t in tasks if t.get("column_id") == column_id]

    # Attach column name for display
    for t in tasks:
        t["_column_name"] = _find_column_name(t.get("column_id", ""))

    return tasks


def create_task(title, body_markdown=None, priority="media"):
    """Create a new task in the configured project. Returns task dict or None."""
    _, _, project_id = _get_config()

    payload = {
        "title": title,
        "project_id": project_id,
        "priority": priority,
    }
    if body_markdown:
        payload["body_markdown"] = body_markdown

    return _request("POST", "tasks", payload)


def search_tasks_by_title(substring):
    """List all project tasks whose title contains substring (case-insensitive)."""
    tasks = list_tasks()
    return [t for t in tasks if substring.lower() in t.get("title", "").lower()]


# ── CLI ──

def _print_task(task, full=False):
    """Pretty-print a task."""
    key = task.get("task_key", task.get("id", "?"))
    column = task.get("_column_name") or _find_column_name(task.get("column_id", ""))
    priority = task.get("priority", "?")
    print(f"  {key}  [{column}]  [{priority}]  {task['title']}")
    if full and task.get("body_markdown"):
        for line in task["body_markdown"].strip().split("\n"):
            print(f"    {line}")


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "get":
        if len(sys.argv) < 3:
            print("Usage: platform_client.py get <TASK_KEY> [--full]")
            sys.exit(1)
        full = "--full" in sys.argv
        task = get_task(sys.argv[2])
        if task:
            task["_column_name"] = _find_column_name(task.get("column_id", ""))
            _print_task(task, full=full)
        else:
            print(f"Task {sys.argv[2]} not found.")
            sys.exit(1)

    elif cmd == "move":
        if len(sys.argv) < 4:
            print('Usage: platform_client.py move <TASK_KEY> "<COLUMN_NAME>"')
            sys.exit(1)
        ok = move_task(sys.argv[2], sys.argv[3])
        if ok:
            print(f"Moved {sys.argv[2]} -> {sys.argv[3]}")
        else:
            sys.exit(1)

    elif cmd == "comment":
        if len(sys.argv) < 4:
            print('Usage: platform_client.py comment <TASK_KEY> "<BODY>"')
            sys.exit(1)
        ok = add_comment(sys.argv[2], sys.argv[3])
        if ok:
            print(f"Comment added to {sys.argv[2]}")
        else:
            sys.exit(1)

    elif cmd == "create":
        if len(sys.argv) < 3:
            print('Usage: platform_client.py create "<TITLE>" ["<BODY_MARKDOWN>"]')
            sys.exit(1)
        title = sys.argv[2]
        body = sys.argv[3] if len(sys.argv) > 3 else None
        task = create_task(title, body)
        if task:
            key = task.get("task_key", task.get("id", "?"))
            print(f"Created: {key}  {task['title']}")
        else:
            print("Failed to create task.")
            sys.exit(1)

    elif cmd == "list":
        column = None
        if "--column" in sys.argv:
            idx = sys.argv.index("--column")
            if idx + 1 < len(sys.argv):
                column = sys.argv[idx + 1]
        tasks = list_tasks(column_name=column)
        if tasks:
            for t in tasks:
                _print_task(t)
        else:
            print("No tasks found.")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__.strip())
        sys.exit(1)


if __name__ == "__main__":
    main()
