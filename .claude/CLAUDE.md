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

### Filosofía de diseño

Moderno y tech (SaaS / IA). Fondo off-white en modo claro. Azul como color primario de acción, índigo como acento exclusivo de elementos IA.

### Colores primarios — Azul

| Token                    | Hex       | Uso                                       |
| ------------------------ | --------- | ----------------------------------------- |
| `--color-primary`        | `#2563D4` | Botones primarios, links, focus rings     |
| `--color-primary-hover`  | `#1A4DB8` | Hover sobre elementos primarios           |
| `--color-primary-active` | `#133A94` | Estado activo / pressed                   |
| `--color-primary-subtle` | `#EBF2FF` | Fondos tintados, badge info, selected row |
| `--color-primary-border` | `#C3D8FE` | Bordes de elementos info / selected       |

### Acento IA — Índigo

| Token               | Hex       | Uso                                      |
| ------------------- | --------- | ---------------------------------------- |
| `--color-ai-accent` | `#4F5FE8` | Score badge, clasificador, elementos NLP |
| `--color-ai-hover`  | `#6B7FF0` | Hover sobre elementos IA                 |
| `--color-ai-subtle` | `#EEF0FD` | Fondo de badges IA                       |

### Neutros — Slate

| Token                    | Hex       | Uso                                    |
| ------------------------ | --------- | -------------------------------------- |
| `--color-text-primary`   | `#0F1623` | Texto principal, headings              |
| `--color-text-secondary` | `#4A5568` | Texto secundario, labels               |
| `--color-text-muted`     | `#8896A9` | Placeholders, metadata, timestamps     |
| `--color-border`         | `#E2E6ED` | Bordes de tarjetas, inputs, divisores  |
| `--color-bg-page`        | `#F7F8FA` | Fondo general de la página (off-white) |
| `--color-bg-surface`     | `#FFFFFF` | Tarjetas, paneles, modales             |
| `--color-bg-surface-2`   | `#EFF1F5` | Inputs, stat cards, filas alternas     |

### Estados semánticos de documentos

| Token                | Hex       | Status                   | Uso                                           |
| -------------------- | --------- | ------------------------ | --------------------------------------------- |
| `--color-success`    | `#16A34A` | `classified`             | Documento clasificado correctamente           |
| `--color-success-bg` | `#DCFCE7` | —                        | Fondo badge classified                        |
| `--color-warning`    | `#D97706` | `pending` / `processing` | En cola o procesando                          |
| `--color-warning-bg` | `#FEF3C7` | —                        | Fondo badge pending                           |
| `--color-error`      | `#DC2626` | `error`                  | Error en OCR o clasificación                  |
| `--color-error-bg`   | `#FEE2E2` | —                        | Fondo badge error                             |
| `--color-review`     | `#7C3AED` | `review`                 | Confianza IA < 0.70, requiere revisión humana |
| `--color-review-bg`  | `#F3E8FF` | —                        | Fondo badge review                            |

### Modo oscuro

| Token claro              | Valor claro | Valor oscuro |
| ------------------------ | ----------- | ------------ |
| `--color-bg-page`        | `#F7F8FA`   | `#0D1117`    |
| `--color-bg-surface`     | `#FFFFFF`   | `#161B24`    |
| `--color-bg-surface-2`   | `#EFF1F5`   | `#1E2633`    |
| `--color-border`         | `#E2E6ED`   | `#2A3547`    |
| `--color-text-primary`   | `#0F1623`   | `#E8EDF5`    |
| `--color-text-secondary` | `#4A5568`   | `#94A3B8`    |
| `--color-text-muted`     | `#8896A9`   | `#4A5A72`    |
| `--color-primary`        | `#2563D4`   | `#4D8EF5`    |
| `--color-primary-subtle` | `#EBF2FF`   | `#0F1E3D`    |
| `--color-ai-accent`      | `#4F5FE8`   | `#818CF8`    |
| `--color-review`         | `#7C3AED`   | `#A78BFA`    |

### CSS Variables — pegar en `frontend/src/index.css`

```css
:root {
  /* Primarios */
  --color-primary:        #2563D4;
  --color-primary-hover:  #1A4DB8;
  --color-primary-active: #133A94;
  --color-primary-subtle: #EBF2FF;
  --color-primary-border: #C3D8FE;

  /* Acento IA */
  --color-ai-accent: #4F5FE8;
  --color-ai-hover:  #6B7FF0;
  --color-ai-subtle: #EEF0FD;

  /* Fondos */
  --color-bg-page:      #F7F8FA;
  --color-bg-surface:   #FFFFFF;
  --color-bg-surface-2: #EFF1F5;

  /* Texto */
  --color-text-primary:   #0F1623;
  --color-text-secondary: #4A5568;
  --color-text-muted:     #8896A9;

  /* Bordes */
  --color-border: #E2E6ED;

  /* Estados */
  --color-success:    #16A34A;
  --color-success-bg: #DCFCE7;
  --color-warning:    #D97706;
  --color-warning-bg: #FEF3C7;
  --color-error:      #DC2626;
  --color-error-bg:   #FEE2E2;
  --color-review:     #7C3AED;
  --color-review-bg:  #F3E8FF;

  /* Tipografía */
  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  /* Border radius */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-primary:        #4D8EF5;
    --color-primary-hover:  #3B7FE8;
    --color-primary-active: #2563D4;
    --color-primary-subtle: #0F1E3D;
    --color-primary-border: #162B5C;

    --color-ai-accent: #818CF8;
    --color-ai-hover:  #6B7FF0;
    --color-ai-subtle: #1A1D3D;

    --color-bg-page:      #0D1117;
    --color-bg-surface:   #161B24;
    --color-bg-surface-2: #1E2633;

    --color-text-primary:   #E8EDF5;
    --color-text-secondary: #94A3B8;
    --color-text-muted:     #4A5A72;

    --color-border: #2A3547;

    --color-success:    #22C55E;
    --color-success-bg: #052E16;
    --color-warning:    #F59E0B;
    --color-warning-bg: #1C1100;
    --color-error:      #F87171;
    --color-error-bg:   #1F0606;
    --color-review:     #A78BFA;
    --color-review-bg:  #1E0938;
  }
}
```

### Clases Tailwind equivalentes

```
Botón primario:       bg-blue-600 hover:bg-blue-700 text-white rounded-lg
Botón secundario:     border border-blue-600 text-blue-600 hover:bg-blue-50 rounded-lg
Botón ghost:          border border-slate-200 text-slate-500 hover:bg-slate-50 rounded-lg
Badge classified:     bg-green-100 text-green-700 rounded-full
Badge pending:        bg-amber-100 text-amber-700 rounded-full
Badge review:         bg-violet-100 text-violet-700 rounded-full
Badge error:          bg-red-100 text-red-600 rounded-full
Badge IA:             bg-indigo-50 text-indigo-600 rounded-full
Sidebar item activo:  bg-blue-50 text-blue-700 font-medium rounded-md
Fondo página:         bg-slate-50
Tarjeta:              bg-white border border-slate-200 rounded-xl p-4
Input:                bg-slate-100 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500
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
