---
name: docmind-conventions
description: |
  Conventions, standards, and business rules for the DocMind IA project (UNAP 2026).
  Use this skill whenever a team member asks about: commit format, branch names, folder structure,
  file naming, user roles, document status lifecycle, accepted file types, security constraints,
  or any "how do we do X in this project" question. Trigger this skill proactively any time
  code or discussion touches naming, project structure, roles, or key business constraints.
user-invocable: true
---

Reference guide for all DocMind IA project conventions. Apply these standards consistently across every file, commit, and discussion.

## Commits — Conventional Commits

Format: `type(scope): short description`

**Types:** `feat` `fix` `docs` `refactor` `test` `chore`

**Scopes:** `backend` `frontend` `ai` `db` `docker` `auth`

```
feat(backend): add document upload endpoint
fix(auth): correct JWT expiration to 8 hours
test(db): add migration rollback tests
docs(frontend): update README with Vite setup steps
refactor(ai): extract classifier into dedicated service
chore(docker): update postgres image to 15.4
```

Never use generic messages like `fix bug` or `update code`.

## Branches

```
main                        ← protected, always deployable
feature/backend             ← backend team's integration branch
feature/frontend            ← frontend team's integration branch
feature/ai                  ← AI/ML team's integration branch

feature/backend/auth        ← sub-branches for specific work
feature/backend/documents
feature/frontend/dashboard
feature/frontend/search
```

## Folder Structure

```
docmind-ia/
├── backend/
│   └── app/
│       ├── api/        ← FastAPI routers, one file per resource
│       ├── models/     ← SQLAlchemy ORM models
│       ├── services/   ← ocr.py, classifier.py, audit.py, storage.py
│       └── core/       ← settings.py, security.py, dependencies.py
├── frontend/
│   └── src/
│       ├── components/ ← reusable UI components
│       ├── pages/      ← one file per route/view
│       └── services/   ← API call functions (axios)
├── ml/
│   ├── training/       ← classifier training scripts
│   └── models/         ← exported model files
└── db/
    └── migrations/     ← Alembic migration files
```

## Naming Conventions

| Context | Convention | Example |
|---|---|---|
| Python files | `snake_case.py` | `document_service.py` |
| React components | `PascalCase.tsx` | `DocumentList.tsx` |
| DB tables | `snake_case` plural | `audit_log`, `documents` |
| API endpoints | lowercase, hyphens | `/documents/upload` |
| API versioning | prefix `/api/v1/` | `/api/v1/categories` |
| MinIO paths | `docmind/{org_id}/{year}/{month}/{doc_id}_{filename}` | |
| Env variables | `SCREAMING_SNAKE_CASE` | `DATABASE_URL`, `SECRET_KEY` |

## User Roles

| Role | Permissions |
|---|---|
| `admin` | Full access: manages users, categories, documents; views audit log |
| `editor` | Upload documents, search, manually reclassify |
| `consultor` | Read-only: search and view documents only |

Always enforce role checks server-side. Never trust client-reported roles.

## Document Status Lifecycle

```
pending → processing → classified
                    ↘ error
```

- `pending` — file stored in MinIO, DB record created, waiting for background task
- `processing` — OCR and NLP running
- `classified` — `ocr_text`, `category_id`, `ai_confidence_score` all set
- `error` — pipeline failed; log the reason, notify editor

## Accepted File Types & Validation

- **Allowed:** PDF, JPG, PNG only
- **Max size:** 20 MB per file
- **Validation:** check magic bytes (file content), not just extension or `Content-Type` header
  - PDF: starts with `%PDF`
  - JPG: starts with `FF D8 FF`
  - PNG: starts with `89 50 4E 47`

Reject anything else with HTTP 422 before storing.

## Key Business Rules (never violate these)

| Rule | Value |
|---|---|
| Cross-org data isolation | Every DB query must filter by `organization_id` |
| Max categories per org | 10 (prototype limit) |
| JWT expiration | 8 hours |
| bcrypt rounds | minimum 12 |
| OCR language | Spanish — Tesseract `spa` language pack |
| OCR accuracy target | ≥ 85% |
| Search response time | < 3 seconds (enforced via PostgreSQL GIN index on `ocr_text`) |
| AI confidence threshold | ≥ 0.70 → auto-classify; < 0.70 → requires manual review |
| File access | Never public — only via signed MinIO URLs with expiration |

## MinIO Storage Path

```
bucket: docmind/
└── {organization_id}/
    └── {year}/{month}/
        └── {document_id}_{original_filename}
```

Example: `docmind/org-42/2026/04/doc-789_resolucion_001.pdf`
