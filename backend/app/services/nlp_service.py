"""Servicio NLP: clasificación zero-shot de documentos con HuggingFace Transformers."""
import logging
from typing import Optional

logger = logging.getLogger("docmind")

# Singleton del pipeline — se carga una sola vez (lazy, en el primer uso)
_classifier = None

MODEL_NAME = "cross-encoder/nli-MiniLM2-L6-H768"
CONFIDENCE_THRESHOLD = 0.70

# El modelo acepta hasta ~512 tokens; 512 caracteres es una aproximación segura
MAX_TEXT_CHARS = 512


def _get_classifier():
    """
    Retorna el pipeline de clasificación, cargándolo si es necesario.
    Patrón singleton + lazy loading para no bloquear el startup del servidor.
    """
    global _classifier
    if _classifier is None:
        try:
            from transformers import pipeline  # noqa: PLC0415

            logger.info(f"Cargando modelo NLP: {MODEL_NAME} (puede tardar unos segundos)")
            _classifier = pipeline("zero-shot-classification", model=MODEL_NAME)
            logger.info("Modelo NLP cargado correctamente")
        except Exception as exc:
            logger.warning(
                f"No se pudo cargar el modelo NLP '{MODEL_NAME}': {exc}. "
                "Los documentos quedarán en status='review'."
            )
            # Retornamos None — el pipeline degradará gracefully
    return _classifier


def classify_document(text: str, categories: list[str]) -> tuple[str, float]:
    """
    Clasifica el texto contra la lista de categorías de la organización.

    Args:
        text: Texto extraído por OCR (se trunca a MAX_TEXT_CHARS).
        categories: Nombres de las categorías activas de la organización.

    Returns:
        Tupla (nombre_categoría_predicha, score_confianza).
        Si hay error o no hay datos → ("Sin clasificar", 0.0).
    """
    if not text or not text.strip():
        logger.info("Texto vacío recibido — sin clasificación posible")
        return ("Sin clasificar", 0.0)

    if not categories:
        logger.info("Sin categorías disponibles en la organización")
        return ("Sin clasificar", 0.0)

    clf = _get_classifier()
    if clf is None:
        return ("Sin clasificar", 0.0)

    try:
        truncated = text.strip()[:MAX_TEXT_CHARS]
        result = clf(truncated, candidate_labels=categories)

        best_label: str = result["labels"][0]
        best_score: float = float(result["scores"][0])

        logger.info(
            f"Clasificación NLP: '{best_label}' "
            f"(score={best_score:.3f}, umbral={CONFIDENCE_THRESHOLD})"
        )
        return (best_label, best_score)

    except Exception as exc:
        logger.error(f"Error durante la clasificación NLP: {exc}")
        return ("Sin clasificar", 0.0)
