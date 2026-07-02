"""
Servicio de integración con Google Gemini API.

Funciones:
  - summarize_document(): resumen inteligente de texto OCR
  - chat(): chatbot documental con historial de conversación

Modelo: gemini-1.5-flash (free tier: 15 RPM, 1M tokens/día)
SDK:    google-genai >= 1.0.0  (pip install google-genai)
"""
import json
import logging
import re
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("docmind")

_client = None
MODEL = "gemini-2.5-flash"

# ── Prompts ───────────────────────────────────────────────────────────────────

_SUMMARY_PROMPT = """\
Eres un asistente especializado en documentos administrativos y legales peruanos.
El archivo se llama "{doc_name}". Lee su contenido y genera un resumen en español \
que incluya, cuando la información esté disponible en el texto:

- Tipo de documento (contrato, carta, resolución, informe, memorándum, orden de servicio, propuesta, reporte, etc.)
- Partes involucradas (instituciones, empresas o personas)
- Fecha de emisión o suscripción
- Objeto o propósito principal del documento
- Monto económico y condiciones de pago (si aplica)
- Fechas clave de vigencia, entrega, vencimiento o hitos (si aplica)
- Obligaciones principales o compromisos asumidos (si aplica)

Responde ÚNICAMENTE con el resumen. Sin títulos, sin introducciones, sin listas. \
Usa español formal y redacción continua. El resumen debe ser completo pero conciso: \
máximo 220 palabras. Prioriza los datos más relevantes si el documento es extenso.

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

Los datos incluyen:
- Totales y estados de documentos
- Distribución por categoría y por usuario
- Últimos 5 documentos subidos
- Alertas de vencimiento pendientes con nombre del documento, tipo y fechas exactas
- Documentos en estado 'review' o 'error' que necesitan atención
- Lista completa de usuarios con nombre, rol y estado activo
- Almacenamiento total usado (KB y MB)
- Reglas de riesgo configuradas (nombre, nivel, descripción, palabras clave, tamaño mínimo)
- Lista de documentos con riesgo medio, alto o crítico (nombre, nivel, categoría)

Instrucciones:
- Si preguntan por qué un documento tiene determinado nivel de riesgo, cruza el nombre \
  del documento con las reglas de riesgo disponibles y explícalo con detalle.
- Si preguntan qué documentos están por vencer, usa "alertas_pendientes_detalle" con fechas exactas.
- Si preguntan qué documentos necesitan atención, usa "documentos_que_necesitan_atencion".
- Si preguntan por usuarios, roles o quién puede hacer qué, usa "usuarios".
- Si preguntan por almacenamiento, usa "almacenamiento_total_mb".
Responde en español, de forma concisa y directa. Si no tienes el dato exacto, indícalo.
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
        prompt = _SUMMARY_PROMPT.format(text=truncated, doc_name=doc_name or "desconocido")

        response = client.models.generate_content(model=MODEL, contents=prompt)
        summary = response.text.strip()

        if summary:
            logger.info(f"Resumen Gemini ({len(summary)} chars): {summary[:100]}…")
            return summary

    except Exception as exc:
        logger.warning(f"Error en Gemini summarize: {exc}. Usando heurística.")

    return _fallback_summary(text)


# ── Clasificación ───────────────────────────────────────────────────────────

_CLASSIFY_PROMPT = """\
Eres un clasificador de documentos administrativos y legales peruanos.
Clasifica el siguiente documento en UNA de estas categorías EXACTAS:
{categories}

Responde SOLO con un JSON válido, sin texto adicional ni markdown:
{{"categoria": "<nombre EXACTO de la lista>", "confianza": <número entre 0.0 y 1.0>}}

Reglas:
- "categoria" debe ser una copia literal de un nombre de la lista.
- "confianza" indica qué tan seguro estás (1.0 = certeza total).
- Si ninguna encaja bien, elige la más cercana con confianza baja (< 0.5).

DOCUMENTO ("{doc_name}"):
{text}
"""

_SUGGEST_PROMPT = """\
Eres un organizador de taxonomías documentales. La organización ya tiene estas \
categorías:
{categories}

El siguiente documento NO encaja bien en ninguna. Propón el nombre de UNA categoría \
nueva, corta (1-3 palabras), en español, en singular o plural natural, que describa \
el TIPO de documento (no su contenido específico). Ejemplos de buenos nombres: \
"Facturas", "Contratos", "Resoluciones", "Licencias de software".

Responde SOLO con un JSON válido, sin texto adicional ni markdown:
{{"categoria_sugerida": "<nombre>", "confianza": <número entre 0.0 y 1.0>}}

Si el documento sí encaja en una categoría existente o no amerita una nueva, responde:
{{"categoria_sugerida": null, "confianza": 0.0}}

DOCUMENTO ("{doc_name}"):
{text}
"""


def _extract_json(raw: str) -> Optional[dict]:
    """Extrae el primer objeto JSON de la respuesta (tolera fences ```json)."""
    if not raw:
        return None
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except (json.JSONDecodeError, ValueError):
        return None


_CLASSIFY_SUGGEST_PROMPT = """\
Eres un clasificador de documentos administrativos y legales peruanos.
Categorías existentes en el sistema:
{categories}

Analiza el TIPO de documento y decide:
- Si su tipo corresponde CLARAMENTE a una de las categorías existentes, devuélvela
  en "categoria" (copia literal de la lista) con una confianza alta.
- Si su tipo NO corresponde a ninguna —aunque tenga relación temática— NO lo fuerces:
  deja "categoria" en null y propón en "categoria_nueva" un nombre corto para el tipo
  de documento (1-3 palabras, en plural natural: "Facturas", "Cartas de aceptación").

Ejemplos:
- Una factura y NO existe categoría de facturas → {{"categoria": null, "confianza": 0.0, "categoria_nueva": "Facturas"}}
- Un contrato y existe "Contratos" → {{"categoria": "Contratos", "confianza": 0.9, "categoria_nueva": null}}

Responde SOLO con JSON válido, sin markdown ni texto adicional:
{{"categoria": "<nombre exacto de la lista o null>", "confianza": <0.0-1.0>, "categoria_nueva": "<nombre o null>"}}

DOCUMENTO ("{doc_name}"):
{text}
"""


def classify_or_suggest(
    text: str, categories: list[str], doc_name: str = ""
) -> Optional[dict]:
    """
    Decide en una sola llamada si el documento encaja en una categoría existente o
    amerita una nueva.

    Returns:
        dict {"category": str|None, "confidence": float, "new_category": str|None}
        - category: nombre EXACTO de una categoría existente, o None si no encaja.
        - new_category: nombre propuesto para una categoría nueva (si no encaja), o None.
        None si Gemini no está disponible o falla → el caller aplica su fallback.
    """
    if not _is_available() or not text or not text.strip():
        return None
    try:
        client = _get_client()
        prompt = _CLASSIFY_SUGGEST_PROMPT.format(
            categories="\n".join(f"- {c}" for c in categories) or "(ninguna)",
            doc_name=doc_name or "desconocido",
            text=text[:4000],
        )
        response = client.models.generate_content(model=MODEL, contents=prompt)
        data = _extract_json(response.text or "")
        if not data:
            return None

        raw_cat = data.get("categoria")
        match = None
        if raw_cat:
            match = next(
                (c for c in categories if c.lower() == str(raw_cat).strip().lower()),
                None,
            )
        conf = max(0.0, min(1.0, float(data.get("confianza", 0.0))))

        raw_new = data.get("categoria_nueva")
        new_cat = str(raw_new).strip() if raw_new else None
        # No proponer algo que ya existe.
        if new_cat and any(new_cat.lower() == c.lower() for c in categories):
            new_cat = None

        logger.info(
            f"Gemini clasificación: categoria={match!r} conf={conf:.2f} "
            f"nueva={new_cat!r}"
        )
        return {"category": match, "confidence": conf, "new_category": new_cat}
    except Exception as exc:
        logger.warning(f"Error en Gemini classify_or_suggest: {exc}")
        return None


def classify_document(
    text: str, categories: list[str], doc_name: str = ""
) -> Optional[tuple[str, float]]:
    """
    Clasifica el texto contra las categorías de la organización usando Gemini.

    Returns:
        (nombre_categoria, confianza) si Gemini responde y la categoría es válida;
        None si Gemini no está disponible o falla → el caller aplica su fallback.
    """
    if not _is_available() or not text or not text.strip() or not categories:
        return None
    try:
        client = _get_client()
        prompt = _CLASSIFY_PROMPT.format(
            categories="\n".join(f"- {c}" for c in categories),
            doc_name=doc_name or "desconocido",
            text=text[:4000],
        )
        response = client.models.generate_content(model=MODEL, contents=prompt)
        data = _extract_json(response.text or "")
        if not data:
            return None
        cat = str(data.get("categoria", "")).strip()
        # La categoría debe existir en la lista (match case-insensitive).
        match = next((c for c in categories if c.lower() == cat.lower()), None)
        if not match:
            return None
        conf = max(0.0, min(1.0, float(data.get("confianza", 0.0))))
        logger.info(f"Clasificación Gemini: '{match}' (confianza={conf:.2f})")
        return (match, conf)
    except Exception as exc:
        logger.warning(f"Error en Gemini classify: {exc}")
        return None


def suggest_category(
    text: str, existing_categories: list[str], doc_name: str = ""
) -> Optional[tuple[str, float]]:
    """
    Propone una categoría NUEVA si el documento no encaja en las existentes.

    Returns:
        (nombre_sugerido, confianza) si Gemini propone una categoría nueva válida
        que NO existe ya; None en cualquier otro caso.
    """
    if not _is_available() or not text or not text.strip():
        return None
    try:
        client = _get_client()
        prompt = _SUGGEST_PROMPT.format(
            categories="\n".join(f"- {c}" for c in existing_categories) or "(ninguna)",
            doc_name=doc_name or "desconocido",
            text=text[:4000],
        )
        response = client.models.generate_content(model=MODEL, contents=prompt)
        data = _extract_json(response.text or "")
        if not data:
            return None
        name = data.get("categoria_sugerida")
        if not name or not str(name).strip():
            return None
        name = str(name).strip()
        # No sugerir algo que ya existe (case-insensitive).
        if any(name.lower() == c.lower() for c in existing_categories):
            return None
        conf = max(0.0, min(1.0, float(data.get("confianza", 0.0))))
        logger.info(f"Categoría sugerida por Gemini: '{name}' (confianza={conf:.2f})")
        return (name, conf)
    except Exception as exc:
        logger.warning(f"Error en Gemini suggest_category: {exc}")
        return None


_SUMMARY_STRUCTURE_PROMPT = """\
Eres un asistente experto en documentos administrativos y legales peruanos.
A partir del TEXTO OCR (extraído sin formato) del archivo "{doc_name}", produces
DOS cosas en una sola respuesta JSON:

1) "summary": un resumen en español, formal y de redacción continua (máximo 220 \
palabras, sin títulos ni listas), que incluya cuando aparezca en el texto: tipo de \
documento, partes involucradas, fecha, objeto o propósito, montos y condiciones, \
fechas clave (vigencia/entrega/vencimiento) y obligaciones principales.

2) "blocks": la reconstrucción de la ESTRUCTURA del documento como lista de bloques,
respetando el orden original. Corrige espaciados obvios del OCR pero NO inventes datos.
Tipos de bloque válidos:
- {{"type": "heading", "level": 1-3, "text": "..."}}   (títulos y secciones)
- {{"type": "paragraph", "text": "..."}}               (párrafos de texto corrido)
- {{"type": "bullets", "items": ["...", "..."]}}       (listas con viñetas)
- {{"type": "table", "header": ["col1","col2"], "rows": [["a","b"], ["c","d"]]}}
Reglas de "blocks": une las líneas de un mismo párrafo en un solo "paragraph"; los
datos tabulares (filas y columnas) van como "table"; los títulos numerados
("1. Resumen…") van como "heading" nivel 2; el emisor y el título principal pueden
ir como "heading" nivel 1.

Responde SOLO con JSON válido, sin markdown ni texto adicional, con esta forma:
{{"summary": "...", "blocks": [ ...bloques... ]}}

TEXTO OCR:
{text}
"""


def summarize_and_structure(text: str, doc_name: str = "") -> Optional[dict]:
    """
    Genera en UNA sola llamada a Gemini el resumen y la estructura del documento
    (bloques para el .docx). Ahorra un crédito frente a hacer dos llamadas.

    Returns:
        dict {"summary": str, "blocks": list[dict] | None}, o None si el texto
        está vacío. Si Gemini no está disponible o falla, devuelve el resumen
        heurístico y blocks=None (el caller usa el parser heurístico del .docx).
    """
    if not text or not text.strip():
        return None
    if len(text.strip()) < 80:
        return {"summary": text.strip()[:300], "blocks": None}
    if not _is_available():
        logger.warning("Gemini no disponible — resumen heurístico, sin estructura IA.")
        return {"summary": _fallback_summary(text), "blocks": None}

    try:
        client = _get_client()
        prompt = _SUMMARY_STRUCTURE_PROMPT.format(
            doc_name=doc_name or "desconocido", text=text[:8000]
        )
        response = client.models.generate_content(model=MODEL, contents=prompt)
        data = _extract_json(response.text or "")
        if not data:
            return {"summary": _fallback_summary(text), "blocks": None}

        summary = str(data.get("summary") or "").strip() or _fallback_summary(text)

        blocks = data.get("blocks")
        valid_blocks = None
        if isinstance(blocks, list):
            valid = [b for b in blocks if isinstance(b, dict) and b.get("type")]
            valid_blocks = valid or None

        logger.info(
            f"Gemini resumen+estructura: {len(summary)} chars de resumen, "
            f"{len(valid_blocks) if valid_blocks else 0} bloque(s) para '{doc_name}'"
        )
        return {"summary": summary, "blocks": valid_blocks}
    except Exception as exc:
        logger.warning(f"Error en Gemini summarize_and_structure: {exc}")
        return {"summary": _fallback_summary(text), "blocks": None}


def rerank_semantic(query: str, candidates: list[dict]) -> Optional[list[str]]:
    """
    Re-rankea semánticamente candidatos de búsqueda (ya filtrados por FTS).

    Args:
        query: consulta en lenguaje natural del usuario.
        candidates: lista de dicts {"id": str, "filename": str, "snippet": str}.

    Returns:
        Lista de IDs ordenada por relevancia semántica, o None si Gemini falla
        (el caller mantiene el orden FTS original).
    """
    if not _is_available() or not query.strip() or not candidates:
        return None
    try:
        client = _get_client()
        items = "\n".join(
            f'{i}. id={c["id"]} | {c.get("filename", "")} | {c.get("snippet", "")[:300]}'
            for i, c in enumerate(candidates)
        )
        prompt = (
            "Ordena estos documentos por relevancia semántica frente a la consulta "
            f'del usuario: "{query}".\n\n'
            f"DOCUMENTOS:\n{items}\n\n"
            'Responde SOLO con un JSON: {"orden": ["<id1>", "<id2>", ...]} con los '
            "ids de los documentos relevantes, del más al menos relevante. Omite los "
            "irrelevantes."
        )
        response = client.models.generate_content(model=MODEL, contents=prompt)
        data = _extract_json(response.text or "")
        if not data or "orden" not in data:
            return None
        valid_ids = {c["id"] for c in candidates}
        ordered = [str(i) for i in data["orden"] if str(i) in valid_ids]
        return ordered or None
    except Exception as exc:
        logger.warning(f"Error en Gemini rerank_semantic: {exc}")
        return None


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


def generate_alert_description(sentence: str, alert_type: str) -> str:
    """
    Genera una descripción clara para una alerta de vencimiento usando Gemini.

    Args:
        sentence:   Fragmento de texto OCR que contiene el patrón de vencimiento.
        alert_type: 'expiry', 'deadline' o 'renewal'.

    Returns:
        Una oración descriptiva, o cadena vacía si Gemini no está disponible.
    """
    _TYPE_LABELS = {"expiry": "Vencimiento", "deadline": "Plazo límite", "renewal": "Renovación"}
    label = _TYPE_LABELS.get(alert_type, "Alerta")

    if not _is_available() or not sentence or not sentence.strip():
        return ""

    try:
        client = _get_client()
        prompt = (
            f"Eres un asistente de gestión documental. "
            f"El siguiente fragmento de texto fue detectado como una alerta de tipo '{label}'.\n\n"
            f"FRAGMENTO: {sentence[:400]}\n\n"
            f"Genera UNA sola oración en español que explique claramente qué es lo que vence o tiene plazo, "
            f"cuándo y por qué es importante. Sin comillas, sin títulos, sin punto final."
        )
        response = client.models.generate_content(model=MODEL, contents=prompt)
        desc = (response.text or "").strip().rstrip(".")
        if desc:
            logger.info(f"Gemini alerta '{alert_type}': {desc[:80]}")
            return desc
    except Exception as exc:
        logger.warning(f"Error generando descripción de alerta con Gemini: {exc}")
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
