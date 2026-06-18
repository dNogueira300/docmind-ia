"""audit_category_rule_actions

Agrega valores al enum audit_action para registrar operaciones de gestión de
categorías y reglas de riesgo:
  - category_create, category_update, category_delete
  - rule_create, rule_update, rule_delete

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-06 00:00:00
"""
from typing import Sequence, Union
from alembic import op


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for value in (
            "category_create", "category_update", "category_delete",
            "rule_create", "rule_update", "rule_delete",
        ):
            op.execute(
                f"ALTER TYPE audit_action ADD VALUE IF NOT EXISTS '{value}'"
            )


def downgrade() -> None:
    # PostgreSQL no permite DROP VALUE de enum — se deja sin cambios.
    pass
