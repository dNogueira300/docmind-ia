---
name: docmind-fastapi
description: |
  Canonical FastAPI patterns for the DocMind IA backend (UNAP 2026).
  Use this skill whenever writing or reviewing: FastAPI routers, endpoint handlers, JWT auth
  middleware, role-based access guards, organization isolation queries, background tasks for
  the OCR/NLP pipeline, audit log entries, or any backend API code in this project.
  Trigger proactively when the user creates or edits files under backend/app/api/ or
  backend/app/core/, or asks "how do I implement X in the backend".
user-invocable: true
---

Canonical patterns for DocMind IA's FastAPI backend. Follow these exactly so all endpoints behave consistently across the team.

## Router Structure

One file per resource in `backend/app/api/`. Include each router in `backend/app/main.py`.

```
backend/app/api/
├── auth.py        ← POST /auth/login, POST /auth/logout
├── users.py       ← GET/POST/PUT/DELETE /users (admin only)
├── categories.py  ← GET/POST/PUT/DELETE /categories (per org)
└── documents.py   ← GET/POST/DELETE /documents
```

Skeleton:
```python
# backend/app/api/categories.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.core.security import require_role

router = APIRouter(prefix="/categories", tags=["categories"])
```

## Authentication — `get_current_user`

```python
# backend/app/core/security.py
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.dependencies import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="Inactive user")
    return user
```

JWT tokens expire in **8 hours**. Passwords hashed with bcrypt, minimum **12 rounds**.

## Role Guard — `require_role`

```python
# backend/app/core/security.py (continued)

def require_role(*roles: str):
    """Factory that returns a FastAPI dependency enforcing the given roles."""
    def guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return guard
```

Usage in routers:
```python
# Admin only
@router.post("/")
async def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    ...

# Admin or editor
@router.post("/upload")
async def upload_document(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "editor"))
):
    ...

# Any authenticated user (all roles)
@router.get("/")
async def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ...
```

## Organization Isolation — MANDATORY on every query

Every DB query involving org-scoped data **must** include `organization_id`. This enforces multitenancy — a user from Org A must never see Org B's data.

```python
# CORRECT — always add org filter
doc = db.query(Document).filter(
    Document.id == doc_id,
    Document.organization_id == current_user.organization_id
).first()
if not doc:
    raise HTTPException(status_code=404, detail="Document not found")

# WRONG — missing org filter exposes cross-tenant data
doc = db.query(Document).filter(Document.id == doc_id).first()
```

Apply the same pattern to categories, users, and audit_log queries.

## Background Task — OCR + NLP Pipeline

The pipeline (OCR → NLP classify) runs asynchronously so the upload endpoint returns immediately.

```python
# backend/app/api/documents.py
from fastapi import APIRouter, BackgroundTasks, UploadFile, File, Depends

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "editor"))
):
    # 1. Validate file type by magic bytes (not extension)
    header = await file.read(12)
    validate_file_type(header)
    await file.seek(0)

    # 2. Store in MinIO
    stored_path = await store_file(file, current_user.organization_id)

    # 3. Create DB record with status='pending'
    doc = Document(
        organization_id=current_user.organization_id,
        uploaded_by=current_user.id,
        original_filename=file.filename,
        stored_path=stored_path,
        status="pending"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 4. Log upload action
    log_action(db, doc.id, current_user.id, "upload")

    # 5. Return immediately — pipeline runs in background
    background_tasks.add_task(process_document_pipeline, doc.id)
    return {"id": doc.id, "status": "pending"}
```

## AI Classifier Integration

```python
# backend/app/services/classifier.py
from transformers import pipeline

_classifier = pipeline(
    "zero-shot-classification",
    model="cross-encoder/nli-MiniLM2-L6-H768"
)

def classify_document(ocr_text: str, org_categories: list[str]) -> tuple[str, float]:
    """Returns (predicted_category_name, confidence_score)."""
    result = _classifier(ocr_text[:512], candidate_labels=org_categories)
    return result["labels"][0], result["scores"][0]
```

Confidence threshold: **≥ 0.70** → auto-classify. Below that → manual review.

## Audit Log — required on every document operation

```python
# backend/app/services/audit.py
from app.models.audit_log import AuditLog

VALID_ACTIONS = {"upload", "view", "download", "reclassify", "delete"}

def log_action(
    db: Session,
    document_id: int,
    user_id: int,
    action: str,
    detail: dict | None = None,
    ip_address: str | None = None
):
    assert action in VALID_ACTIONS, f"Invalid audit action: {action}"
    entry = AuditLog(
        document_id=document_id,
        user_id=user_id,
        action=action,
        detail_json=detail,
        ip_address=ip_address
    )
    db.add(entry)
    db.commit()
```

Call `log_action` inside every endpoint that touches a document: upload, view, download, reclassify, delete.

## API Endpoint Reference

| Method | Path | Roles |
|---|---|---|
| POST | /auth/login | public |
| POST | /auth/logout | any |
| GET | /users | admin |
| POST | /users | admin |
| PUT | /users/{id} | admin |
| DELETE | /users/{id} | admin |
| GET | /categories | any |
| POST | /categories | admin |
| PUT | /categories/{id} | admin |
| DELETE | /categories/{id} | admin |
| GET | /documents | any |
| POST | /documents/upload | admin, editor |
| GET | /documents/{id} | any |
| DELETE | /documents/{id} | admin |

## File Type Validation (magic bytes)

```python
MAGIC_BYTES = {
    b"%PDF": "pdf",
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG": "png",
}

def validate_file_type(header: bytes):
    for magic in MAGIC_BYTES:
        if header.startswith(magic):
            return
    raise HTTPException(status_code=422, detail="File type not allowed. Use PDF, JPG, or PNG.")
```
