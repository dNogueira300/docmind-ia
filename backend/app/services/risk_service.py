"""Servicio de evaluación de reglas de riesgo documental."""
import logging
from uuid import UUID
from typing import Optional

logger = logging.getLogger("docmind")

# Orden de prioridad de niveles de riesgo (mayor índice = mayor riesgo)
RISK_PRIORITY = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def evaluate_risk(
    db,
    organization_id: UUID,
    category_id: Optional[UUID],
    ocr_text: str,
    file_size_kb: Optional[int],
) -> str:
    """
    Evalúa las reglas activas de la organización y devuelve el nivel de riesgo
    más alto que aplique al documento.

    Retorna uno de: 'low', 'medium', 'high', 'critical'.
    """
    from app.models.risk_rule import RiskRule

    rules = (
        db.query(RiskRule)
        .filter(
            RiskRule.organization_id == organization_id,
            RiskRule.active == True,
        )
        .all()
    )

    if not rules:
        return "low"

    text_lower = (ocr_text or "").lower()
    highest = "low"
    highest_priority = 0

    for rule in rules:
        if not _rule_applies(rule, category_id, text_lower, file_size_kb):
            continue

        level = rule.risk_level.value if hasattr(rule.risk_level, "value") else rule.risk_level
        priority = RISK_PRIORITY.get(level, 0)
        if priority > highest_priority:
            highest_priority = priority
            highest = level
            logger.info(
                f"Regla de riesgo aplicada: '{rule.name}' → nivel={level}"
            )

    return highest


def _rule_applies(
    rule,
    category_id: Optional[UUID],
    text_lower: str,
    file_size_kb: Optional[int],
) -> bool:
    """Verifica si una regla aplica al documento dado."""
    # Filtro por categorías (si la regla especifica categorías)
    if rule.category_ids:
        cat_ids = [str(c) for c in rule.category_ids]
        if category_id is None or str(category_id) not in cat_ids:
            return False

    # Filtro por palabras clave (todas deben aparecer)
    if rule.keywords:
        for kw in rule.keywords:
            if kw.lower() not in text_lower:
                return False

    # Filtro por tamaño mínimo
    if rule.min_file_size_kb and file_size_kb is not None:
        if file_size_kb < rule.min_file_size_kb:
            return False

    return True
