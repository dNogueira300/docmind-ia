"""
Servicio NLP: clasificación de documentos en español.

Estrategia híbrida:
  1) Heurística por palabras clave en español (rápida, sin modelo, alta precisión
     para tipos comunes: contratos, facturas, informes, resoluciones, etc.).
  2) Si la heurística no es concluyente, se usa zero-shot multilingüe
     (MoritzLaurer/mDeBERTa-v3-base-mnli-xnli — funciona bien en español).
  3) Si todo falla, se elige la mejor etiqueta disponible. NUNCA se devuelve
     "Sin clasificar" cuando hay texto y categorías → el documento no se queda
     atascado en `review`.
"""
import logging
import re
import unicodedata
from typing import Optional

logger = logging.getLogger("docmind")

# ── Singleton del pipeline (lazy load) ───────────────────────────────────────
_classifier = None

# Modelo multilingüe entrenado en XNLI — soporta español nativamente
MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

# Hipótesis en español: imprescindible para que el zero-shot funcione bien
HYPOTHESIS_TEMPLATE = "Este documento es un/una {}."

# Umbral mínimo: si el score del modelo lo supera, marcamos como `classified`.
# Por debajo, igual asignamos la categoría más probable pero quedará en `review`.
CONFIDENCE_THRESHOLD = 0.40

# El modelo acepta hasta 512 tokens; tomamos ~1500 caracteres como ventana segura
MAX_TEXT_CHARS = 1500


# ── Heurística de palabras clave en español ─────────────────────────────────
#
# Mapea palabras clave habituales en documentos peruanos/latinoamericanos
# a una etiqueta canónica. La categoría real se busca por coincidencia
# (case-insensitive, sin acentos, substring) entre estas claves y los nombres
# de las categorías de la organización.
KEYWORD_RULES: list[tuple[str, list[str]]] = [
    ("contrato", [
        "contrato", "clausula", "clausulas", "convenio", "contratante",
        "contratista", "las partes", "el contratante", "el contratado",
        "suscrito entre", "prestacion de servicios profesionales",
    ]),
    # Órdenes de Servicio / Trabajo / Compra
    ("orden", [
        "orden",
        "orden de servicio", "orden de trabajo", "orden de compra",
        "orden n°", "orden no.", "se ordena a", "emision de la orden",
        "ejecutar el servicio",
    ]),
    ("factura", [
        "factura", "ruc", "boleta de venta", "igv",
        "comprobante de pago", "serie y numero", "tipo de comprobante",
    ]),
    # Propuestas Comerciales / Cotizaciones
    ("propuesta", [
        "propuesta",
        "propuesta comercial", "propuesta tecnica", "propuesta economica",
        "cotizacion", "cotización", "oferta comercial", "oferta tecnica",
        "presentamos a su consideracion", "propuesta de servicios",
        "valor de la propuesta",
    ]),
    # Reportes de Avance / Proyecto
    ("reporte", [
        "reporte",
        "reporte de avance", "informe de avance", "avance del proyecto",
        "estado del proyecto", "actividades realizadas en el periodo",
        "primer trimestre", "segundo trimestre", "tercer trimestre",
        "hito completado", "progreso del proyecto", "sprint", "entregable",
    ]),
    ("resolucion", [
        "resolucion",
        "se resuelve", "considerando que", "resuelve:",
        "resolucion directoral", "resolucion rectoral", "resolucion ministerial",
    ]),
    ("informe", [
        "informe",
        "informe n", "informe tecnico", "informe final", "se informa",
        "el presente informe", "antecedentes:", "conclusion:",
    ]),
    ("memorandum", [
        "memorandum", "memorando", "memo n",
        "referencia:", "mediante el presente",
    ]),
    ("carta", [
        "estimado", "estimada", "atentamente", "cordialmente",
        "tengo el agrado", "me dirijo a usted", "carta n",
    ]),
    ("oficio", [
        "oficio n", "oficio circular", "tengo el agrado de dirigirme",
    ]),
    ("solicitud", [
        "solicito", "solicita", "solicitud de", "por la presente solicito",
    ]),
    ("acta", [
        "acta de", "siendo las", "se da por concluida", "se levanta la sesion",
    ]),
    ("constancia", [
        "constancia", "se deja constancia", "hace constar",
    ]),
    ("certificado", [
        "certifica", "certificado", "se certifica que",
    ]),
]


def _normalize(text: str) -> str:
    """Pasa a minúsculas y quita acentos para matching tolerante."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _match_category_by_keyword(
    text: str, categories: list[str]
) -> Optional[tuple[str, float]]:
    """
    Busca la mejor categoría aplicando reglas de palabras clave.

    Cuenta cuántas pistas de cada concepto (contrato, factura, …) aparecen
    en el texto. Para cada concepto, intenta encontrar una categoría real
    de la organización cuyo nombre contenga ese concepto. Si encuentra
    coincidencias claras (>=2 keywords), retorna (nombre_categoria, score).
    """
    normalized_text = _normalize(text)
    normalized_cats = {c: _normalize(c) for c in categories}

    best_concept: Optional[str] = None
    best_hits = 0

    for concept, keywords in KEYWORD_RULES:
        hits = sum(
            1
            for kw in keywords
            if re.search(rf"\b{re.escape(kw)}", normalized_text)
        )
        if hits > best_hits:
            best_hits = hits
            best_concept = concept

    if not best_concept or best_hits < 2:
        return None

    # Buscar categoría real cuyo nombre normalizado contenga el concepto
    for original, normalized in normalized_cats.items():
        if best_concept in normalized:
            # Score heurístico: 0.65 base + 0.05 por keyword extra (cap a 0.90)
            score = min(0.65 + 0.05 * (best_hits - 2), 0.90)
            logger.info(
                f"Clasificación por keywords: concepto='{best_concept}', "
                f"hits={best_hits}, categoría='{original}', score={score:.2f}"
            )
            return (original, score)

    return None


def _get_classifier():
    """Carga el pipeline zero-shot la primera vez (puede tardar ~30s)."""
    global _classifier
    if _classifier is None:
        try:
            from transformers import pipeline  # noqa: PLC0415

            logger.info(f"Cargando modelo NLP: {MODEL_NAME} (puede tardar)")
            _classifier = pipeline(
                "zero-shot-classification",
                model=MODEL_NAME,
            )
            logger.info("Modelo NLP cargado correctamente")
        except Exception as exc:
            logger.warning(
                f"No se pudo cargar el modelo NLP '{MODEL_NAME}': {exc}. "
                "Se usará solo la heurística por keywords."
            )
    return _classifier


def classify_document(
    text: str, categories: list[str]
) -> tuple[str, float]:
    """
    Clasifica el texto contra la lista de categorías de la organización.

    Returns:
        (nombre_categoria, score_confianza) — score en [0.0, 1.0].
        Si no hay texto o no hay categorías → ("Sin clasificar", 0.0).
        En todos los demás casos siempre retorna la mejor categoría posible
        (jamás "Sin clasificar"), aunque el score sea bajo.
    """
    if not text or not text.strip():
        logger.info("Texto vacío — sin clasificación posible")
        return ("Sin clasificar", 0.0)

    if not categories:
        logger.info("Sin categorías disponibles en la organización")
        return ("Sin clasificar", 0.0)

    # ── 1) Heurística por palabras clave ────────────────────────────────────
    keyword_match = _match_category_by_keyword(text, categories)
    if keyword_match is not None:
        return keyword_match

    # ── 2) Zero-shot NLP ────────────────────────────────────────────────────
    clf = _get_classifier()
    if clf is not None:
        try:
            truncated = text.strip()[:MAX_TEXT_CHARS]
            result = clf(
                truncated,
                candidate_labels=categories,
                hypothesis_template=HYPOTHESIS_TEMPLATE,
                multi_label=False,
            )
            best_label: str = result["labels"][0]
            best_score: float = float(result["scores"][0])
            logger.info(
                f"Clasificación NLP: '{best_label}' "
                f"(score={best_score:.3f}, umbral={CONFIDENCE_THRESHOLD})"
            )
            return (best_label, best_score)
        except Exception as exc:
            logger.error(f"Error durante la clasificación NLP: {exc}")

    # ── 3) Fallback final: primera categoría disponible con score 0.0 ──────
    # Esto evita que el documento quede bloqueado sin categoría.
    fallback = categories[0]
    logger.info(
        f"Fallback de clasificación: asignando '{fallback}' con score 0.0"
    )
    return (fallback, 0.0)
