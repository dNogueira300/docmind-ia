"""plan_pricing

Tabla de precios editables para la landing pública. Una fila por plan, con
valores por defecto (free gratis, pro con precio, enterprise por cotización).

Revision ID: d1f4a5b6c7e8
Revises: c9e3f4a5b6d7
Create Date: 2026-06-25 18:30:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = "d1f4a5b6c7e8"
down_revision: Union[str, None] = "c9e3f4a5b6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS plan_pricing ("
        "  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "  plan         VARCHAR(20) NOT NULL UNIQUE,"
        "  price        NUMERIC(10,2) NOT NULL DEFAULT 0,"
        "  currency     VARCHAR(8) NOT NULL DEFAULT 'S/',"
        "  period       VARCHAR(20) NOT NULL DEFAULT '/mes',"
        "  tagline      VARCHAR(140),"
        "  highlight    BOOLEAN NOT NULL DEFAULT FALSE,"
        "  custom_quote BOOLEAN NOT NULL DEFAULT FALSE,"
        "  updated_at   TIMESTAMP NOT NULL DEFAULT NOW()"
        ")"
    )
    # Seed de precios por defecto (idempotente).
    op.execute(
        "INSERT INTO plan_pricing (plan, price, currency, period, tagline, highlight, custom_quote) VALUES "
        "('free', 0, 'S/', '/mes', 'Para empezar y probar', FALSE, FALSE),"
        "('pro', 149, 'S/', '/mes', 'El más popular', TRUE, FALSE),"
        "('enterprise', 0, 'S/', '/mes', 'Para instituciones y gran volumen', FALSE, TRUE) "
        "ON CONFLICT (plan) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS plan_pricing")
