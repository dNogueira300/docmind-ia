-- ================================================================
-- DocMind IA — Migración 003
-- Multi-tenant SaaS: slug por empresa, super_admin global,
-- desactivación de empresas y usuarios super_admin sin org.
-- Se ejecuta automáticamente solo en instalaciones NUEVAS de la BD.
-- En instalaciones existentes, aplicar con: alembic upgrade head
-- ================================================================

-- ── organizations: slug + active + updated_at ──────────────────
ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS slug VARCHAR(50);

ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();

-- Slug para la org demo existente (si alguna fila no tiene slug)
UPDATE organizations SET slug = 'demo' WHERE slug IS NULL AND name = 'Institución Demo';
-- Cualquier otra fila sin slug: usar id truncado
UPDATE organizations
   SET slug = lower(substr(id::text, 1, 8))
 WHERE slug IS NULL;

ALTER TABLE organizations
    ALTER COLUMN slug SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'organizations_slug_key'
    ) THEN
        ALTER TABLE organizations ADD CONSTRAINT organizations_slug_key UNIQUE (slug);
    END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_organizations_slug   ON organizations (slug);
CREATE INDEX IF NOT EXISTS idx_organizations_active ON organizations (active);

-- ── user_role: agregar 'super_admin' ───────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum WHERE enumlabel = 'super_admin'
                                AND enumtypid = 'user_role'::regtype
    ) THEN
        ALTER TYPE user_role ADD VALUE 'super_admin';
    END IF;
END$$;

-- ── users: organization_id NULLABLE (super_admin no pertenece a ninguna org)
ALTER TABLE users
    ALTER COLUMN organization_id DROP NOT NULL;

-- ── Seed: el super admin global lo crea el backend en el arranque ───────
-- Ver app/main.py::lifespan → ensure_super_admin() — usa
-- variables de entorno SUPER_ADMIN_EMAIL y SUPER_ADMIN_PASSWORD
-- y aplica bcrypt(12) on-the-fly, evitando hashes hardcodeados.

-- ── Permisos: NULL organization_id permitido sólo si role='super_admin' ────
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'users_super_admin_no_org'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT users_super_admin_no_org
            CHECK (
                (role = 'super_admin' AND organization_id IS NULL)
             OR (role <> 'super_admin' AND organization_id IS NOT NULL)
            );
    END IF;
END$$;
