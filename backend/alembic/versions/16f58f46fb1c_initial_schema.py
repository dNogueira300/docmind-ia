"""initial_schema

Crea el esquema base de DocMind IA (tipos enum, tablas, índices y datos
semilla mínimos) de forma self-contained.

Históricamente las tablas se creaban con `db/migrations/001_initial_schema.sql`
ejecutado por Docker al inicializar el contenedor local, y esta migración era
un stamp vacío. Eso rompe `alembic upgrade head` contra una base vacía (p. ej.
el Postgres managed de Railway, donde ese .sql NO se ejecuta). Aquí se replica
el esquema para que las migraciones corran limpio desde cero.

Notas:
  - Todo es idempotente (IF NOT EXISTS / guards DO) → seguro de re-aplicar y no
    afecta bases existentes donde esta revisión ya está registrada.
  - Se OMITEN los GRANT a `docmind_user`: ese rol solo existe en el Postgres
    local de docker-compose; en Railway la app se conecta con el rol dueño del
    schema. Los permisos del .sql original eran específicos de ese entorno.
  - `organizations.slug/active/updated_at` y el valor enum `super_admin` los
    agrega la migración posterior `b2c3d4e5f6a7`; aquí se crea el esquema "Hito 1".

Revision ID: 16f58f46fb1c
Revises:
Create Date: 2026-04-11 09:54:49.768053
"""
from typing import Sequence, Union

from alembic import op


revision: str = "16f58f46fb1c"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extensiones ──────────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ── Tipos ENUM (idempotentes vía guard) ──────────────────────────────────
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN "
        "CREATE TYPE user_role AS ENUM ('admin', 'editor', 'consultor'); "
        "END IF; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'doc_status') THEN "
        "CREATE TYPE doc_status AS ENUM "
        "('pending', 'processing', 'classified', 'review', 'error'); "
        "END IF; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'audit_action') THEN "
        "CREATE TYPE audit_action AS ENUM "
        "('upload', 'view', 'download', 'reclassify', 'delete', 'login'); "
        "END IF; END $$;"
    )

    # ── organizations ────────────────────────────────────────────────────────
    op.execute(
        "CREATE TABLE IF NOT EXISTS organizations ("
        "  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "  name       VARCHAR(255) NOT NULL,"
        "  created_at TIMESTAMP NOT NULL DEFAULT NOW()"
        ")"
    )

    # ── users ────────────────────────────────────────────────────────────────
    op.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "  organization_id UUID NOT NULL REFERENCES organizations(id),"
        "  name            VARCHAR(255) NOT NULL,"
        "  email           VARCHAR(255) NOT NULL,"
        "  password_hash   TEXT NOT NULL,"
        "  role            user_role NOT NULL DEFAULT 'consultor',"
        "  active          BOOLEAN NOT NULL DEFAULT TRUE,"
        "  created_at      TIMESTAMP NOT NULL DEFAULT NOW(),"
        "  UNIQUE (organization_id, email)"
        ")"
    )

    # ── categories ───────────────────────────────────────────────────────────
    op.execute(
        "CREATE TABLE IF NOT EXISTS categories ("
        "  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "  organization_id UUID NOT NULL REFERENCES organizations(id),"
        "  name            VARCHAR(100) NOT NULL,"
        "  description     TEXT,"
        "  color           VARCHAR(7) NOT NULL DEFAULT '#2563D4',"
        "  created_at      TIMESTAMP NOT NULL DEFAULT NOW(),"
        "  UNIQUE (organization_id, name)"
        ")"
    )

    # ── documents ────────────────────────────────────────────────────────────
    op.execute(
        "CREATE TABLE IF NOT EXISTS documents ("
        "  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "  organization_id     UUID NOT NULL REFERENCES organizations(id),"
        "  category_id         UUID REFERENCES categories(id) ON DELETE SET NULL,"
        "  uploaded_by         UUID NOT NULL REFERENCES users(id),"
        "  original_filename   VARCHAR(500) NOT NULL,"
        "  stored_path         TEXT NOT NULL,"
        "  file_type           VARCHAR(10) NOT NULL"
        "                      CHECK (file_type IN ('pdf', 'jpg', 'png')),"
        "  file_size_kb        INTEGER,"
        "  ocr_text            TEXT,"
        "  ai_confidence_score FLOAT"
        "                      CHECK (ai_confidence_score >= 0 AND ai_confidence_score <= 1),"
        "  status              doc_status NOT NULL DEFAULT 'pending',"
        "  created_at          TIMESTAMP NOT NULL DEFAULT NOW(),"
        "  updated_at          TIMESTAMP NOT NULL DEFAULT NOW()"
        ")"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_ocr_fts ON documents "
        "USING GIN (to_tsvector('spanish', COALESCE(ocr_text, '')))"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_org ON documents (organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_category ON documents (category_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_created ON documents (created_at DESC)")

    # ── audit_log ────────────────────────────────────────────────────────────
    op.execute(
        "CREATE TABLE IF NOT EXISTS audit_log ("
        "  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "  document_id UUID REFERENCES documents(id) ON DELETE SET NULL,"
        "  user_id     UUID NOT NULL REFERENCES users(id),"
        "  action      audit_action NOT NULL,"
        "  detail_json JSONB,"
        "  ip_address  VARCHAR(45),"
        "  timestamp   TIMESTAMP NOT NULL DEFAULT NOW()"
        ")"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_document ON audit_log (document_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log (timestamp DESC)")

    # ── Datos semilla mínimos ────────────────────────────────────────────────
    # La organización demo (slug 'demo' se backfillea en b2c3d4e5f6a7) y sus
    # categorías base. Idempotente con ON CONFLICT.
    op.execute(
        "INSERT INTO organizations (id, name) VALUES "
        "('00000000-0000-0000-0000-000000000001', 'Institución Demo') "
        "ON CONFLICT (id) DO NOTHING"
    )
    op.execute(
        "INSERT INTO categories (organization_id, name, description, color) VALUES "
        "('00000000-0000-0000-0000-000000000001', 'Contratos', "
        " 'Acuerdos y convenios institucionales', '#2563D4'),"
        "('00000000-0000-0000-0000-000000000001', 'Resoluciones', "
        " 'Resoluciones administrativas y directivas', '#4F5FE8'),"
        "('00000000-0000-0000-0000-000000000001', 'Informes', "
        " 'Informes de gestión y técnicos', '#D97706'),"
        "('00000000-0000-0000-0000-000000000001', 'Memorándums', "
        " 'Comunicaciones internas entre áreas', '#16A34A'),"
        "('00000000-0000-0000-0000-000000000001', 'Sin clasificar', "
        " 'Documentos pendientes de revisión manual', '#8896A9') "
        "ON CONFLICT (organization_id, name) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_log")
    op.execute("DROP TABLE IF EXISTS documents")
    op.execute("DROP TABLE IF EXISTS categories")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TABLE IF EXISTS organizations")
    op.execute("DROP TYPE IF EXISTS audit_action")
    op.execute("DROP TYPE IF EXISTS doc_status")
    op.execute("DROP TYPE IF EXISTS user_role")
