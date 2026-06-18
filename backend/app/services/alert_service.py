"""Servicio de detección de fechas de vencimiento en texto OCR.

Soporta dos formatos de fecha:
  - Numérico:  20/04/2026  |  20-04-2026  |  20.04.2026
  - Texto ES:  20 de abril de 2026  |  31 de diciembre de 2026
"""
import logging
import re
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger("docmind")

ALERT_DAYS_BEFORE = 30

# ── Meses en español ──────────────────────────────────────────────────────────
_MONTHS_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
    'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
    'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
}
_MONTH_NAMES = '|'.join(_MONTHS_ES)

# ── Patrones de fecha ─────────────────────────────────────────────────────────
# Formato numérico:  20/04/2026  o  20-04-2026  o  20.04.2026
_DATE_NUM = r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}'
# Formato texto ES:  20 de abril de 2026
_DATE_TXT = rf'\d{{1,2}}\s+de\s+(?:{_MONTH_NAMES})\s+de\s+\d{{4}}'
# Combinado (cualquiera de los dos)
_DATE_ANY = rf'(?:{_DATE_TXT}|{_DATE_NUM})'

# ── Patrones de contexto (trigger keywords + fecha) ───────────────────────────
# Cada tupla: (regex_con_grupo_de_fecha, alert_type)
_TYPE_LABELS = {
    'expiry':   'Vencimiento',
    'deadline': 'Plazo límite',
    'renewal':  'Renovación',
}

_PATTERNS: list[tuple[str, str]] = [
    # vence / vencimiento
    (rf'vence?\s+el\s+({_DATE_ANY})',                           'expiry'),
    (rf'fecha\s+de\s+vencimiento\s*[:\s]+({_DATE_ANY})',        'expiry'),
    (rf'vencimiento\s+(?:de\s+[\w\s]{{1,30}})?\s+el\s+({_DATE_ANY})', 'expiry'),

    # válido / vigencia
    (rf'v[áa]lido\s+hasta\s+(?:el\s+)?({_DATE_ANY})',           'expiry'),
    (rf'vigente?\s+hasta\s+(?:el\s+)?({_DATE_ANY})',             'expiry'),
    (rf'vigencia\s+(?:hasta\s+)?(?:el\s+)?({_DATE_ANY})',        'expiry'),

    # expira
    (rf'expira?\s+el\s+({_DATE_ANY})',                           'expiry'),
    (rf'expiraci[oó]n\s+(?:del?\s+)?(?:contrato\s+)?(?:el\s+)?({_DATE_ANY})', 'expiry'),

    # fecha límite / plazo máximo / fecha máxima
    (rf'fecha\s+l[íi]mite\s*[:\s]*({_DATE_ANY})',               'deadline'),
    (rf'plazo\s+(?:m[áa]ximo|l[íi]mite)\s+(?:de\s+[\w\s]{{1,40}})?\s+el\s+({_DATE_ANY})', 'deadline'),
    (rf'fecha\s+m[áa]xima\s+(?:de\s+[\w\s]{{1,40}})?\s+el\s+({_DATE_ANY})', 'deadline'),
    (rf'a\s+m[áa]s\s+tardar\s+(?:el\s+)?({_DATE_ANY})',         'deadline'),
    (rf'plazo\s+m[áa]ximo\s+establecido.{{0,60}}({_DATE_ANY})',  'deadline'),

    # renovación
    (rf'renovaci[oó]n\s*[:\s]*(?:el\s+)?({_DATE_ANY})',         'renewal'),
    (rf'debe\s+(?:gestionar\s+)?(?:la\s+)?renovaci[oó]n.{{0,80}}({_DATE_ANY})', 'renewal'),

    # "a partir del" / "a los" (para fechas de inicio de período de soporte etc.)
    # no incluidas — solo nos interesan fechas de cierre/vencimiento
]


def _parse_date_numeric(raw: str) -> Optional[date]:
    """Parsea DD/MM/YYYY o DD-MM-YYYY o DD.MM.YYYY."""
    parts = re.split(r'[\/\-\.]', raw.strip())
    if len(parts) != 3:
        return None
    try:
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        if year < 100:
            year += 2000
        return date(year, month, day)
    except (ValueError, TypeError):
        return None


def _parse_date_text(raw: str) -> Optional[date]:
    """Parsea '20 de abril de 2026'."""
    m = re.match(
        rf'(\d{{1,2}})\s+de\s+({_MONTH_NAMES})\s+de\s+(\d{{4}})',
        raw.strip(), re.IGNORECASE
    )
    if not m:
        return None
    try:
        day   = int(m.group(1))
        month = _MONTHS_ES[m.group(2).lower()]
        year  = int(m.group(3))
        return date(year, month, day)
    except (KeyError, ValueError):
        return None


def _parse_date(raw: str) -> Optional[date]:
    """Intenta parsear la fecha en cualquiera de los dos formatos."""
    d = _parse_date_text(raw)
    if d:
        return d
    return _parse_date_numeric(raw)


def _build_alert_title(text: str, m: "re.Match", alert_type: str) -> str:
    """
    Genera una descripción clara para la alerta.
    Intenta usar Gemini primero; cae a NER/heurística si no está disponible.
    """
    label = _TYPE_LABELS.get(alert_type, 'Alerta')

    # Extraer oración de contexto (con mayor ventana para Gemini)
    sentence_start = max(0, text.rfind('.', 0, m.start()) + 1)
    sentence_end   = min(len(text), m.end() + 150)
    sentence       = text[sentence_start:sentence_end].strip()

    # Intentar con Gemini para descripción más clara
    from app.services import gemini_service  # noqa: PLC0415
    desc = gemini_service.generate_alert_description(sentence, alert_type)
    if desc:
        return desc

    # Fallback: NER spaCy
    from app.services.ner_service import extract_subject  # noqa: PLC0415
    trigger_pos = m.start() - sentence_start
    subject = extract_subject(sentence, trigger_pos)
    subject = _clean_subject_text(subject)

    if not subject or len(subject) < 5:
        return label

    return f"{label}: {subject}"


def _clean_subject_text(subject: str) -> str:
    """Limpia el sujeto extraído para mostrarlo correctamente."""
    s = re.sub(r'\s+', ' ', subject).strip()
    s = re.sub(r'^[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+', '', s)
    s = s.rstrip('.,;:').strip()
    s = re.sub(r'^(?:la |el |los |las |de |del |que |y |e )', '', s, flags=re.IGNORECASE)
    s = s.strip().capitalize()
    if len(s) > 200:
        cut = s.rfind(' ', 0, 200)
        s = s[:cut] if cut > 50 else s[:200]
    return s


def detect_expiry_dates(text: str) -> list[dict]:
    """
    Escanea el texto OCR buscando fechas de vencimiento con sus keywords.

    Devuelve lista de dicts con:
      detected_date, alert_date, alert_type, detail (fragmento de contexto)
    """
    if not text:
        return []

    text_lower = text.lower()
    today = date.today()
    results: list[dict] = []
    seen: set[date] = set()

    for pattern, alert_type in _PATTERNS:
        for m in re.finditer(pattern, text_lower):
            raw_date = m.group(1)
            detected = _parse_date(raw_date)

            if not detected:
                continue
            if detected < today:
                continue          # fechas pasadas no generan alertas
            if detected in seen:
                continue          # evitar duplicados por misma fecha
            seen.add(detected)

            alert_date = detected - timedelta(days=ALERT_DAYS_BEFORE)
            if alert_date < today:
                alert_date = today   # si ya pasó el momento de alerta, disparar hoy

            # Generar un título limpio para la alerta:
            # extraer el SUJETO que vence/expira (texto justo antes del trigger),
            # en lugar de mostrar un fragmento crudo del OCR.
            detail = _build_alert_title(text, m, alert_type)

            results.append({
                'detected_date': detected,
                'alert_date':    alert_date,
                'alert_type':    alert_type,
                'detail':        detail,
            })

            logger.info(
                f"Alerta detectada: tipo={alert_type} fecha={detected} "
                f"alerta={alert_date} patrón=«{m.group(0)[:60]}»"
            )

    logger.info(f"detect_expiry_dates: {len(results)} alerta(s) encontrada(s)")
    return results


def persist_alerts(db, document_id: str, organization_id, alerts: list[dict]) -> None:
    """Persiste las alertas en BD evitando duplicados por (document_id, detected_date)."""
    from app.models.alert import DocumentAlert, AlertType, AlertStatus
    import uuid

    for a in alerts:
        try:
            alert_type_val = AlertType(a['alert_type'])
        except ValueError:
            alert_type_val = AlertType.expiry

        alert = DocumentAlert(
            document_id=uuid.UUID(str(document_id)),
            organization_id=organization_id,
            alert_type=alert_type_val,
            detected_date=a['detected_date'],
            alert_date=a['alert_date'],
            status=AlertStatus.pending,
            detail=a.get('detail'),
        )
        db.add(alert)

    try:
        db.commit()
        logger.info(f"Alertas guardadas en BD: {len(alerts)} para doc={document_id}")
    except Exception as exc:
        db.rollback()
        logger.error(f"Error guardando alertas para doc={document_id}: {exc}")
