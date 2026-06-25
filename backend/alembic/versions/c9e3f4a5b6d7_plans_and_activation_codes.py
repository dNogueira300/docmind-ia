"""plans_and_activation_codes

Agrega el modelo de monetización SaaS:
  - organizations: plan, plan_expires_at, ai_credits_used, ai_credits_reset_at
  - tabla activation_codes: códigos que canjea el admin para activar un plan.

Revision ID: c9e3f4a5b6d7
Revises: b8d2e3f4a5c6
Create Date: 2026-06-25 14:00:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c9e3f4a5b6d7"
down_revision: Union[str, None] = "b8d2e3f4a5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── organizations: campos de plan ────────────────────────────────────────
    op.execute(
        "ALTER TABLE organizations "
        "ADD COLUMN IF NOT EXISTS plan VARCHAR(20) NOT NULL DEFAULT 'free'"
    )
    op.execute(
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS plan_expires_at TIMESTAMP"
    )
    op.execute(
        "ALTER TABLE organizations "
        "ADD COLUMN IF NOT EXISTS ai_credits_used INTEGER NOT NULL DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS ai_credits_reset_at TIMESTAMP"
    )

    # La organización demo es la vitrina del sistema → plan enterprise (todas las
    # features). Las organizaciones nuevas arrancan en 'free' por defecto.
    op.execute(
        "UPDATE organizations SET plan = 'enterprise' "
        "WHERE id = '00000000-0000-0000-0000-000000000001'"
    )

    # ── tabla activation_codes ───────────────────────────────────────────────
    op.execute(
        "CREATE TABLE IF NOT EXISTS activation_codes ("
        "  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "  code          VARCHAR(40) NOT NULL UNIQUE,"
        "  plan          VARCHAR(20) NOT NULL,"
        "  duration_days INTEGER NOT NULL DEFAULT 365,"
        "  used          BOOLEAN NOT NULL DEFAULT FALSE,"
        "  used_by_org   UUID REFERENCES organizations(id) ON DELETE SET NULL,"
        "  used_at       TIMESTAMP,"
        "  expires_at    TIMESTAMP,"
        "  created_at    TIMESTAMP NOT NULL DEFAULT NOW()"
        ")"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS activation_codes")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS ai_credits_reset_at")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS ai_credits_used")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS plan_expires_at")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS plan")
