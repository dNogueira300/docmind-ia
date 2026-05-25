"""digitalization_and_fuzzy

Agrega:
  - documents.digitalized_path (TEXT) para el .docx generado por OCR
  - extensión pg_trgm
  - índices GIN trigram para búsqueda por nombre y fuzzy en ocr_text

Revision ID: a1b2c3d4e5f6
Revises: 16f58f46fb1c
Create Date: 2026-05-16 10:00:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "16f58f46fb1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS digitalized_path TEXT")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_filename_trgm "
        "ON documents USING GIN (original_filename gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_ocr_trgm "
        "ON documents USING GIN (ocr_text gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_documents_ocr_trgm")
    op.execute("DROP INDEX IF EXISTS idx_documents_filename_trgm")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS digitalized_path")
