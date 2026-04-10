#!/usr/bin/env python3
"""
CI Failure Bridge — When CI fails, auto-create a bug task in Aztec Plataforma.
Triggered by: .github/workflows/linear-bridge.yml

Usage:
  python scripts/ci_failure_bridge.py <run_id>
"""
import os
import sys
import json
import subprocess

# Add scripts dir to path for platform_client import
sys.path.insert(0, os.path.dirname(__file__))
from platform_client import add_comment, create_task, search_tasks_by_title


def get_failed_jobs(run_id):
    """Get failed job names from a GitHub Actions run."""
    try:
        result = subprocess.run(
            ["gh", "run", "view", str(run_id), "--json", "jobs"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"gh CLI error: {result.stderr}", file=sys.stderr)
            return []
        jobs = json.loads(result.stdout).get("jobs", [])
        return [j["name"] for j in jobs if j.get("conclusion") == "failure"]
    except FileNotFoundError:
        print("gh CLI not found. Install: https://cli.github.com/", file=sys.stderr)
        return []


def get_repo_url():
    """Get the GitHub repo URL from git remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10,
        )
        url = result.stdout.strip()
        if url.startswith("git@github.com:"):
            url = url.replace("git@github.com:", "https://github.com/").rstrip(".git")
        return url.rstrip(".git")
    except Exception:
        return "https://github.com/OWNER/REPO"


def create_ci_bug(run_id, failed_jobs, branch):
    """Create or update a CI failure task in Aztec Plataforma (idempotent)."""
    repo_url = get_repo_url()
    title = f"[CI-BRIDGE] CI failed on {branch}"
    body_markdown = f"""## CI Failure Report

**Run ID**: {run_id}
**Branch**: `{branch}`
**Failed jobs**: {', '.join(failed_jobs) if failed_jobs else 'unknown'}

[Ver run en GitHub]({repo_url}/actions/runs/{run_id})
"""

    # Check for existing open bridge task (idempotent — no duplicates)
    existing = search_tasks_by_title("[CI-BRIDGE]")
    # Filter to only open tasks (not in "Hecho")
    open_bridge = [
        t for t in existing
        if t.get("_column_name", "") != "Hecho"
    ]

    if open_bridge:
        # Add comment to existing task instead of creating duplicate
        task = open_bridge[0]
        task_key = task.get("task_key", task.get("id"))
        add_comment(
            task_key,
            f"CI failed again on `{branch}`\n\n**Jobs**: {', '.join(failed_jobs)}\n\n"
            f"[Run {run_id}]({repo_url}/actions/runs/{run_id})"
        )
        print(f"Updated existing CI bridge task {task_key}")
    else:
        task = create_task(title, body_markdown, priority="alta")
        if task:
            key = task.get("task_key", task.get("id", "?"))
            print(f"Created new CI bridge task: {key}  {title}")
        else:
            print("Failed to create CI bridge task.", file=sys.stderr)
            sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    run_id = sys.argv[1]
    branch = os.environ.get("GITHUB_HEAD_REF", "unknown")
    failed = get_failed_jobs(run_id)

    if failed:
        print(f"CI failed on {branch}. Failed jobs: {', '.join(failed)}")
        create_ci_bug(run_id, failed, branch)
    else:
        print(f"No failed jobs found for run {run_id}. Creating generic bridge task.")
        create_ci_bug(run_id, ["unknown"], branch)


if __name__ == "__main__":
    main()
