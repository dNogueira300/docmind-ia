"""audit_user_actions

Agrega valores al enum audit_action para registrar operaciones de gestión de usuarios:
  - user_create
  - user_update
  - user_password
  - user_deactivate
  - user_activate

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-01 00:00:00
"""
from typing import Sequence, Union
from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE dentro de autocommit_block porque PostgreSQL no permite
    # usar valores nuevos de enum en la misma transacción en que se agregaron.
    with op.get_context().autocommit_block():
        for value in ("user_create", "user_update", "user_password", "user_deactivate", "user_activate"):
            op.execute(
                f"ALTER TYPE audit_action ADD VALUE IF NOT EXISTS '{value}'"
            )


def downgrade() -> None:
    # PostgreSQL no permite DROP VALUE de enum — se deja sin cambios.
    pass
