# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DocMind IA** — Intelligent document management SaaS platform for Peruvian/Latin American institutions. Digitizes, classifies, and centralizes institutional documentation using OCR + NLP.

University project (UNAP, 2026) — development window: 23/03/2026 to 28/06/2026.

## Stack

```
Backend:    Python 3.11 + FastAPI
Frontend:   React.js (Vite) + Tailwind CSS
Database:   PostgreSQL 15 (full-text search on ocr_text)
OCR:        Tesseract OCR (primary) + Google Cloud Vision API (fallback)
NLP/AI:     HuggingFace zero-shot-classification — model BETO (Spanish)
Storage:    MinIO (S3-compatible)
Auth:       JWT + bcrypt
DevOps:     Docker + docker-compose
```

## Development Commands

### Start the full stack
```bash
docker compose up
```

### Backend (FastAPI)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs auto-generated at `http://localhost:8000/docs` (Swagger UI).

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

### Backend tests
```bash
cd backend
pytest                          # all tests
pytest tests/test_auth.py       # single file
pytest -k "test_login"          # single test by name
```

### Database migrations (Alembic)
```bash
cd backend
alembic upgrade head            # apply all migrations
alembic revision --autogenerate -m "description"  # generate new migration
```

## Architecture

### Backend structure (`backend/app/`)
```
api/        # FastAPI routers — one file per resource (auth, users, categories, documents)
models/     # SQLAlchemy ORM models
services/   # Business logic: ocr.py, classifier.py, audit.py, storage.py
core/       # Config (settings), JWT auth middleware, security utilities
```

### Key data model
- **organizations** — multitenancy root; all data is scoped to an organization
- **categories** — fully customizable per organization; no global taxonomy
- **documents** — status lifecycle: `pending → processing → classified | error`; `ocr_text` holds extracted text; `ai_confidence_score` holds NLP confidence
- **audit_log** — immutable operation log (upload, view, download, reclassify, delete)

### User roles
- `admin` — full access, manages users and categories
- `editor` — can upload, search, and manually reclassify documents
- `consultor` — read-only (search + view)

### Document processing pipeline
1. User uploads file → stored in MinIO at `docmind/{org_id}/{year}/{month}/{doc_id}_{filename}`
2. DB record created with `status: pending`; API returns immediately
3. Background task: OCR extracts text → NLP classifies against org's live category list
4. If confidence ≥ 0.70 → auto-classify; if < 0.70 → status "requires manual review"
5. `ocr_text`, `category_id`, `ai_confidence_score`, `status` updated in DB

### AI classifier
Uses HuggingFace `zero-shot-classification` with dynamic `candidate_labels` fetched from the organization's current categories — no retraining needed when categories change.

```python
classifier = pipeline("zero-shot-classification", model="cross-encoder/nli-MiniLM2-L6-H768")
result = classifier(ocr_text[:512], candidate_labels=org_categories)
```

### File storage (MinIO)
Files are never publicly accessible. Access only via signed URLs with expiration. Validate file type by content (not just extension/Content-Type); max size 20 MB.

## Key Constraints
- OCR must support Spanish (`spa` Tesseract language pack); target ≥ 85% accuracy
- Search queries must respond in < 3 seconds (PostgreSQL full-text index on `ocr_text`)
- Prototype supports up to 10 categories per organization
- Accepted file types: PDF, JPG, PNG only
- JWT tokens expire in 8 hours; bcrypt with minimum 12 rounds
- Cross-organization data isolation must be enforced at every query level

## Security

### Rate limiting
- Login endpoint (`POST /api/v1/auth/login`) is limited to **10 requests/minute per IP** via `slowapi`.
- Exceeding the limit returns HTTP 429 with message: `"Demasiados intentos. Espera un minuto antes de intentar de nuevo."`
- The shared `Limiter` instance lives in `backend/app/core/limiter.py`.

### CORS
- Allowed origins are controlled by the `ALLOWED_ORIGINS` env variable (parsed as a JSON list).
- Development default: `["*"]`
- Production (Railway): set to `["https://your-frontend.railway.app"]`

### Swagger / OpenAPI docs
- With `ENVIRONMENT=production`: `/docs`, `/redoc`, and `/openapi.json` return 404 (disabled at app creation).
- With `ENVIRONMENT=development` (default): all three are available normally.

### SECRET_KEY
- Never commit a real `SECRET_KEY` to the repository.
- Minimum 64 hex characters. Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`

### audit_log
- The `audit_log` table is **immutable**: never issue `UPDATE` or `DELETE` against it — only `INSERT`.
- Every document operation (`upload`, `view`, `download`, `reclassify`, `delete`) must be logged.

### HTTP Security Headers
All responses include the following headers (set by the `security_headers` middleware in `main.py`):
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

### File upload security
- Files are validated by magic bytes (not just extension or `Content-Type`).
- Empty files (0 bytes) are rejected with HTTP 400.
- Files with an invalid declared `Content-Type` are rejected with HTTP 422.
- Files over 20 MB are rejected with HTTP 413.
- All rejections are logged (WARNING level) including IP, filename, and reason.
