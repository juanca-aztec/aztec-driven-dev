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

2. **Validate acceptance criteria** — inspect `body_markdown` of the fetched task:

   - If `body_markdown` does **NOT** contain `- [ ]` (i.e., no checklist items):
     1. Inform the user: "Esta tarea no tiene criterios de aceptación definidos."
     2. Ask: "Por favor describe qué quieres lograr con esta tarea."
     3. Wait for the user's response, then generate a full markdown template:
        ```
        ## Objetivo
        <one-line summary from user input>

        ## Descripción
        <expanded description based on user input>

        ## Criterios de Aceptación
        - [ ] <measurable criterion 1>
        - [ ] <measurable criterion 2>
        - [ ] <measurable criterion 3>

        ## Notas Técnicas
        <any relevant technical notes>
        ```
     4. Update the task with the generated template:
        ```bash
        python3 scripts/platform_client.py update $0 "<TEMPLATE>"
        ```
     5. Confirm to the user that the task was updated with acceptance criteria.
   - If `body_markdown` **contains** `- [ ]`: continue normally to the next step.

3. **Create a feature branch** from the task metadata:
   ```bash
   git checkout -b feat/$0-<slugified-title>
   ```
   Use the task title to generate a short kebab-case slug.

4. **Move to En curso** in Aztec Plataforma:
   ```bash
   python3 scripts/platform_client.py move $0 "En curso"
   ```

5. **Confirm** to the user:
   ```
   Task $0 started.
   Branch: feat/$0-<slug>
   Status: En curso
   ```

## Rules

- NEVER start coding without running this skill first.
- If the task does not exist, stop and inform the user.
- If already on a feature branch for this task, skip branch creation.
