"""
Unit tests del servicio NLP.

Cubre la lógica de clasificación sin cargar el modelo HuggingFace
(lento, ~30s). El zero-shot se mockea; la heurística por keywords
se prueba directamente (sin dependencias externas).
"""
from unittest.mock import patch, MagicMock

import pytest

from app.services.nlp_service import (
    classify_document,
    _match_category_by_keyword,
    _normalize,
    CONFIDENCE_THRESHOLD,
)


# ── _normalize ────────────────────────────────────────────────────────────────

def test_normalize_quita_acentos():
    assert _normalize("Resolución") == "resolucion"
    assert _normalize("Contratos") == "contratos"
    assert _normalize("Comunicación Oficial") == "comunicacion oficial"


def test_normalize_a_minusculas():
    assert _normalize("INFORME TÉCNICO") == "informe tecnico"


# ── _match_category_by_keyword ────────────────────────────────────────────────

def test_keyword_contrato_detectado():
    text = "Este contrato de servicios entre las partes establece las clausulas."
    cats = ["Contratos", "Facturas", "Informes"]
    result = _match_category_by_keyword(text, cats)
    assert result is not None
    nombre, score = result
    assert nombre == "Contratos"
    assert score >= 0.65


def test_keyword_factura_detectada():
    text = "Factura N.° 001-00456 RUC 20512345678 IGV 18% subtotal S/ 1000."
    cats = ["Contratos", "Facturas", "Resoluciones"]
    result = _match_category_by_keyword(text, cats)
    assert result is not None
    assert result[0] == "Facturas"


def test_keyword_resolucion_detectada():
    text = "Se resuelve: aprobar la resolución directoral N.° 021-2026. Considerando que..."
    cats = ["Contratos", "Resoluciones", "Cartas"]
    result = _match_category_by_keyword(text, cats)
    assert result is not None
    assert result[0] == "Resoluciones"


def test_keyword_sin_match_suficiente_retorna_none():
    """Texto sin keywords claras no debe retornar ninguna categoría."""
    text = "El documento es importante para la institución."
    cats = ["Contratos", "Facturas"]
    result = _match_category_by_keyword(text, cats)
    assert result is None


def test_keyword_texto_vacio():
    result = _match_category_by_keyword("", ["Contratos"])
    assert result is None


def test_keyword_categoria_no_coincide_con_concepto():
    """Texto con keywords de 'contrato' pero sin categoría con ese nombre → None."""
    text = "Este contrato establece las clausulas entre las partes contratantes."
    cats = ["Actas", "Certificados", "Memorandos"]
    result = _match_category_by_keyword(text, cats)
    assert result is None


# ── classify_document ─────────────────────────────────────────────────────────

def test_classify_texto_vacio():
    nombre, score = classify_document("", ["Contratos", "Facturas"])
    assert nombre == "Sin clasificar"
    assert score == 0.0


def test_classify_sin_categorias():
    nombre, score = classify_document("Este es un contrato de servicios.", [])
    assert nombre == "Sin clasificar"
    assert score == 0.0


def test_classify_via_keywords_sin_modelo():
    """La heurística encuentra la categoría sin cargar el modelo NLP."""
    text = "Factura N.° 0001-00567 RUC 20567891234 IGV 18% monto total S/ 580.00 comprobante de pago."
    cats = ["Contratos", "Facturas", "Resoluciones"]
    nombre, score = classify_document(text, cats)
    assert nombre == "Facturas"
    assert score >= 0.65


def test_classify_fallback_zero_shot():
    """Cuando la heurística no alcanza el umbral, se llama al modelo zero-shot."""
    text = "Documento de naturaleza desconocida con poca información."
    cats = ["Actas", "Certificados"]

    mock_result = {"labels": ["Actas"], "scores": [0.72]}
    with patch("app.services.nlp_service._get_classifier") as mock_get:
        mock_clf = MagicMock()
        mock_clf.return_value = mock_result
        mock_get.return_value = mock_clf

        nombre, score = classify_document(text, cats)

    assert nombre == "Actas"
    assert score == pytest.approx(0.72)


def test_classify_fallback_final_sin_modelo():
    """Si el modelo no está disponible y la heurística falla, retorna primera categoría con score 0."""
    text = "Texto sin palabras clave reconocibles en absoluto."
    cats = ["Actas", "Informes"]

    with patch("app.services.nlp_service._get_classifier", return_value=None):
        nombre, score = classify_document(text, cats)

    assert nombre == cats[0]  # fallback → primera categoría
    assert score == 0.0


def test_classify_score_sobre_umbral_es_classified():
    """Score >= CONFIDENCE_THRESHOLD indica clasificación automática."""
    assert CONFIDENCE_THRESHOLD == 0.40
    _, score = classify_document(
        "Este contrato de servicios entre el contratante y el contratista establece clausulas.",
        ["Contratos", "Facturas"],
    )
    assert score >= CONFIDENCE_THRESHOLD


def test_classify_informe_detectado():
    text = (
        "INFORME N.° 015-2026-UNAP. Asunto: Se informa el resultado del proceso "
        "de contratación. Antecedentes: El presente informe técnico..."
    )
    cats = ["Informes", "Contratos", "Resoluciones"]
    nombre, score = classify_document(text, cats)
    assert nombre == "Informes"


def test_classify_oficio_detectado():
    text = "Oficio N.° 087-2026. Tengo el agrado de dirigirme a usted para comunicar..."
    cats = ["Oficios", "Cartas", "Resoluciones"]
    nombre, score = classify_document(text, cats)
    assert nombre == "Oficios"
