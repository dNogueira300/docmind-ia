"""
Servicio de integración con Google Gemini API.

Funciones:
  - summarize_document(): resumen inteligente de texto OCR
  - chat(): chatbot documental con historial de conversación

Modelo: gemini-1.5-flash (free tier: 15 RPM, 1M tokens/día)
SDK:    google-genai >= 1.0.0  (pip install google-genai)
"""
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("docmind")

_client = None
MODEL = "gemini-2.5-flash"

# ── Prompts ───────────────────────────────────────────────────────────────────

_SUMMARY_PROMPT = """\
Eres un asistente especializado en documentos administrativos y legales peruanos.
Lee el siguiente documento y genera un resumen conciso de 2 a 4 oraciones que incluya, \
cuando la información esté disponible en el texto:

- Tipo de documento (contrato, carta, resolución, informe, memorándum, etc.)
- Partes involucradas (instituciones o personas)
- Fecha de emisión o suscripción
- Objeto o propósito principal
- Monto económico (si aplica)
- Fechas clave de vigencia, entrega o vencimiento (si aplica)

Responde ÚNICAMENTE con el resumen. Sin títulos, sin introducciones, sin listas. \
Usa español formal y redacción continua.

DOCUMENTO:
{text}
"""

_CHAT_SYSTEM = """\
Eres DocMind, el asistente inteligente del sistema de gestión documental DocMind IA.
Tienes acceso al contenido completo del documento "{doc_name}".
Responde las preguntas del usuario basándote EXCLUSIVAMENTE en la información del documento.
Si algún dato no está en el documento, dilo claramente.
Responde en español, de forma precisa y concisa. Sé directo y útil.
"""

_GLOBAL_CHAT_SYSTEM = """\
Eres DocMind, el asistente inteligente del sistema de gestión documental DocMind IA.
Tienes acceso a las estadísticas actuales del sistema de la organización del usuario.

DATOS DEL SISTEMA (actualizados al momento de la consulta):
{context_json}

Puedes responder preguntas sobre documentos, usuarios, categorías, alertas y cualquier \
dato del sistema. Si no tienes el dato exacto, indícalo y sugiere cómo encontrarlo.
Responde en español, de forma concisa y directa.
"""


# ── Cliente ───────────────────────────────────────────────────────────────────

def _get_client():
    global _client
    if _client is None:
        from google import genai  # noqa: PLC0415
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY no está configurada en .env")
        _client = genai.Client(api_key=settings.gemini_api_key)
        logger.info("Cliente Gemini inicializado correctamente")
    return _client


def _is_available() -> bool:
    return bool(settings.gemini_api_key)


# ── Funciones públicas ────────────────────────────────────────────────────────

def summarize_document(text: str, doc_name: str = "") -> str:
    """
    Genera un resumen inteligente del texto OCR del documento.

    Fallback: extracción heurística si Gemini no está disponible o falla.
    """
    if not text or len(text.strip()) < 80:
        return text.strip()[:300] if text else ""

    if not _is_available():
        logger.warning("Gemini no disponible (API key ausente). Usando heurística.")
        return _fallback_summary(text)

    try:
        client = _get_client()
        # Limitar a 8000 chars (~2000 tokens) — suficiente para documentos de 10 páginas
        truncated = text[:8000]
        prompt = _SUMMARY_PROMPT.format(text=truncated)

        response = client.models.generate_content(model=MODEL, contents=prompt)
        summary = response.text.strip()

        if summary:
            logger.info(f"Resumen Gemini ({len(summary)} chars): {summary[:100]}…")
            return summary[:600]

    except Exception as exc:
        logger.warning(f"Error en Gemini summarize: {exc}. Usando heurística.")

    return _fallback_summary(text)


def chat(
    message: str,
    doc_text: str,
    doc_name: str,
    history: Optional[list[dict]] = None,
) -> str:
    """
    Responde una pregunta sobre el documento.

    Args:
        message:  Pregunta del usuario
        doc_text: Texto OCR del documento (contexto)
        doc_name: Nombre del archivo
        history:  Lista de dicts {role: 'user'|'assistant', content: str}

    Returns:
        Respuesta en texto del modelo.
    """
    if not _is_available():
        return "El chatbot no está disponible: configura GEMINI_API_KEY en el .env del proyecto."

    try:
        client = _get_client()

        # Construir el prompt completo incluyendo contexto del documento e historial
        parts = [
            _CHAT_SYSTEM.format(doc_name=doc_name),
            f"\nCONTENIDO DEL DOCUMENTO (primeros 8000 caracteres):\n{doc_text[:8000]}",
        ]

        # Historial reciente (máx. 6 turnos = 12 mensajes)
        for turn in (history or [])[-12:]:
            role_label = "Usuario" if turn.get("role") == "user" else "Asistente"
            parts.append(f"\n{role_label}: {turn.get('content', '')}")

        parts.append(f"\nUsuario: {message}")
        parts.append("\nAsistente:")

        full_prompt = "\n".join(parts)

        response = client.models.generate_content(model=MODEL, contents=full_prompt)
        reply = response.text.strip()

        logger.info(f"Chat Gemini → {len(reply)} chars: {reply[:60]}…")
        return reply

    except Exception as exc:
        logger.error(f"Error en Gemini chat: {exc}")
        return "No pude procesar tu consulta. Verifica la conexión e intenta de nuevo."


def chat_global(
    message: str,
    context: dict,
    history: Optional[list[dict]] = None,
) -> str:
    """
    Chatbot global del sistema. Responde preguntas sobre estadísticas,
    documentos, usuarios y cualquier dato de la plataforma.
    """
    if not _is_available():
        return "El asistente no está disponible: configura GEMINI_API_KEY en .env."

    try:
        import json  # noqa: PLC0415
        client = _get_client()

        context_json = json.dumps(context, ensure_ascii=False, indent=2)
        system_ctx = _GLOBAL_CHAT_SYSTEM.format(context_json=context_json)

        parts = [system_ctx]
        for turn in (history or [])[-10:]:
            role_label = "Usuario" if turn.get("role") == "user" else "DocMind"
            parts.append(f"\n{role_label}: {turn.get('content', '')}")
        parts.append(f"\nUsuario: {message}")
        parts.append("\nDocMind:")

        response = client.models.generate_content(model=MODEL, contents="\n".join(parts))
        return response.text.strip()

    except Exception as exc:
        logger.error(f"Error en Gemini chat_global: {exc}")
        return "No pude procesar tu consulta. Intenta de nuevo."


def extract_text_from_image(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """
    Extrae texto de una imagen usando Gemini Vision (multimodal).

    Se usa como fallback cuando Tesseract devuelve 0 caracteres en todos los
    intentos (documentos oscuros, fotos de teléfono, PDFs de baja calidad).

    Args:
        image_bytes: bytes PNG o JPEG de la imagen
        mime_type:   'image/png' o 'image/jpeg'

    Returns:
        Texto extraído o string vacío si falla.
    """
    if not _is_available():
        logger.warning("Gemini Vision OCR no disponible: API key ausente.")
        return ""

    try:
        from google.genai import types  # noqa: PLC0415

        client = _get_client()

        prompt = (
            "Eres un sistema OCR de alta precisión especializado en documentos en español. "
            "Extrae TODO el texto visible en esta imagen, incluyendo encabezados, cuerpo, "
            "tablas, firmas y pies de página. "
            "Devuelve ÚNICAMENTE el texto extraído, sin comentarios, sin markdown, "
            "respetando la estructura y los párrafos del documento original."
        )

        response = client.models.generate_content(
            model=MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
        )

        text = (response.text or "").strip()
        logger.info(f"Gemini Vision OCR: {len(text)} chars extraídos de imagen {mime_type}")
        return text

    except Exception as exc:
        logger.warning(f"Error en Gemini Vision OCR: {exc}")
        return ""


# ── Fallback heurístico ───────────────────────────────────────────────────────

def _fallback_summary(text: str) -> str:
    """Extracción heurística cuando Gemini no está disponible."""
    import re  # noqa: PLC0415

    clean = re.sub(r'\n+', ' ', text)
    clean = re.sub(r'\s{2,}', ' ', clean).strip()

    # Buscar sección OBJETO / ASUNTO
    m = re.search(
        r'(?:objeto|asunto|propósito|materia)[^\n]*[:.\n]\s*(.{60,600})',
        clean, re.IGNORECASE
    )
    if m:
        fragment = m.group(1).strip()
        if len(fragment) <= 400:
            return fragment
        cut = fragment.rfind(' ', 0, 400)
        return (fragment[:cut] if cut > 200 else fragment[:400]) + '…'

    # Fallback: primer párrafo sustancial (saltar headers)
    skip = re.compile(
        r'^(?:\w[\w\s]+,\s+\d{1,2}\s+de\s+\w+|\d+$|[A-ZÁÉÍÓÚÜÑ\s\W]{10,}$|N[°\.])',
        re.IGNORECASE
    )
    for para in re.split(r'(?<=\.)\s{2,}', clean):
        para = para.strip()
        if len(para) >= 60 and not skip.match(para):
            return para[:400] + ('…' if len(para) > 400 else '')

    return clean[:400] + ('…' if len(clean) > 400 else '')
