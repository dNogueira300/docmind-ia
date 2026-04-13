"""initial_schema

Revision ID: 16f58f46fb1c
Revises:
Create Date: 2026-04-11 09:54:49.768053

Las tablas fueron creadas por db/migrations/001_initial_schema.sql vía Docker.
Esta migración está vacía y se marca con `alembic stamp head` para que Alembic
registre el estado actual sin tocar la BD.
"""
from typing import Sequence, Union


revision: str = "16f58f46fb1c"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
