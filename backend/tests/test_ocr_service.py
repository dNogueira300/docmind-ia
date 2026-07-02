"""Tests de las heurísticas de calidad del OCR (filtrado de show-through).

Estas funciones son Python puro y no requieren Tesseract ni MinIO, así que se
prueban de forma aislada. Cubren el caso real: un escaneo con texto fantasma del
reverso de la hoja (bleed-through) que se transparenta como líneas ilegibles.
"""
import sys
import types

# Stubs para no cargar dependencias pesadas al importar el módulo.
sys.modules.setdefault("pytesseract", types.ModuleType("pytesseract"))
sys.modules.setdefault(
    "app.services.minio_service", types.ModuleType("minio_service")
)

from app.services import ocr_service  # noqa: E402


CLEAN = (
    "4. Riesgos identificados\n"
    "El proyecto DocMind IA presenta riesgo de retraso por dependencia de la "
    "disponibilidad del equipo tecnico del cliente para las pruebas de aceptacion.\n"
    "La propuesta para Minera Andes vence el 20 de mayo de 2026."
)

# Ruido típico de show-through: tokens de 1-2 chars y símbolos sueltos.
GARBAGE = (
    "A E E Ed co PRECISA o A A PA : EXT AFA IA ES ES HEE 2d. Y pe TE A AS 3\n"
    "pi > A z q e e e o AA 5 2 E EAS AAA ES ic api: a ] > Es > A ZA > E SR\n"
    "SS A A: 4 RAN TI TEA E RAS O NE EAS"
)


def test_is_word_like():
    assert ocr_service._is_word_like("proyecto")
    assert ocr_service._is_word_like("IA") is False   # < 3 chars
    assert ocr_service._is_word_like("==%") is False  # sin letras
    assert ocr_service._is_word_like("z") is False


def test_good_words_clean_beats_garbage_ratio():
    """El texto limpio tiene mayor densidad de palabras reales por línea."""
    clean_q = ocr_service._line_quality(CLEAN.splitlines()[1])
    garbage_q = ocr_service._line_quality(GARBAGE.splitlines()[0])
    assert clean_q > ocr_service._LINE_MIN_QUALITY
    assert garbage_q < ocr_service._LINE_MIN_QUALITY


def test_strip_garbage_lines_removes_showthrough():
    mixed = CLEAN + "\n" + GARBAGE
    result = ocr_service.strip_garbage_lines(mixed)
    assert "DocMind IA presenta riesgo" in result
    assert "Minera Andes" in result
    # Ninguna línea de basura debe sobrevivir.
    assert "RAN TI TEA" not in result
    assert "EXT AFA IA" not in result


def test_strip_keeps_short_titles():
    """Títulos y fechas cortas (≤3 tokens) se conservan siempre."""
    text = "5. Plan Q2 2026\n31 de marzo"
    assert ocr_service.strip_garbage_lines(text) == text


def test_strip_removes_short_junk_lines():
    """Ruido corto de show-through (una letra o símbolo suelto) se descarta."""
    text = "Contenido legible de la propuesta comercial vigente\ne.\nmá\nA\n4\n*"
    result = ocr_service.strip_garbage_lines(text)
    assert "Contenido legible" in result
    for junk in ("e.", "má", "A", "4", "*"):
        assert junk not in result.split("\n")


def test_text_quality_ratio_distinguishes_layers():
    """La capa de texto limpia supera el umbral; la basura del escáner no."""
    assert ocr_service._text_quality_ratio(CLEAN) >= ocr_service._DIGITAL_TEXT_MIN_QUALITY
    assert ocr_service._text_quality_ratio(GARBAGE) < ocr_service._DIGITAL_TEXT_MIN_QUALITY


def test_otsu_threshold_in_range():
    from PIL import Image  # import perezoso: Pillow sí está disponible en tests

    img = Image.new("L", (10, 10), color=200)
    thr = ocr_service._otsu_threshold(img)
    assert 0 <= thr <= 255
