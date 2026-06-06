"""
Servicio de NER (Named Entity Recognition) con spaCy.

Modelo: es_core_news_lg  (~560 MB, spaCy español)
Instalación (una sola vez): python -m spacy download es_core_news_lg

Se usa para extraer el SUJETO de una alerta de vencimiento, por ejemplo:
  "La licencia de uso del módulo NLP vence el 30 de junio"
  → sujeto detectado: "licencia de uso del módulo NLP"
"""
import logging
import re

logger = logging.getLogger("docmind")

_NLP = None
_NLP_TRIED = False

_MODEL_NAME = "es_core_news_lg"
_FALLBACK_NAME = "es_core_news_sm"


def _get_nlp():
    global _NLP, _NLP_TRIED
    if _NLP_TRIED:
        return _NLP
    _NLP_TRIED = True

    for model in (_MODEL_NAME, _FALLBACK_NAME):
        try:
            import spacy  # noqa: PLC0415
            _NLP = spacy.load(model)
            logger.info(f"spaCy NER cargado: {model}")
            return _NLP
        except OSError:
            logger.warning(f"spaCy model '{model}' no encontrado. Intentando descarga…")
            try:
                import subprocess, sys  # noqa: PLC0415
                subprocess.run([sys.executable, "-m", "spacy", "download", model], check=True)
                import spacy  # noqa: PLC0415
                _NLP = spacy.load(model)
                logger.info(f"spaCy NER descargado y cargado: {model}")
                return _NLP
            except Exception as exc:
                logger.warning(f"No se pudo cargar spaCy '{model}': {exc}")
        except Exception as exc:
            logger.warning(f"Error cargando spaCy '{model}': {exc}")

    logger.warning("spaCy no disponible. Se usará extracción por regex para alertas.")
    _NLP = False
    return None


def extract_subject(sentence: str, trigger_start: int) -> str:
    """
    Extrae el sujeto (qué vence/expira/renueva) de la oración.

    Args:
        sentence  : la oración completa que contiene la fecha
        trigger_start : posición dentro de `sentence` donde empieza el trigger
                        ("vence el", "expira el", etc.)

    Returns:
        Cadena limpia con el sujeto. Ejemplo: "licencia de uso del módulo NLP"
    """
    nlp = _get_nlp()

    if nlp:
        return _subject_via_spacy(nlp, sentence, trigger_start)

    # Fallback: regex — toma el último sustantivo/sintagma antes del trigger
    return _subject_via_regex(sentence, trigger_start)


def _clean_subject(text: str) -> str:
    """Limpia y normaliza el texto del sujeto extraído."""
    s = re.sub(r'\s+', ' ', text).strip()
    s = re.sub(r'^[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+', '', s)
    s = s.rstrip('.,;:').strip()
    s = re.sub(r'^(?:la |el |los |las |de |del |que |y |e )', '', s, flags=re.IGNORECASE)
    s = s.strip().capitalize()
    if len(s) > 80:
        cut = s.rfind(' ', 0, 80)
        s = s[:cut] if cut > 30 else s[:80]
    return s


def _subject_via_spacy(nlp, sentence: str, trigger_start: int) -> str:
    """Usa el dependency parser de spaCy para encontrar el sujeto real."""
    doc = nlp(sentence)

    best_subject_tokens: list = []
    best_dist = 9999

    for token in doc:
        if token.idx >= trigger_start:
            continue
        if token.dep_ in ("nsubj", "nsubjpass", "ROOT"):
            dist = trigger_start - token.idx
            if dist < best_dist:
                best_dist = dist
                subtree_tokens = list(token.subtree)
                best_subject_tokens = [
                    t for t in subtree_tokens
                    if t.idx < trigger_start
                ]

    if best_subject_tokens:
        subject = " ".join(t.text for t in sorted(best_subject_tokens, key=lambda t: t.idx))
        subject = _clean_subject(subject)
        if len(subject) >= 5:
            return subject

    chunks_before_trigger = [
        chunk for chunk in doc.noun_chunks
        if chunk.end_char <= trigger_start
    ]
    if chunks_before_trigger:
        subject = _clean_subject(chunks_before_trigger[-1].text)
        if len(subject) >= 5:
            return subject

    return _subject_via_regex(sentence, trigger_start)


def _subject_via_regex(sentence: str, trigger_start: int) -> str:
    """Extracción de sujeto por regex cuando spaCy no está disponible."""
    before = sentence[:trigger_start].strip()

    # Limpiar artefactos y tomar los últimos 80 chars antes del trigger
    before = re.sub(r'\s+', ' ', before)
    before = before[-100:].lstrip()

    # Quitar artículos/preposiciones al inicio
    before = re.sub(r'^(?:la |el |los |las |de |del |que |y |e |a )', '', before, flags=re.IGNORECASE)
    # Quitar puntuación al inicio (puede quedar tras lstrip)
    before = re.sub(r'^[,;:.\s]+', '', before)
    before = before.strip().capitalize()

    # Limitar a 80 chars cortando en palabra completa
    if len(before) > 80:
        cut = before.rfind(' ', 0, 80)
        before = before[:cut] if cut > 30 else before[:80]

    return before
