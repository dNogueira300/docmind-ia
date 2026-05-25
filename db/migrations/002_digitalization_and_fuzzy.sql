-- ================================================================
-- DocMind IA — Migración 002
-- Digitalización OCR -> DOCX + búsqueda fuzzy (pg_trgm)
-- Se ejecuta automáticamente solo en instalaciones NUEVAS de la BD
-- (PostgreSQL ejecuta /docker-entrypoint-initdb.d una sola vez).
-- En instalaciones existentes, aplicar con: alembic upgrade head
-- ================================================================

-- ── Archivo digitalizado (.docx) generado tras el OCR ──────────
ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS digitalized_path TEXT;

-- ── Búsqueda fuzzy con trigramas ────────────────────────────────
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Índice trigram sobre el nombre del archivo (búsqueda por nombre y fuzzy)
CREATE INDEX IF NOT EXISTS idx_documents_filename_trgm
    ON documents
    USING GIN (original_filename gin_trgm_ops);

-- Índice trigram sobre el contenido OCR (fuzzy en texto extraído)
CREATE INDEX IF NOT EXISTS idx_documents_ocr_trgm
    ON documents
    USING GIN (ocr_text gin_trgm_ops);
