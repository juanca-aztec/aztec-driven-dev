# CLAUDE.md — Harness-Driven Development

## Project

This is a demo Task Board (vanilla HTML/CSS/JS) used to demonstrate
Harness-Driven Development: an approach where an AI agent enforces
software best practices mechanically via scripts, hooks, and gates.

The harness connects Aztec Plataforma (project management) with GitHub (code)
through automated enforcement.

## Skills

The agent has 4 skills that connect with the harness:

| Skill | When to use |
|-------|-------------|
| `/create-issue <title>` | Create a new task in Aztec Plataforma with acceptance criteria. |
| `/start-issue AZT-X` | ALWAYS before writing code. Reads platform task, creates branch, moves to En curso. |
| `/close-issue AZT-X` | ALWAYS to finish work. Runs 3 gates (tests + CI + criteria), posts evidence, moves to Hecho. |
| `/status` | Check project dashboard: tasks, branch, CI status. |

> **Note**: `AZT-X` is used as an example. Replace with your actual project prefix and task number (e.g., `AZT-5`, `PPG-1`). The prefix is set when creating the project in Aztec Plataforma.

## Harness Rules

1. **No code without issue**: Before touching code, run `/start-issue`.
2. **Refs, never Closes**: Commit messages MUST contain `Refs AZT-XXX`.
   NEVER use `Closes`, `Fixes`, or `Resolves` — they bypass harness gates.
3. **Mechanical Definition of Done**: Use `/close-issue` to close tasks.
   NEVER close manually in Aztec Plataforma. The harness runs 3 gates first.
4. **No secrets in code**: gitleaks blocks commits with secrets automatically.
5. **Evidence always**: Every task closure includes an audit trail comment in Aztec Plataforma.

## Commit Message Format

```
<type>: <short description>

<optional body>

Refs AZT-XXX
```

Types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/platform_client.py` | REST client for Aztec Plataforma API (get, move, comment, list, create, projects) |
| `scripts/close_issue.sh` | Gate script: tests + CI + acceptance criteria |
| `scripts/check_issue_ref.sh` | Commit-msg hook: enforces `Refs AZT-XXX` |
| `scripts/ci_failure_bridge.py` | Auto-creates platform task when CI fails |

### Required environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `PLATFORM_API_KEY` | Yes | API key for Aztec Plataforma |
| `PLATFORM_BASE_URL` | Yes | Base URL of the Supabase edge functions |
| `PLATFORM_PROJECT_ID` | No | UUID of a specific project. Optional — `list` and `projects` work without it (fetches all active projects). Only required for `create` when not passing `--project-id` interactively. |

## Tech Stack

- Frontend: HTML + CSS + vanilla JS (no frameworks)
- Tests: Node.js + jsdom
- Harness scripts: Python 3 (stdlib only) + Bash
- CI: GitHub Actions
- Project management: Aztec Plataforma (pixel-plan-grid)
