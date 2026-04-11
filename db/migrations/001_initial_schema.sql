-- ================================================================
-- DocMind IA — Esquema inicial PostgreSQL
-- Archivo: db/migrations/001_initial_schema.sql
-- Versión: 1.0 — Hito 1
-- Ejecutado automáticamente por Docker al crear la BD
-- ================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── TIPOS ENUM ──────────────────────────────────────────────────
CREATE TYPE user_role AS ENUM ('admin', 'editor', 'consultor');

CREATE TYPE doc_status AS ENUM (
    'pending', 'processing', 'classified', 'review', 'error'
);

CREATE TYPE audit_action AS ENUM (
    'upload', 'view', 'download', 'reclassify', 'delete', 'login'
);

-- ── organizations ────────────────────────────────────────────────
CREATE TABLE organizations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ── users ────────────────────────────────────────────────────────
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name            VARCHAR(255) NOT NULL,
    email           VARCHAR(255) NOT NULL,
    password_hash   TEXT NOT NULL,
    role            user_role NOT NULL DEFAULT 'consultor',
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (organization_id, email)
);

-- ── categories ───────────────────────────────────────────────────
CREATE TABLE categories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    color           VARCHAR(7) NOT NULL DEFAULT '#2563D4',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (organization_id, name)
);

-- ── documents ────────────────────────────────────────────────────
CREATE TABLE documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL REFERENCES organizations(id),
    category_id         UUID REFERENCES categories(id) ON DELETE SET NULL,
    uploaded_by         UUID NOT NULL REFERENCES users(id),
    original_filename   VARCHAR(500) NOT NULL,
    stored_path         TEXT NOT NULL,
    file_type           VARCHAR(10) NOT NULL
                        CHECK (file_type IN ('pdf', 'jpg', 'png')),
    file_size_kb        INTEGER,
    ocr_text            TEXT,
    ai_confidence_score FLOAT
                        CHECK (ai_confidence_score >= 0 AND ai_confidence_score <= 1),
    status              doc_status NOT NULL DEFAULT 'pending',
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_ocr_fts
    ON documents
    USING GIN (to_tsvector('spanish', COALESCE(ocr_text, '')));

CREATE INDEX idx_documents_org      ON documents (organization_id);
CREATE INDEX idx_documents_category ON documents (category_id);
CREATE INDEX idx_documents_status   ON documents (status);
CREATE INDEX idx_documents_created  ON documents (created_at DESC);

-- ── audit_log ────────────────────────────────────────────────────
CREATE TABLE audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    user_id     UUID NOT NULL REFERENCES users(id),
    action      audit_action NOT NULL,
    detail_json JSONB,
    ip_address  VARCHAR(45),
    timestamp   TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_document ON audit_log (document_id);
CREATE INDEX idx_audit_user     ON audit_log (user_id);
CREATE INDEX idx_audit_time     ON audit_log (timestamp DESC);

-- ── Permisos para docmind_user ───────────────────────────────────
GRANT USAGE ON SCHEMA public TO docmind_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO docmind_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO docmind_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO docmind_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO docmind_user;

-- ── Datos semilla ────────────────────────────────────────────────
INSERT INTO organizations (id, name) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Institución Demo');

INSERT INTO categories (organization_id, name, description, color) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Contratos',
     'Acuerdos y convenios institucionales', '#2563D4'),
    ('00000000-0000-0000-0000-000000000001', 'Resoluciones',
     'Resoluciones administrativas y directivas', '#4F5FE8'),
    ('00000000-0000-0000-0000-000000000001', 'Informes',
     'Informes de gestión y técnicos', '#D97706'),
    ('00000000-0000-0000-0000-000000000001', 'Memorándums',
     'Comunicaciones internas entre áreas', '#16A34A'),
    ('00000000-0000-0000-0000-000000000001', 'Sin clasificar',
     'Documentos pendientes de revisión manual', '#8896A9');