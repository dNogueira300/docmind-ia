"""doc_ai_suggested_category

Agrega documents.ai_suggested_category (TEXT): el nombre de categoría que Gemini
propuso para un documento que no encajó en ninguna existente. Se persiste al
procesar el documento (reutilizando la decisión que Gemini ya tomó, sin llamadas
extra) para que, al aprobar la categoría sugerida, se puedan clasificar en lote
todos los documentos en review que esperaban esa misma categoría.

Revision ID: b8d2e3f4a5c6
Revises: a7c1d2e3f4b5
Create Date: 2026-06-25 12:00:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b8d2e3f4a5c6"
down_revision: Union[str, None] = "a7c1d2e3f4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS ai_suggested_category TEXT"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_ai_suggested_category "
        "ON documents (organization_id, ai_suggested_category)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_documents_ai_suggested_category")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS ai_suggested_category")
