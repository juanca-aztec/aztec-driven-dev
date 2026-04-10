---
name: create-issue
description: Create a well-documented task in Aztec Plataforma with objective, description, acceptance criteria, and technical notes
user-invocable: true
allowed-tools: Bash(python3 scripts/*)
argument-hint: "<TITLE> [details]"
---

# Create Issue

Create a well-documented task in Aztec Plataforma following a standard template.

## Usage Examples

```
/create-issue Add dark mode toggle
/create-issue Agregar contador de tareas por columna
/create-issue Fix login bug on mobile
```

## Language

Detect the language from the user's request:
- If the user writes in **Spanish**, use the Spanish template
- If the user writes in **English**, use the English template
- If unclear, default to Spanish

## Steps

1. **Parse the request**: Extract the title and any details the user provides.

2. **Build the description** using the template for the detected language:

### Spanish Template (default for this project)

```markdown
## Objetivo
Breve descripción de lo que logra este issue y por qué es importante.

## Descripción
Explicación detallada de la feature, bug o tarea. Incluye contexto
que ayude a entender el alcance y el enfoque.

## Criterios de Aceptación
- [ ] Primer criterio medible
- [ ] Segundo criterio medible
- [ ] Tercer criterio medible

## Notas Técnicas
- Archivos, componentes o áreas del código relevantes
- Dependencias o restricciones
- Enfoque sugerido (si aplica)
```

### English Template

```markdown
## Objective
Brief description of what this issue accomplishes and why it matters.

## Description
Detailed explanation of the feature, bug, or task. Include context
that helps understand the scope and approach.

## Acceptance Criteria
- [ ] First measurable criterion
- [ ] Second measurable criterion
- [ ] Third measurable criterion

## Technical Notes
- Relevant files, components, or areas of the codebase
- Dependencies or constraints
- Suggested approach (if applicable)
```

3. **Create the task**:
   ```bash
   python3 scripts/platform_client.py create "<TITLE>" "<DESCRIPTION>"
   ```

4. **Confirm** to the user showing the task key (e.g., AZT-5) and title.

## Template Rules

- **Objetivo/Objective**: Always include. One sentence explaining the "what" and "why".
- **Descripción/Description**: Always include. 2-3 sentences with context, scope, and approach.
- **Criterios de Aceptación/Acceptance Criteria**: Always include. Each criterion must be:
  - Specific and measurable (not vague like "funciona bien" / "works well")
  - Testable (can be verified as done or not done)
  - Written as `- [ ]` checkboxes (the harness gate 3 checks these)
- **Notas Técnicas/Technical Notes**: Include when relevant.

## Examples of Good vs Bad Criteria

**Bad / Mal:**
- [ ] Dark mode works / El dark mode funciona
- [ ] Looks good / Se ve bien

**Good / Bien:**
- [ ] Toggle button visible in the header / Botón toggle visible en el header
- [ ] Clicking toggle switches styles / Al hacer click cambia los estilos
- [ ] Preference persists via localStorage / La preferencia se guarda en localStorage

## Rules

- If the user gives a vague request, infer reasonable criteria from the project context.
- If the user only gives a title, generate the full description based on the project (Task Board).
- Every task must have at least: Objetivo, Descripción, and Criterios de Aceptación.
