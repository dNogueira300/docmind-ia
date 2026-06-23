"""ocr_pdf_and_category_suggestions

Agrega:
  - documents.ocr_pdf_path (TEXT): PDF con capa de texto OCR (editable)
  - tipo enum suggestion_status
  - tabla category_suggestions: sugerencias de categorías de la IA (Gemini)
    pendientes de aprobación por el admin de la organización.

Revision ID: a7c1d2e3f4b5
Revises: f6a7b8c9d0e1
Create Date: 2026-06-23 10:00:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a7c1d2e3f4b5"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── documents.ocr_pdf_path ───────────────────────────────────────────────
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS ocr_pdf_path TEXT")

    # ── enum suggestion_status ───────────────────────────────────────────────
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'suggestion_status') THEN "
        "CREATE TYPE suggestion_status AS ENUM ('pending', 'approved', 'rejected'); "
        "END IF; END $$;"
    )

    # ── tabla category_suggestions ───────────────────────────────────────────
    op.execute(
        "CREATE TABLE IF NOT EXISTS category_suggestions ("
        "  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,"
        "  document_id     UUID REFERENCES documents(id) ON DELETE SET NULL,"
        "  suggested_name  VARCHAR(100) NOT NULL,"
        "  confidence      FLOAT,"
        "  status          suggestion_status NOT NULL DEFAULT 'pending',"
        "  created_at      TIMESTAMP NOT NULL DEFAULT NOW(),"
        "  reviewed_at     TIMESTAMP,"
        "  reviewed_by     UUID REFERENCES users(id) ON DELETE SET NULL"
        ")"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_category_suggestions_org_status "
        "ON category_suggestions (organization_id, status)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS category_suggestions")
    op.execute("DROP TYPE IF EXISTS suggestion_status")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS ocr_pdf_path")
