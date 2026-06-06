FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema:
#   - tesseract + idioma español → OCR
#   - poppler-utils              → pdf2image (rasteriza PDFs escaneados de N páginas)
#   - libpq-dev + gcc            → psycopg2-binary
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.docker.txt .
RUN pip install --no-cache-dir --timeout=300 -r requirements.docker.txt

# Descargar modelo spaCy español para NER de alertas
# es_core_news_lg (~560 MB): NER con dependencias + vectores
RUN python -m spacy download es_core_news_lg

# El resumen ahora usa Google Gemini API (google-genai, ya instalado vía requirements).
# No se necesita modelo local de ~850 MB — la imagen es ~850 MB más liviana.

# Copiar código fuente
COPY . .

# Exponer puerto
EXPOSE 8000

# Comando de arranque (modo desarrollo con hot-reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]