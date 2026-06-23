"""Exporta todos los modelos SQLAlchemy para que Alembic los detecte."""
from app.models.base import Base
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.category import Category
from app.models.document import Document, DocStatus
from app.models.audit_log import AuditLog, AuditAction
from app.models.alert import DocumentAlert, AlertType, AlertStatus
from app.models.approval import DocumentApproval, ApprovalStatus
from app.models.risk_rule import RiskRule, RiskLevel
from app.models.category_suggestion import CategorySuggestion, SuggestionStatus

__all__ = [
    "Base",
    "Organization",
    "User",
    "UserRole",
    "Category",
    "Document",
    "DocStatus",
    "AuditLog",
    "AuditAction",
    "DocumentAlert",
    "AlertType",
    "AlertStatus",
    "DocumentApproval",
    "ApprovalStatus",
    "RiskRule",
    "RiskLevel",
    "CategorySuggestion",
    "SuggestionStatus",
]
