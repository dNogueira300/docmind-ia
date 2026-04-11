---
name: docmind-migrations
description: |
  Alembic database migration guide for DocMind IA (UNAP 2026 — PostgreSQL 15).
  Use this skill whenever a team member needs to: create a new migration, apply pending
  migrations, roll back a migration, add a column or index, set up the initial schema,
  seed development data, or troubleshoot Alembic errors. Trigger proactively when the user
  modifies SQLAlchemy models or asks about database schema changes.
user-invocable: true
---

Standard workflow for all DocMind IA database migrations using Alembic + PostgreSQL 15.

## Core Commands

```bash
cd backend

# Apply all pending migrations (run this after pulling new code)
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Generate a new migration from model changes
alembic revision --autogenerate -m "20260413_add_soft_delete_to_documents"

# Check current revision applied to the DB
alembic current

# Show full migration history
alembic history --verbose
```

`alembic.ini` must point to `DATABASE_URL` from `.env`. Inside docker-compose, the host is `db` not `localhost`.

## Every Migration Must Have

1. **`upgrade()`** — applies the change forward
2. **`downgrade()`** — reverses it completely (never skip this)
3. **Descriptive `-m` message** following naming convention below

Template:
```python
"""20260413_add_soft_delete_to_documents

Revision ID: abc123
Revises: xyz789
Create Date: 2026-04-13
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column("documents", sa.Column("deleted_at", sa.DateTime, nullable=True))

def downgrade():
    op.drop_column("documents", "deleted_at")
```

## Migration Naming Convention

Use `YYYYMMDD_short_description` in the `-m` flag:

```
"initial_schema"
"add_ocr_text_fts_index"
"add_soft_delete_to_documents"
"add_color_to_categories"
"create_audit_log_table"
```

## Full-Text Search Index (critical for DocMind)

The `ocr_text` column powers all document search. Whenever adding or modifying `ocr_text`, include the `tsvector` generated column and GIN index — Alembic's `--autogenerate` will NOT create these automatically.

```python
def upgrade():
    # Add generated tsvector column
    op.execute("""
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS ocr_text_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('spanish', coalesce(ocr_text, ''))) STORED
    """)
    # Create GIN index for fast full-text search (<3s requirement)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_ocr_text_tsv
        ON documents USING GIN (ocr_text_tsv)
    """)

def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_documents_ocr_text_tsv")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS ocr_text_tsv")
```

## Complete Schema Reference

Initial migration must create these 5 tables en este orden (por dependencias):

```sql
-- 1. Multitenancy root
organizations (
  id          SERIAL PRIMARY KEY,
  name        VARCHAR NOT NULL,
  created_at  TIMESTAMP DEFAULT now()
)

-- 2. Customizable categories per org (max 10 in prototype)
categories (
  id              SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  name            VARCHAR NOT NULL,
  description     TEXT,
  color           VARCHAR(7),  -- hex color e.g. #FF5733
  created_at      TIMESTAMP DEFAULT now()
)

-- 3. Users
users (
  id              SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  name            VARCHAR NOT NULL,
  email           VARCHAR NOT NULL UNIQUE,
  password_hash   VARCHAR NOT NULL,   -- bcrypt, min 12 rounds
  role            VARCHAR NOT NULL,   -- 'admin' | 'editor' | 'consultor'
  active          BOOLEAN DEFAULT true,
  created_at      TIMESTAMP DEFAULT now()
)

-- 4. Documents (core entity)
documents (
  id                  SERIAL PRIMARY KEY,
  organization_id     INTEGER NOT NULL REFERENCES organizations(id),
  category_id         INTEGER REFERENCES categories(id),  -- nullable until classified
  uploaded_by         INTEGER NOT NULL REFERENCES users(id),
  original_filename   VARCHAR NOT NULL,
  stored_path         VARCHAR NOT NULL,
  file_type           VARCHAR(4) NOT NULL, -- 'pdf' | 'jpg' | 'png'
  file_size_kb        INTEGER,
  ocr_text            TEXT,
  ai_confidence_score FLOAT,
  status              VARCHAR NOT NULL DEFAULT 'pending',
  created_at          TIMESTAMP DEFAULT now(),
  updated_at          TIMESTAMP DEFAULT now()
)

-- 5. Immutable audit trail
audit_log (
  id          SERIAL PRIMARY KEY,
  document_id INTEGER NOT NULL REFERENCES documents(id),
  user_id     INTEGER NOT NULL REFERENCES users(id),
  action      VARCHAR NOT NULL,  -- 'upload'|'view'|'download'|'reclassify'|'delete'
  detail_json JSONB,
  ip_address  VARCHAR,
  timestamp   TIMESTAMP DEFAULT now()
)
```

## Seed Data for Development

```python
# backend/app/db/seed.py
def seed_dev_data(db):
    org = Organization(name="UNAP Test")
    db.add(org)
    db.flush()

    for name in ["Resoluciones", "Contratos", "Memorándums", "Informes", "Facturas"]:
        db.add(Category(organization_id=org.id, name=name))

    db.add(User(
        organization_id=org.id, name="Admin DocMind",
        email="admin@docmind.test", password_hash=hash_password("admin123"), role="admin"
    ))
    db.add(User(
        organization_id=org.id, name="Editor DocMind",
        email="editor@docmind.test", password_hash=hash_password("editor123"), role="editor"
    ))
    db.commit()
```

## Common Pitfalls

| Pitfall | Rule |
|---|---|
| Editar una migración ya aplicada | Nunca — crear una nueva migración |
| Omitir `downgrade()` | Siempre escribirlo, incluso si parece irreversible |
| Confiar ciegamente en `--autogenerate` | Revisar el archivo generado; Alembic no detecta GIN indexes, tsvector, ni CHECK constraints |
| Host de BD incorrecto | Dentro de Docker: host = `db`, no `localhost` |
| Eliminar categoría con documentos | Los documentos pasan a `category_id = NULL`, no se eliminan |

## Quick Diagnostic

```bash
# ¿El modelo cambió pero no hay migración?
alembic check

# ¿Cuál es la revisión actual de la BD?
alembic current

# Volver a una revisión específica
alembic downgrade <revision_id>
```
