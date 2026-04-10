---
name: status
description: Display project status dashboard — Aztec Plataforma tasks, current branch, CI status
user-invocable: true
allowed-tools: Bash(git *) Bash(gh *) Bash(python3 scripts/*)
---

# Project Status

Display a dashboard of the current project state.

## Steps

1. **Aztec Plataforma tasks**:
   ```bash
   python3 scripts/platform_client.py list
   ```
   This fetches tasks from **all active projects** (when PLATFORM_PROJECT_ID is not set)
   or from the configured single project.
   Show all tasks grouped first by **project**, then by **column** (Sin empezar, Sprint semanal, En curso, Hecho).

2. **Current branch**:
   ```bash
   git branch --show-current
   ```

3. **Recent commits**:
   ```bash
   git log --oneline -5
   ```

4. **Last CI run**:
   ```bash
   gh run list --limit 1
   ```

5. **Format as dashboard**:
   ```
   ┌──────────────────────────────────────────┐
   │              PROJECT STATUS              │
   ├──────────────────────────────────────────┤
   │ Branch: feat/PLY-3-6-multi-project       │
   │                                          │
   │ HDD Playground [PLY]                     │
   │   Sin empezar:                           │
   │     PLY-2  [Sin empezar]  ...            │
   │   En curso:                              │
   │     PLY-1  [En curso]     ...            │
   │                                          │
   │ Aztec Core [AZT]                         │
   │   En curso:                              │
   │     AZT-5  [En curso]     ...            │
   │                                          │
   │ CI: Last run passed (2m ago)             │
   └──────────────────────────────────────────┘
   ```

## If a task key is provided (`/status PLY-1`)

Show detailed info for that specific task:
```bash
python3 scripts/platform_client.py get $0 --full
```
Include: column, description, acceptance criteria.
