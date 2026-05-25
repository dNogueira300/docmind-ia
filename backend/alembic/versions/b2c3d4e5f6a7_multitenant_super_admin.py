"""multitenant_super_admin

Agrega:
  - organizations.slug (UNIQUE NOT NULL), active, updated_at
  - user_role: nuevo valor 'super_admin'
  - users.organization_id pasa a NULLABLE (solo NULL para super_admin)
  - CHECK: NULL org_id <=> role='super_admin'
  - Seed: usuario super admin global

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-17 09:00:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── organizations: slug, active, updated_at ─────────────────────────────
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS slug VARCHAR(50)")
    op.execute(
        "ALTER TABLE organizations "
        "ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE"
    )
    op.execute(
        "ALTER TABLE organizations "
        "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()"
    )

    # Asignar slug a las filas existentes
    op.execute(
        "UPDATE organizations SET slug = 'demo' "
        "WHERE slug IS NULL AND name = 'Institución Demo'"
    )
    op.execute(
        "UPDATE organizations "
        "   SET slug = lower(substr(id::text, 1, 8)) "
        " WHERE slug IS NULL"
    )
    op.execute("ALTER TABLE organizations ALTER COLUMN slug SET NOT NULL")
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'organizations_slug_key') THEN "
        "ALTER TABLE organizations ADD CONSTRAINT organizations_slug_key UNIQUE (slug); "
        "END IF; END $$;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_organizations_slug "
        "ON organizations (slug)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_organizations_active "
        "ON organizations (active)"
    )

    # ── user_role: agregar super_admin ──────────────────────────────────────
    # PostgreSQL no permite USAR un valor de enum recién agregado dentro de la
    # misma transacción en que se agregó. La migración usa 'super_admin' más
    # abajo en el CHECK constraint, así que necesitamos commitearlo primero.
    # `autocommit_block()` hace COMMIT del bloque actual, ejecuta este ALTER
    # en autocommit y reabre la transacción de la migración para el resto.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'super_admin'"
        )

    # ── users.organization_id NULLABLE ──────────────────────────────────────
    op.execute("ALTER TABLE users ALTER COLUMN organization_id DROP NOT NULL")

    # El super admin lo crea el backend en el arranque (lifespan) con
    # bcrypt aplicado on-the-fly desde SUPER_ADMIN_PASSWORD env var.
    # Ver app/main.py::ensure_super_admin().

    # ── CHECK: super_admin <=> organization_id IS NULL ──────────────────────
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'users_super_admin_no_org') THEN "
        "ALTER TABLE users ADD CONSTRAINT users_super_admin_no_org "
        "CHECK ("
        "  (role = 'super_admin' AND organization_id IS NULL) OR "
        "  (role <> 'super_admin' AND organization_id IS NOT NULL)"
        "); "
        "END IF; END $$;"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_super_admin_no_org")
    op.execute("DELETE FROM users WHERE role = 'super_admin'")
    op.execute("ALTER TABLE users ALTER COLUMN organization_id SET NOT NULL")
    # No se puede DROP VALUE de un enum en PostgreSQL — se deja el valor.
    op.execute("DROP INDEX IF EXISTS idx_organizations_active")
    op.execute("DROP INDEX IF EXISTS idx_organizations_slug")
    op.execute("ALTER TABLE organizations DROP CONSTRAINT IF EXISTS organizations_slug_key")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS active")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS slug")
