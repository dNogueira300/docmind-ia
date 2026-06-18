"""
Unit tests del servicio Gemini.

La API key y el cliente de Google se mockean siempre — estos tests
no hacen peticiones reales a la API de Gemini.
"""
import re
from unittest.mock import patch, MagicMock

import pytest

import app.services.gemini_service as gemini_svc


# ── Helper: resetear el singleton de cliente entre tests ─────────────────────

@pytest.fixture(autouse=True)
def reset_gemini_client():
    """Limpia el cliente singleton antes de cada test para evitar interferencias."""
    original = gemini_svc._client
    gemini_svc._client = None
    yield
    gemini_svc._client = original


# ── summarize_document ────────────────────────────────────────────────────────

def test_summarize_sin_api_key_usa_heuristica():
    """Sin API key, summarize_document usa el fallback heurístico."""
    with patch.object(gemini_svc.settings, "gemini_api_key", None):
        text = (
            "Contrato de prestación de servicios entre la Universidad Nacional "
            "de la Amazonía Peruana y la empresa TechSoft S.A.C. El objeto del "
            "presente contrato es la provisión de servicios de desarrollo de software. "
            "Monto: S/ 45,000.00. Vigencia: 6 meses."
        )
        result = gemini_svc.summarize_document(text, "contrato.pdf")
    assert isinstance(result, str)
    assert len(result) > 0
    assert len(result) <= 600


def test_summarize_texto_muy_corto_retorna_truncado():
    """Texto con menos de 80 chars se retorna tal cual, sin llamar a Gemini."""
    short = "Texto breve."
    with patch.object(gemini_svc.settings, "gemini_api_key", None):
        result = gemini_svc.summarize_document(short)
    assert result == short


def test_summarize_texto_vacio_retorna_vacio():
    with patch.object(gemini_svc.settings, "gemini_api_key", None):
        result = gemini_svc.summarize_document("")
    assert result == ""


def test_summarize_con_api_key_llama_a_gemini():
    """Con API key configurada, se llama al modelo Gemini."""
    mock_response = MagicMock()
    mock_response.text = "Contrato de servicios por S/ 45,000 entre UNAP y TechSoft S.A.C."

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    texto_largo = "a" * 200

    with patch.object(gemini_svc.settings, "gemini_api_key", "fake-key"), \
         patch("app.services.gemini_service._get_client", return_value=mock_client):
        result = gemini_svc.summarize_document(texto_largo, "doc.pdf")

    assert result == mock_response.text
    mock_client.models.generate_content.assert_called_once()


def test_summarize_gemini_falla_usa_heuristica():
    """Si Gemini lanza una excepción, se cae al fallback heurístico."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("timeout")

    text = (
        "El objeto del presente informe técnico es evaluar el estado "
        "de la infraestructura de red de la Universidad. Se concluye "
        "que el sistema requiere actualización urgente."
    )

    with patch.object(gemini_svc.settings, "gemini_api_key", "fake-key"), \
         patch("app.services.gemini_service._get_client", return_value=mock_client):
        result = gemini_svc.summarize_document(text, "informe.pdf")

    assert isinstance(result, str)
    assert len(result) > 0


def test_fallback_respeta_limite_600_chars():
    """El límite de 600 chars aplica SOLO a la heurística (sin Gemini disponible)."""
    # Texto largo sin API key → fuerza la ruta heurística.
    texto_largo = (
        "El objeto del presente contrato es la prestación integral de servicios. " * 50
    )
    with patch.object(gemini_svc.settings, "gemini_api_key", None):
        result = gemini_svc.summarize_document(texto_largo, "contrato.pdf")

    assert len(result) <= 600


def test_summarize_gemini_se_valida_por_contenido_no_longitud():
    """La ruta de Gemini se valida por contenido: devuelve el resumen tal cual,
    sin recortarlo a 600 chars (el cap es contrato del fallback, no de Gemini)."""
    resumen_gemini = (
        "Contrato de prestación de servicios entre la UNAP y TechSoft S.A.C. por "
        "S/ 45,000.00 con vigencia de 6 meses. " * 10  # > 600 chars, con contenido real
    )
    mock_response = MagicMock()
    mock_response.text = resumen_gemini

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(gemini_svc.settings, "gemini_api_key", "fake-key"), \
         patch("app.services.gemini_service._get_client", return_value=mock_client):
        result = gemini_svc.summarize_document("b" * 300)

    # Validación por contenido (no por longitud): se respeta el texto de Gemini.
    assert result == resumen_gemini.strip()
    assert "TechSoft" in result
    assert len(result) > 600  # la ruta de Gemini NO está limitada a 600


# ── _fallback_summary ─────────────────────────────────────────────────────────

def test_fallback_detecta_seccion_objeto():
    text = (
        "Contrato N.° 001.\n\n"
        "Objeto: Provisión de materiales de laboratorio para el año académico 2026. "
        "El monto total es de S/ 12,000. Vigencia: 12 meses."
    )
    result = gemini_svc._fallback_summary(text)
    assert "Provisión" in result or "materiales" in result.lower()


def test_fallback_primer_parrafo_sustancial():
    text = (
        "Iquitos, 01 de junio de 2026\n\n"
        "El presente memorando tiene como propósito informar sobre los avances "
        "del proyecto de digitalización documental iniciado en el primer trimestre."
    )
    result = gemini_svc._fallback_summary(text)
    assert len(result) > 30


def test_fallback_texto_corto_retorna_completo():
    text = "Acta firmada." * 10  # 130 chars
    result = gemini_svc._fallback_summary(text)
    assert len(result) > 0


# ── chat ──────────────────────────────────────────────────────────────────────

def test_chat_sin_api_key_retorna_mensaje_error():
    with patch.object(gemini_svc.settings, "gemini_api_key", None):
        result = gemini_svc.chat("¿Qué dice?", "texto del doc", "doc.pdf")
    assert "GEMINI_API_KEY" in result or "no está disponible" in result.lower()


def test_chat_responde_correctamente():
    mock_response = MagicMock()
    mock_response.text = "El monto es S/ 45,000.00."

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(gemini_svc.settings, "gemini_api_key", "fake-key"), \
         patch("app.services.gemini_service._get_client", return_value=mock_client):
        result = gemini_svc.chat(
            message="¿Cuál es el monto?",
            doc_text="El contrato es por S/ 45,000.00 con vigencia de 6 meses.",
            doc_name="contrato.pdf",
            history=[],
        )

    assert result == "El monto es S/ 45,000.00."


def test_chat_incluye_historial_en_prompt():
    """El historial debe pasarse al cliente; verificamos que se llama con el prompt completo."""
    mock_response = MagicMock()
    mock_response.text = "La vigencia es 6 meses."

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    history = [
        {"role": "user", "content": "¿Quiénes firman?"},
        {"role": "assistant", "content": "La UNAP y TechSoft."},
    ]

    with patch.object(gemini_svc.settings, "gemini_api_key", "fake-key"), \
         patch("app.services.gemini_service._get_client", return_value=mock_client):
        result = gemini_svc.chat(
            "¿Cuánto dura?", "Contrato 6 meses.", "contrato.pdf", history
        )

    # Verificar que se incluyó el historial en el prompt enviado
    call_args = mock_client.models.generate_content.call_args
    prompt_sent = call_args[1].get("contents") or call_args[0][1]
    assert "TechSoft" in prompt_sent  # historial incluido


def test_chat_falla_retorna_mensaje_error():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("connection reset")

    with patch.object(gemini_svc.settings, "gemini_api_key", "fake-key"), \
         patch("app.services.gemini_service._get_client", return_value=mock_client):
        result = gemini_svc.chat("¿Qué?", "texto", "doc.pdf")

    assert "No pude" in result or "error" in result.lower()


# ── chat_global ───────────────────────────────────────────────────────────────

def test_chat_global_sin_api_key():
    with patch.object(gemini_svc.settings, "gemini_api_key", None):
        result = gemini_svc.chat_global("¿Cuántos docs?", {})
    assert "no está disponible" in result.lower() or "GEMINI_API_KEY" in result


def test_chat_global_responde_con_contexto():
    mock_response = MagicMock()
    mock_response.text = "Hay 10 documentos en el sistema."

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    context = {"total_documentos": 10, "alertas_pendientes": 2}

    with patch.object(gemini_svc.settings, "gemini_api_key", "fake-key"), \
         patch("app.services.gemini_service._get_client", return_value=mock_client):
        result = gemini_svc.chat_global("¿Cuántos docs hay?", context)

    assert result == "Hay 10 documentos en el sistema."


# ── extract_text_from_image ───────────────────────────────────────────────────

def test_extract_image_sin_api_key_retorna_vacio():
    with patch.object(gemini_svc.settings, "gemini_api_key", None):
        result = gemini_svc.extract_text_from_image(b"\x89PNG\r\n")
    assert result == ""


def test_extract_image_con_api_key():
    """
    Mockea el módulo google.genai completo (no instalado en env local, solo Docker).
    Verifica que se llama al modelo y se retorna el texto extraído.
    """
    import sys

    mock_response = MagicMock()
    mock_response.text = "Texto extraído de la imagen por Gemini Vision."

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    mock_part = MagicMock()
    mock_types = MagicMock()
    mock_types.Part.from_bytes.return_value = mock_part

    mock_google_genai = MagicMock()
    mock_google_genai.types = mock_types

    mock_google = MagicMock()
    mock_google.genai = mock_google_genai

    fake_modules = {
        "google": mock_google,
        "google.genai": mock_google_genai,
        "google.genai.types": mock_types,
    }

    with patch.dict(sys.modules, fake_modules), \
         patch.object(gemini_svc.settings, "gemini_api_key", "fake-key"), \
         patch("app.services.gemini_service._get_client", return_value=mock_client):
        result = gemini_svc.extract_text_from_image(b"\x89PNG fake", "image/png")

    assert "Texto extraído" in result


def test_extract_image_falla_retorna_vacio():
    """Si la llamada al modelo falla, retorna string vacío."""
    import sys

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("Vision API error")

    mock_types = MagicMock()
    mock_types.Part.from_bytes.return_value = MagicMock()

    mock_google_genai = MagicMock()
    mock_google_genai.types = mock_types

    fake_modules = {
        "google": MagicMock(genai=mock_google_genai),
        "google.genai": mock_google_genai,
        "google.genai.types": mock_types,
    }

    with patch.dict(sys.modules, fake_modules), \
         patch.object(gemini_svc.settings, "gemini_api_key", "fake-key"), \
         patch("app.services.gemini_service._get_client", return_value=mock_client):
        result = gemini_svc.extract_text_from_image(b"\xff\xd8\xff fake", "image/jpeg")

    assert result == ""
