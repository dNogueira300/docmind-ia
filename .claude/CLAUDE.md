# DocMind IA — Contexto para Claude Code

Proyecto académico UNAP 2026. Sistema de gestión documental inteligente con IA.
Equipo: Error 404 | Repo: https://github.com/dNogueira300/docmind-ia

---

## Antes de cualquier tarea

1. Revisar las skills del proyecto disponibles
2. Consultar el plan de desarrollo en `plan_desarrollo_docmind_ia.md` si hay dudas sobre el alcance

---

## Stack tecnológico

| Capa          | Tecnología                                       |
| ------------- | ------------------------------------------------ |
| Backend       | Python 3.11 + FastAPI + SQLAlchemy + Alembic     |
| Frontend      | React.js + Tailwind CSS + Axios                  |
| Base de datos | PostgreSQL 15 (full-text search en español)      |
| OCR           | Tesseract OCR / Google Cloud Vision API          |
| IA / NLP      | HuggingFace Transformers — modelo BETO (español) |
| Storage       | MinIO                                            |
| Auth          | JWT + bcrypt                                     |
| DevOps        | Docker + docker-compose                          |
| VCS           | Git + GitHub                                     |

---

## Estructura del repositorio

```
docmind-ia/
├── .claude/
│   ├── CLAUDE.md                          ← este archivo
│   └── skills/
│       ├── docmind-conventions/SKILL.md
│       ├── fastapi-patterns/SKILL.md
│       ├── react-patterns/SKILL.md
│       └── db-migrations/SKILL.md
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints FastAPI
│   │   ├── models/       # Modelos SQLAlchemy
│   │   ├── services/     # Lógica de negocio (OCR, IA, auditoría)
│   │   └── core/         # Config, auth, seguridad
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/     # Llamadas a la API (Axios)
│   └── package.json
├── ml/
│   ├── training/
│   └── models/
├── db/
│   └── migrations/
│       └── 001_initial_schema.sql
├── docker-compose.yml
├── .env
└── plan_desarrollo_docmind_ia.md
```

---

## Comandos frecuentes

```bash
# Levantar el stack completo
docker compose up -d

# Ver logs del backend en tiempo real
docker compose logs backend -f

# Correr migraciones
cd backend && alembic upgrade head

# Correr tests
cd backend && pytest

# Ver migración actual
cd backend && alembic current

# Instalar dependencias frontend
cd frontend && npm install

# Levantar frontend en desarrollo
cd frontend && npm run dev
```

---

## Ramas Git

| Rama               | Propósito                                                  |
| ------------------ | ---------------------------------------------------------- |
| `main`             | Protegida. Solo merge desde `develop`. Nunca push directo. |
| `develop`          | Rama de integración. Todos los PR van aquí.                |
| `feature/backend`  | API REST, servicios, modelos                               |
| `feature/frontend` | Interfaz React.js                                          |
| `feature/ai`       | Módulo OCR y clasificador NLP                              |
| `feature/db`       | Esquema y migraciones                                      |

### Formato de commits (Conventional Commits)

```
tipo(scope): descripción en minúsculas

feat(backend): agregar endpoint POST /documents/upload
fix(auth): corregir validación de token JWT expirado
docs(readme): actualizar instrucciones de instalación
chore(docker): configurar servicio MinIO en docker-compose
test(backend): agregar pruebas para módulo de auditoría
refactor(db): renombrar columna stored_path
```

---

## Reglas de negocio críticas

- SIEMPRE verificar que `organization_id` del usuario coincide con el recurso al que accede
- SIEMPRE registrar en `audit_log` toda operación sobre documentos: `upload`, `view`, `download`, `reclassify`, `delete`
- La tabla `audit_log` es INMUTABLE: nunca emitir UPDATE ni DELETE sobre ella, solo INSERT
- El clasificador IA retorna un `ai_confidence_score` entre 0.0 y 1.0:
  - Score >= 0.70 → clasificar automáticamente
  - Score < 0.70 → asignar status `review` para revisión manual
- Al eliminar una categoría, los documentos asociados pasan a `category_id = NULL`, NO se eliminan
- El endpoint de subida responde inmediatamente con `status: pending`; el OCR y la IA corren en background

### Roles y permisos

| Acción                  | admin | editor | consultor |
| ----------------------- | ----- | ------ | --------- |
| Subir documentos        | ✓     | ✓      | —         |
| Buscar y ver documentos | ✓     | ✓      | ✓         |
| Descargar documentos    | ✓     | ✓      | ✓         |
| Reclasificar documentos | ✓     | ✓      | —         |
| Gestionar categorías    | ✓     | —      | —         |
| Gestionar usuarios      | ✓     | —      | —         |
| Ver auditoría           | ✓     | —      | —         |

---

## Paleta de colores — DocMind IA

### Filosofía de diseño — "Deep Navy Tech"

Categoría: **Tech & SaaS** (resultado del design system ui-ux-pro-max).
Estilo: **Dark Mode OLED + Swiss Precision**. Fondo navy ultra-profundo (no negro puro) optimizado para pantallas OLED. Azul tech brillante como primario de acción, índigo-violeta como acento IA. Tipografía: **Space Grotesk** (headings/labels) + **DM Sans** (body). Todos los pares de texto cumplen WCAG AA o AAA.

**Contrastes garantizados dark:**
- Texto primario `#ECF0FF` sobre `#060D1B` → ~17:1 (AAA)
- Texto secondary `#97AED1` sobre `#060D1B` → ~7.5:1 (AAA)
- Texto muted `#5C789E` sobre `#060D1B` → ~4.8:1 (AA)

**Contrastes garantizados light:**
- Texto primario `#080F20` sobre `#F1F5FB` → ~18:1 (AAA)
- Texto secondary `#344B6E` sobre `#F1F5FB` → ~8.5:1 (AAA)
- Texto muted `#6480A0` sobre `#F1F5FB` → ~5.2:1 (AA)

### Colores primarios — Azul Tech

| Token                    | Light       | Dark                       | Uso                                       |
| ------------------------ | ----------- | -------------------------- | ----------------------------------------- |
| `--color-primary`        | `#1A5FE8`   | `#2D7FF9`                  | Botones primarios, links, focus rings     |
| `--color-primary-hover`  | `#2D7FF9`   | `#4D95FF`                  | Hover sobre elementos primarios           |
| `--color-primary-active` | `#1248C4`   | `#1A65E0`                  | Estado activo / pressed                   |
| `--color-primary-subtle` | `#EBF3FF`   | `rgba(45,127,249,0.13)`    | Fondos tintados, badge info, selected row |
| `--color-primary-border` | `#B5D0FB`   | `rgba(45,127,249,0.30)`    | Bordes de elementos info / selected       |

### Acento IA — Índigo Violeta

| Token               | Light     | Dark                    | Uso                                      |
| ------------------- | --------- | ----------------------- | ---------------------------------------- |
| `--color-ai-accent` | `#5046D4` | `#7059F5`               | Score badge, clasificador, elementos NLP |
| `--color-ai-subtle` | `#EDEAFF` | `rgba(112,89,245,0.13)` | Fondo de badges IA                       |

### Fondos y superficies

| Token                  | Light       | Dark        | Uso                                    |
| ---------------------- | ----------- | ----------- | -------------------------------------- |
| `--color-bg-page`      | `#F1F5FB`   | `#060D1B`   | Fondo general de la página             |
| `--color-bg-surface`   | `#FFFFFF`   | `#0C1525`   | Tarjetas, paneles, modales             |
| `--color-bg-surface-2` | `#E8EFF8`   | `#111E36`   | Inputs, stat cards, filas alternas     |
| `--color-bg-surface-3` | `#DAE4F2`   | `#182745`   | Elementos elevados, tooltips           |

### Texto

| Token                    | Light       | Dark        | Uso                                |
| ------------------------ | ----------- | ----------- | ---------------------------------- |
| `--color-text-primary`   | `#080F20`   | `#ECF0FF`   | Texto principal, headings          |
| `--color-text-secondary` | `#344B6E`   | `#97AED1`   | Texto secundario, labels           |
| `--color-text-muted`     | `#6480A0`   | `#5C789E`   | Placeholders, metadata, timestamps |

### Bordes

| Token                  | Light       | Dark                       |
| ---------------------- | ----------- | -------------------------- |
| `--color-border`       | `#C5D4EC`   | `rgba(99,140,210,0.16)`    |
| `--color-border-light` | `#D8E5F5`   | `rgba(99,140,210,0.09)`    |

### Estados semánticos de documentos

| Token                | Light       | Dark                       | Status                   | Uso                                           |
| -------------------- | ----------- | -------------------------- | ------------------------ | --------------------------------------------- |
| `--color-success`    | `#16A34A`   | `#2DD88A`                  | `classified`             | Documento clasificado correctamente           |
| `--color-success-bg` | `#DCFCE7`   | `rgba(45,216,138,0.12)`    | —                        | Fondo badge classified                        |
| `--color-warning`    | `#D97706`   | `#F5C53A`                  | `pending` / `processing` | En cola o procesando                          |
| `--color-warning-bg` | `#FEF3C7`   | `rgba(245,197,58,0.12)`    | —                        | Fondo badge pending                           |
| `--color-error`      | `#DC2626`   | `#F55858`                  | `error`                  | Error en OCR o clasificación                  |
| `--color-error-bg`   | `#FEE2E2`   | `rgba(245,88,88,0.12)`     | —                        | Fondo badge error                             |
| `--color-review`     | `#7C3AED`   | `#B07EF5`                  | `review`                 | Confianza IA < 0.70, requiere revisión humana |
| `--color-review-bg`  | `#EDE9FE`   | `rgba(176,126,245,0.12)`   | —                        | Fondo badge review                            |

### Variables especiales del panel branding (Login)

```css
/* Aplican sobre fondo azul (light) o fondo navy (dark) — siempre sobre fondo oscuro/saturado */
--color-brand-panel-grid:      rgba(255,255,255,0.04);   /* líneas del grid */
--color-brand-text:            rgba(255,255,255,0.92);   /* título principal */
--color-brand-text-dim:        rgba(255,255,255,0.62);   /* descripción */
--color-brand-text-feat:       rgba(255,255,255,0.72);   /* features list */
--color-brand-icon-bg:         rgba(255,255,255,0.12);   /* fondo iconos */
--color-brand-icon-border:     rgba(255,255,255,0.18);   /* borde iconos */
--color-brand-icon-color:      rgba(255,255,255,0.82);   /* color iconos */

/* Difieren por tema: */
/* light: */ --color-brand-panel-glow:      rgba(255,255,255,0.08);
/* dark:  */ --color-brand-panel-glow:      rgba(45,127,249,0.07);
/* light: */ --color-brand-headline-accent: rgba(191,219,254,1);
/* dark:  */ --color-brand-headline-accent: #4D95FF;
```

### Tipografía

```css
--font-display: 'Space Grotesk', system-ui, sans-serif;  /* headings h1–h6 */
--font-sans:    'DM Sans', system-ui, sans-serif;         /* body, UI labels */
```

---

## Convenciones de código

### Python (backend)

- `snake_case` para variables, funciones y archivos
- Type hints obligatorios en todas las funciones
- Docstrings en funciones públicas
- Máximo 88 caracteres por línea (Black formatter)

### JavaScript / React (frontend)

- `camelCase` para variables y funciones
- `PascalCase` para componentes React
- Prefijo `use` para hooks personalizados (`useDocuments`, `useAuth`)
- Archivos de componentes: `NombreComponente.jsx`
- Archivos de páginas: `NombrePagina.jsx` dentro de `pages/`

### SQL

- `UPPER_CASE` para keywords SQL
- `snake_case` para nombres de tablas y columnas
- UUIDs como primary keys (no enteros autoincrementales)
- Siempre incluir `created_at TIMESTAMP NOT NULL DEFAULT NOW()`
