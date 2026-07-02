"""document_structured_content

Agrega documents.structured_content (JSONB): la estructura del documento
(lista de bloques: headings, párrafos, viñetas y tablas) reconstruida por
Gemini a partir del texto OCR. Se persiste al procesar el documento para poder
mostrar la vista previa "Digitalizado" con la misma estructura que el .docx
descargable, sin re-llamar a la IA en cada vista.

Revision ID: f7b8c9d0e1a2
Revises: e2a5b6c7d8f9
Create Date: 2026-07-02 07:10:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f7b8c9d0e1a2"
down_revision: Union[str, None] = "e2a5b6c7d8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS structured_content JSONB"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS structured_content")
