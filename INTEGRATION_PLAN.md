# Plan de Integración: Harness ↔ Aztec Plataforma

## Objetivo

Reemplazar Linear como tracker del harness por **pixel-plan-grid** (la plataforma propia de Aztec).
En lugar de que los skills hablen con la API de Linear via GraphQL, hablarán con la API REST de pixel-plan-grid.

Esto convierte el sistema en **dog-fooding real**: la plataforma se usa a sí misma para gestionar su propio desarrollo.

---

## Diagnóstico: qué tiene cada proyecto hoy

### harness-driven-dev (aztec-driven-dev)
- `linear_client.py` — cliente GraphQL de 380 líneas para Linear
- 4 skills: `/start-issue`, `/close-issue`, `/create-issue`, `/status`
- `close_issue.sh` — 3 gates: tests, CI, criterios de aceptación (lee checkboxes de Linear)
- `ci_failure_bridge.py` — crea bugs en Linear cuando CI falla
- `.env` con `LINEAR_API_KEY` y `LINEAR_TEAM_KEY`
- Issues se referencian como `DEMO-5` en commits

### pixel-plan-grid
- API REST en Supabase Edge Functions (`api-gateway`)
- Endpoints: proyectos, tareas, columnas, comentarios, dependencias
- Tareas identificadas por **UUID** (no hay short key tipo `HAR-5`)
- 5 columnas globales: Sin empezar → En espera → Sprint semanal → En curso → Hecho
- Autenticación: API Key via Bearer token
- Webhooks: task.created, task.moved, task.assigned, task.completed
- `body_markdown` en tareas soporta checkboxes `[x]` / `[ ]`

---

## Problema central: el short key

El harness usa IDs legibles en commits: `Refs HAR-5`.
pixel-plan-grid solo tiene UUIDs como `3f2a1b9c-...`.

Nadie va a escribir `Refs 3f2a1b9c-4d5e-...` en un commit.

**Solución:** agregar un campo `task_key` a las tareas con formato `{PREFIX}-{N}`.
Ejemplo: `AZT-5`, `AZT-12`. El prefijo lo define el proyecto.

---

## Cambios necesarios

### Repo 1: pixel-plan-grid

#### Base de datos (Supabase — migración)

**1. Agregar `prefix` a proyectos**
```sql
ALTER TABLE projects ADD COLUMN prefix text;
-- Ejemplo: 'AZT', 'HAR', 'PPG'
```

**2. Agregar `task_key` a tareas (auto-generado)**
```sql
ALTER TABLE tasks ADD COLUMN task_key text UNIQUE;
-- Generado como: '{project.prefix}-{sequential_number}'
-- Trigger: se calcula al insertar, usando el prefijo del proyecto padre
```

El trigger incrementa un contador por proyecto para garantizar que los números sean secuenciales y únicos dentro del proyecto.

---

#### Backend — Edge Function `api-gateway`

**3. Exponer `task_key` en todos los endpoints de tareas**
- `GET /tasks` → incluir `task_key` en la respuesta
- `POST /tasks` → el key se genera automáticamente (no lo manda el cliente)
- `GET /tasks/:id` → incluir `task_key`
- Nuevo: `GET /tasks/by-key/:key` → buscar tarea por `task_key` (ej: `AZT-5`)

**4. Exponer `prefix` en proyectos**
- `POST /projects` → aceptar campo `prefix` opcional
- `GET /projects` → incluir `prefix` en respuesta

---

#### Frontend — pixel-plan-grid

**5. Campo `prefix` en creación/edición de proyectos**

En el formulario de crear/editar proyecto, agregar un campo de texto corto (2-5 chars, uppercase automático):

```
Nombre del proyecto: [Aztec Plataforma      ]
Prefijo:             [AZT]  ← nuevo campo
```

Si no se llena, se auto-genera de las primeras 3 letras del nombre.

**6. Mostrar `task_key` en las task cards del Kanban**

En `TaskCard.tsx`, mostrar el key como badge pequeño en la esquina superior derecha de la card:

```
┌─────────────────────────────┐
│ AZT-12             [media]  │  ← AZT-12 es nuevo
│ Implementar dark mode       │
│ ● Juan  📅 15 ene    3pts   │
└─────────────────────────────┘
```

**7. Mostrar `task_key` en el `TaskDetailPanel`**

En el panel derecho de detalle, mostrar el key junto al título y agregar un botón de copiar:

```
AZT-12  [copiar]
Implementar dark mode
──────────────────────
```

Copiar al portapapeles el formato listo para commit: `Refs AZT-12`.

**8. Buscar tareas por `task_key` en el `FilterBar`**

El buscador de texto ya existe. Agregar soporte para que si el usuario escribe `AZT-12`, también busque por `task_key` además de por título.

**9. Mostrar `task_key` en el `ActivityLog`**

Cuando el harness publica evidencia como comentario, ese comentario aparece en la pestaña **Comments** del `TaskDetailPanel`. No requiere cambios en el componente — ya funciona con `body_markdown`. Solo hay que asegurarse de que el formato de evidencia del harness sea markdown válido.

---

### Repo 2: harness-driven-dev (aztec-driven-dev)

#### Scripts

**10. Reemplazar `linear_client.py` → `platform_client.py`**

Nuevo cliente REST (Python stdlib, sin pip) para pixel-plan-grid.
Mismas funciones que el cliente de Linear, nueva implementación:

| Función Linear | Función nueva | Endpoint |
|---|---|---|
| `get_issue(id)` | `get_task(key)` | `GET /tasks/by-key/{key}` |
| `update_issue_state(id, state)` | `move_task(key, column_name)` | `PATCH /tasks/{id}/move` |
| `add_comment(id, body)` | `add_comment(key, body)` | `POST /tasks/{id}/comments` |
| `list_issues(state)` | `list_tasks(column_name)` | `GET /tasks?status={column}` |
| `create_issue(title, body)` | `create_task(title, body)` | `POST /tasks` |

Variables de entorno nuevas:
```
PLATFORM_API_KEY=your_api_key_here
PLATFORM_BASE_URL=https://rbyraluapzywfrouluwh.supabase.co/functions/v1
PLATFORM_PROJECT_ID=uuid_del_proyecto
```

**11. Actualizar `close_issue.sh`**

El Gate 3 (criterios de aceptación) hoy lee el body del issue en Linear y cuenta checkboxes `[x]`.
Con el nuevo cliente, leerá el `body_markdown` de la tarea en pixel-plan-grid. La lógica de conteo de checkboxes no cambia.

El bloque de evidencia final se publica como comentario via `platform_client.py add_comment`.

**12. Actualizar `ci_failure_bridge.py`**

Hoy crea/actualiza bugs en Linear. Con el cambio, usará `platform_client.py` para:
- Buscar si ya existe una tarea con `[CI-BRIDGE]` en el título
- Si no: `create_task("[CI-BRIDGE] CI failure: {run_id}", body_markdown)`
- Si sí: `add_comment(key, nuevo_detalle)`

**13. Actualizar `.env.example`**

```env
# Antes
LINEAR_API_KEY=lin_api_your_key_here
LINEAR_TEAM_KEY=DEMO

# Después
PLATFORM_API_KEY=your_api_key_from_settings
PLATFORM_BASE_URL=https://<project>.supabase.co/functions/v1
PLATFORM_PROJECT_ID=uuid_del_proyecto_en_aztec_plataforma
```

---

#### Skills de Claude Code

**14. Actualizar `/start-issue`**

```
Antes: linear_client.py get DEMO-5
Después: platform_client.py get AZT-5
```

Cambios adicionales:
- El nombre del branch se genera del `task_key` + título: `feat/AZT-5-dark-mode-toggle`
- Mover tarea a columna "En curso" (en lugar de estado "In Progress" de Linear)

**15. Actualizar `/close-issue`**

Solo cambia la invocación del script. Los gates son los mismos.
El skill sigue llamando a `close_issue.sh AZT-5`.

**16. Actualizar `/create-issue`**

Crea tarea en pixel-plan-grid via `platform_client.py create`.
El formato de criterios de aceptación como checkboxes markdown sigue igual — se guarda en `body_markdown`.

**17. Actualizar `/status`**

```
Antes: lista issues de Linear agrupados por estado
Después: lista tareas de pixel-plan-grid agrupadas por columna
```

Columnas a mostrar: Sin empezar, Sprint semanal, En curso, Hecho.

**18. Actualizar `CLAUDE.md`**

- Reemplazar referencias a "Linear" por "Aztec Plataforma"
- Reemplazar `LINEAR_API_KEY` / `LINEAR_TEAM_KEY` por las nuevas vars
- Actualizar formato de IDs: `DEMO-5` → `AZT-5` (o el prefijo del proyecto)

---

## Orden de ejecución recomendado

```
Fase 1 — Base de datos (pixel-plan-grid)
  [ ] Migración: agregar `prefix` a projects
  [ ] Migración: agregar `task_key` a tasks + trigger de auto-generación

Fase 2 — Backend (pixel-plan-grid)
  [ ] Exponer `task_key` en endpoints existentes
  [ ] Nuevo endpoint: GET /tasks/by-key/:key
  [ ] Aceptar `prefix` en POST/PATCH /projects

Fase 3 — Frontend (pixel-plan-grid)
  [ ] Campo `prefix` en formulario de crear/editar proyecto
  [ ] Badge `task_key` en TaskCard
  [ ] Key + botón copiar en TaskDetailPanel
  [ ] Soporte búsqueda por task_key en FilterBar

Fase 4 — Harness (aztec-driven-dev)
  [ ] Escribir platform_client.py
  [ ] Actualizar close_issue.sh
  [ ] Actualizar ci_failure_bridge.py
  [ ] Actualizar los 4 skills
  [ ] Actualizar .env.example y CLAUDE.md

Fase 5 — Prueba de humo
  [ ] Crear proyecto en pixel-plan-grid con prefijo "AZT"
  [ ] Crear tarea → verificar que se genera AZT-1
  [ ] /start-issue AZT-1 → verifica branch + columna "En curso"
  [ ] Commit con "Refs AZT-1" → hook lo acepta
  [ ] /close-issue AZT-1 → 3 gates + comentario de evidencia en la tarea
```

---

## Lo que NO cambia

- Los 3 gates de `close_issue.sh` (tests, CI, criterios)
- El pre-commit hook `check_issue_ref.sh` (solo cambia el prefijo esperado)
- La estructura de GitHub Actions (CI sigue igual)
- El formato de commits: `feat: descripción. Refs AZT-5`
- La lógica de criterios de aceptación (checkboxes en markdown)
- El concepto del harness — solo cambia con qué sistema habla

---

## Beneficio neto

| Aspecto | Antes | Después |
|---|---|---|
| Tracker | Linear (externo, de pago) | pixel-plan-grid (propio, gratis) |
| API | GraphQL complejo, 380 líneas | REST simple, ~150 líneas |
| Visibilidad | En Linear, separado del flujo | En la misma plataforma donde vive el trabajo |
| Dog-fooding | No | Sí — se usa la herramienta para desarrollar la herramienta |
| Dependencias externas | Linear account requerida | Solo Supabase (ya existe) |
