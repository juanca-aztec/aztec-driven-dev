---
name: start-issue
description: Start work on a platform task — fetch details, create branch, move to En curso
user-invocable: true
allowed-tools: Bash(git *) Bash(python3 scripts/*)
argument-hint: "<TASK_KEY> (e.g., AZT-1)"
---

# Start Issue

Begin work on Aztec Plataforma task `$ARGUMENTS`.

## Steps

1. **Fetch task from Aztec Plataforma**:
   ```bash
   python3 scripts/platform_client.py get $0
   ```
   Show the user: title, description, acceptance criteria.

2. **Create a feature branch** from the task metadata:
   ```bash
   git checkout -b feat/$0-<slugified-title>
   ```
   Use the task title to generate a short kebab-case slug.

3. **Move to En curso** in Aztec Plataforma:
   ```bash
   python3 scripts/platform_client.py move $0 "En curso"
   ```

4. **Confirm** to the user:
   ```
   Task $0 started.
   Branch: feat/$0-<slug>
   Status: En curso
   ```

## Rules

- NEVER start coding without running this skill first.
- If the task does not exist, stop and inform the user.
- If already on a feature branch for this task, skip branch creation.
