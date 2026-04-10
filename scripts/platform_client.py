#!/usr/bin/env python3
"""
Aztec Plataforma REST API client — for HDD harness integration.
Uses only stdlib (no pip dependencies).

Usage:
  python scripts/platform_client.py get AZT-1
  python scripts/platform_client.py create "Title" ["Description"] [--project-id <UUID>]
  python scripts/platform_client.py move AZT-1 "En curso"
  python scripts/platform_client.py comment AZT-1 "Evidence message"
  python scripts/platform_client.py list [--column "En curso"] [--project-id <UUID>]
  python scripts/platform_client.py update <KEY> "<BODY_MARKDOWN>"
  python scripts/platform_client.py projects
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
    """Load config from .env file first, then environment.

    Returns (api_key, base_url, project_id) where project_id may be None.
    """
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

    # project_id may be None — callers that need it must validate themselves
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


def list_projects():
    """List all projects available to the current user."""
    return _request("GET", "projects")


def list_tasks(column_name=None, project_id=None):
    """List tasks, optionally filtered by column name and/or project_id.

    When project_id is None:
      - If PLATFORM_PROJECT_ID is set in .env, uses that (single-project behaviour).
      - Otherwise, fetches all projects with status 'En ejecucion' and returns
        tasks from all of them, tagging each with _project_name and _project_prefix.
    """
    if project_id is None:
        _, _, config_project_id = _get_config()
        if config_project_id:
            # Single-project mode (legacy behaviour)
            tasks = _request("GET", f"tasks?project_id={config_project_id}")
        else:
            # Multi-project mode: fetch all active projects
            projects = list_projects()
            active = [p for p in projects if p.get("status") == "En ejecucion"]
            if not active:
                print(
                    "ERROR: PLATFORM_PROJECT_ID requerido para esta operacion. "
                    "Agregalo al .env",
                    file=sys.stderr,
                )
                sys.exit(1)
            tasks = []
            for proj in active:
                proj_tasks = _request("GET", f"tasks?project_id={proj['id']}")
                for t in proj_tasks:
                    t["_project_name"] = proj.get("name", "")
                    t["_project_prefix"] = proj.get("prefix", "")
                tasks.extend(proj_tasks)
    else:
        tasks = _request("GET", f"tasks?project_id={project_id}")

    if column_name:
        column_id = _find_column_id(column_name)
        tasks = [t for t in tasks if t.get("column_id") == column_id]

    # Attach column name for display
    for t in tasks:
        t["_column_name"] = _find_column_name(t.get("column_id", ""))

    return tasks


def create_task(title, body_markdown=None, priority="media", project_id=None):
    """Create a new task in the configured project. Returns task dict or None.

    project_id overrides the value from .env when provided.
    """
    _, _, config_project_id = _get_config()
    resolved_project_id = project_id or config_project_id

    if not resolved_project_id:
        print(
            "ERROR: PLATFORM_PROJECT_ID requerido para esta operacion. "
            "Agregalo al .env",
            file=sys.stderr,
        )
        sys.exit(1)

    payload = {
        "title": title,
        "project_id": resolved_project_id,
        "priority": priority,
    }
    if body_markdown:
        payload["body_markdown"] = body_markdown

    return _request("POST", "tasks", payload)


def search_tasks_by_title(substring):
    """List all project tasks whose title contains substring (case-insensitive)."""
    tasks = list_tasks()
    return [t for t in tasks if substring.lower() in t.get("title", "").lower()]


def update_task(task_key, body_markdown):
    """Update a task's body_markdown. Returns True/False."""
    task = get_task(task_key)
    if not task:
        print(f"Task {task_key} not found.", file=sys.stderr)
        return False
    _request("PATCH", f"tasks/{task['id']}", {"body_markdown": body_markdown})
    return True


# ── CLI ──

def _print_task(task, full=False):
    """Pretty-print a task."""
    key = task.get("task_key", task.get("id", "?"))
    column = task.get("_column_name") or _find_column_name(task.get("column_id", ""))
    priority = task.get("priority", "?")
    project_prefix = task.get("_project_prefix", "")
    project_label = f"[{project_prefix}] " if project_prefix else ""
    print(f"  {project_label}{key}  [{column}]  [{priority}]  {task['title']}")
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
            print('Usage: platform_client.py create "<TITLE>" ["<BODY_MARKDOWN>"] [--project-id <UUID>]')
            sys.exit(1)
        title = sys.argv[2]
        body = None
        override_project_id = None
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--project-id" and i + 1 < len(sys.argv):
                override_project_id = sys.argv[i + 1]
                i += 2
            else:
                if body is None:
                    body = sys.argv[i]
                i += 1
        task = create_task(title, body, project_id=override_project_id)
        if task:
            key = task.get("task_key", task.get("id", "?"))
            print(f"Created: {key}  {task['title']}")
        else:
            print("Failed to create task.")
            sys.exit(1)

    elif cmd == "list":
        column = None
        project_id_arg = None
        if "--column" in sys.argv:
            idx = sys.argv.index("--column")
            if idx + 1 < len(sys.argv):
                column = sys.argv[idx + 1]
        if "--project-id" in sys.argv:
            idx = sys.argv.index("--project-id")
            if idx + 1 < len(sys.argv):
                project_id_arg = sys.argv[idx + 1]
        tasks = list_tasks(column_name=column, project_id=project_id_arg)
        if tasks:
            # Group by project if multi-project
            has_multi = any(t.get("_project_name") for t in tasks)
            if has_multi:
                from collections import defaultdict
                by_project = defaultdict(list)
                for t in tasks:
                    proj_label = t.get("_project_name") or "Unknown"
                    by_project[proj_label].append(t)
                for proj_name, proj_tasks in by_project.items():
                    print(f"\n{proj_name}:")
                    for t in proj_tasks:
                        _print_task(t)
            else:
                for t in tasks:
                    _print_task(t)
        else:
            print("No tasks found.")

    elif cmd == "update":
        if len(sys.argv) < 4:
            print('Usage: platform_client.py update <TASK_KEY> "<BODY_MARKDOWN>"')
            sys.exit(1)
        ok = update_task(sys.argv[2], sys.argv[3])
        if ok:
            print(f"Updated {sys.argv[2]}")
        else:
            sys.exit(1)

    elif cmd == "projects":
        projects = list_projects()
        if not projects:
            print("No projects found.")
            return
        for i, proj in enumerate(projects, 1):
            prefix = proj.get("prefix", "?")
            name = proj.get("name", "?")
            status = proj.get("status", "?")
            print(f"  {i}. [{prefix}] {name}  ({status})")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__.strip())
        sys.exit(1)


if __name__ == "__main__":
    main()
