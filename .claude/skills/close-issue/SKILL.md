---
name: close-issue
description: Close a platform task with evidence — runs 3 gates (tests, CI, acceptance criteria) before closing
user-invocable: true
allowed-tools: Bash(git *) Bash(gh *) Bash(npm test*) Bash(python3 scripts/*) Bash(bash scripts/*)
argument-hint: "<TASK_KEY> (e.g., AZT-1)"
---

# Close Issue

Close Aztec Plataforma task `$ARGUMENTS` with mechanical verification.

## Steps

1. **Run the harness gate script**:
   ```bash
   bash scripts/close_issue.sh $0
   ```
   This runs 3 gates:
   - **Gate 1**: Tests passing? (`npm test`)
   - **Gate 2**: CI green? (`gh run list`)
   - **Gate 3**: Acceptance criteria all checked? (Aztec Plataforma API)

2. **If ALL gates pass**:
   The script automatically:
   - Posts evidence comment to the task in Aztec Plataforma
   - Moves task to "Hecho"
   - Report: `Task $0 closed with evidence.`

3. **If ANY gate fails**:
   - Report which gate failed and why
   - Do NOT close the task
   - Suggest what the user needs to fix

## Rules

- NEVER close a task if a gate fails.
- NEVER use workarounds to bypass gates.
- NEVER close tasks manually in Aztec Plataforma — always use this skill.
- The user must fix the root cause, then run `/close-issue` again.
