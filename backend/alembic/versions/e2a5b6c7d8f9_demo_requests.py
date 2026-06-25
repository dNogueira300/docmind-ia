"""demo_requests

Tabla de solicitudes de demo/acceso enviadas desde la landing pública.

Revision ID: e2a5b6c7d8f9
Revises: d1f4a5b6c7e8
Create Date: 2026-06-25 19:00:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = "e2a5b6c7d8f9"
down_revision: Union[str, None] = "d1f4a5b6c7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS demo_requests ("
        "  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "  name              VARCHAR(200) NOT NULL,"
        "  email             VARCHAR(255) NOT NULL,"
        "  organization_name VARCHAR(255),"
        "  plan              VARCHAR(20) NOT NULL DEFAULT 'free',"
        "  message           TEXT,"
        "  status            VARCHAR(20) NOT NULL DEFAULT 'pending',"
        "  response_message  TEXT,"
        "  activation_code   VARCHAR(40),"
        "  responded_at      TIMESTAMP,"
        "  responded_by      UUID REFERENCES users(id) ON DELETE SET NULL,"
        "  created_at        TIMESTAMP NOT NULL DEFAULT NOW()"
        ")"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_demo_requests_status "
        "ON demo_requests (status, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS demo_requests")
