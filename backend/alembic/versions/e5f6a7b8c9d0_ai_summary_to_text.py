"""ai_summary_to_text

Cambia el tipo de documents.ai_summary de VARCHAR(300) a TEXT para
permitir resúmenes de hasta 500 caracteres sin truncamiento.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-01 00:00:00
"""
from typing import Sequence, Union
from alembic import op


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # VARCHAR → TEXT es seguro en PostgreSQL: no hay reescritura de tabla
    # y no hay pérdida de datos (TEXT acepta cualquier longitud).
    op.execute(
        "ALTER TABLE documents ALTER COLUMN ai_summary TYPE TEXT"
    )


def downgrade() -> None:
    # Al revertir, los resúmenes que superen 300 chars serán truncados.
    op.execute(
        "ALTER TABLE documents ALTER COLUMN ai_summary TYPE VARCHAR(300) "
        "USING ai_summary::VARCHAR(300)"
    )
