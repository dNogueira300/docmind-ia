"""next_level_features

Agrega:
  - documents.ai_summary (VARCHAR 300)
  - documents.risk_level (VARCHAR 20, default 'low')
  - documents.status: nuevo valor 'pending_approval'
  - categories.requires_approval (BOOLEAN, default false)
  - categories.approver_role (VARCHAR 20, default 'admin')
  - Tabla document_alerts (alertas de vencimiento)
  - Tabla document_approvals (flujo de aprobación)
  - Tabla risk_rules (reglas de riesgo)
  - Enums: alert_type, alert_status, approval_status, risk_level

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-31 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Nuevo valor en doc_status ────────────────────────────────────────────
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE doc_status ADD VALUE IF NOT EXISTS 'pending_approval'"
        )

    # ── Enums nuevos ─────────────────────────────────────────────────────────
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alert_type') THEN "
        "CREATE TYPE alert_type AS ENUM ('expiry', 'deadline', 'renewal'); "
        "END IF; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alert_status') THEN "
        "CREATE TYPE alert_status AS ENUM ('pending', 'triggered', 'dismissed'); "
        "END IF; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'approval_status') THEN "
        "CREATE TYPE approval_status AS ENUM ('pending', 'approved', 'rejected'); "
        "END IF; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'risk_level') THEN "
        "CREATE TYPE risk_level AS ENUM ('low', 'medium', 'high', 'critical'); "
        "END IF; END $$;"
    )

    # ── Columnas en documents ─────────────────────────────────────────────────
    op.execute(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS ai_summary VARCHAR(300)"
    )
    op.execute(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS risk_level VARCHAR(20) NOT NULL DEFAULT 'low'"
    )

    # ── Columnas en categories ────────────────────────────────────────────────
    op.execute(
        "ALTER TABLE categories ADD COLUMN IF NOT EXISTS "
        "requires_approval BOOLEAN NOT NULL DEFAULT FALSE"
    )
    op.execute(
        "ALTER TABLE categories ADD COLUMN IF NOT EXISTS "
        "approver_role VARCHAR(20) NOT NULL DEFAULT 'admin'"
    )

    # ── Tabla document_alerts ─────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_alerts (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            alert_type      alert_type NOT NULL DEFAULT 'expiry',
            detected_date   DATE NOT NULL,
            alert_date      DATE NOT NULL,
            status          alert_status NOT NULL DEFAULT 'pending',
            detail          TEXT,
            created_at      TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_alerts_org ON document_alerts (organization_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_alerts_doc ON document_alerts (document_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_alerts_date ON document_alerts (alert_date ASC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_alerts_status ON document_alerts (status)"
    )

    # ── Tabla document_approvals ──────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_approvals (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            requested_by    UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            reviewed_by     UUID REFERENCES users(id) ON DELETE RESTRICT,
            status          approval_status NOT NULL DEFAULT 'pending',
            comment         TEXT,
            requested_at    TIMESTAMP NOT NULL DEFAULT NOW(),
            reviewed_at     TIMESTAMP
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_approvals_org ON document_approvals (organization_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_approvals_doc ON document_approvals (document_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_approvals_status ON document_approvals (status)"
    )

    # ── Tabla risk_rules ──────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_rules (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            name            VARCHAR(100) NOT NULL,
            description     TEXT,
            category_ids    UUID[],
            keywords        TEXT[],
            min_file_size_kb INTEGER,
            risk_level      risk_level NOT NULL,
            active          BOOLEAN NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_risk_rules_org ON risk_rules (organization_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_risk_rules_active ON risk_rules (active)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS risk_rules")
    op.execute("DROP TABLE IF EXISTS document_approvals")
    op.execute("DROP TABLE IF EXISTS document_alerts")
    op.execute("ALTER TABLE categories DROP COLUMN IF EXISTS approver_role")
    op.execute("ALTER TABLE categories DROP COLUMN IF EXISTS requires_approval")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS risk_level")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS ai_summary")
    # Los enums no se pueden eliminar fácilmente si hay dependencias
    # op.execute("DROP TYPE IF EXISTS risk_level")
    # op.execute("DROP TYPE IF EXISTS approval_status")
    # op.execute("DROP TYPE IF EXISTS alert_status")
    # op.execute("DROP TYPE IF EXISTS alert_type")
