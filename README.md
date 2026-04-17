# DocMind IA — Sistema de Gestión Documental Inteligente

<div align="center">

![DocMind IA](https://img.shields.io/badge/DocMind-IA-1D4ED8?style=for-the-badge&logo=brain&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18.3-61DAFB?style=flat-square&logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=flat-square&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-24%2F24%20passing-16A34A?style=flat-square&logo=pytest&logoColor=white)

**Plataforma SaaS de gestión documental con OCR automático, clasificación IA y búsqueda semántica**

[Demo local](#instalación-rápida) · [API Docs](http://localhost:8000/docs) · [Repositorio](https://github.com/dNogueira300/docmind-ia)

</div>

---

## ¿Qué es DocMind IA?

DocMind IA automatiza la gestión documental institucional usando inteligencia artificial. Digitaliza documentos físicos mediante OCR, los clasifica automáticamente por tipo usando NLP, y permite encontrarlos en menos de 3 segundos mediante búsqueda semántica full-text en español.

Desarrollado como proyecto académico para el curso de **Gestión de Servicios en Tecnología de Información** — UNAP 2026. Equipo: **Error 404**.

---

## Características principales

| Característica          | Descripción                                                                                       |
| ----------------------- | ------------------------------------------------------------------------------------------------- |
| **OCR automático**      | pypdf para PDFs digitales · Tesseract para imágenes y PDFs escaneados (español)                   |
| **Clasificación IA**    | Zero-shot NLP con `cross-encoder/nli-MiniLM2-L6-H768` — sin reentrenamiento al agregar categorías |
| **Búsqueda semántica**  | Índice GIN PostgreSQL sobre el texto extraído. Resultados en <3 segundos                          |
| **Multitenancy**        | Organizaciones completamente aisladas con categorías personalizadas                               |
| **Control de roles**    | admin · editor · consultor con 7 permisos diferenciados                                           |
| **Audit log inmutable** | Registro completo de todas las operaciones (solo INSERT, nunca UPDATE/DELETE)                     |
| **Pipeline asíncrono**  | El upload responde en <200ms · OCR + IA corren en background                                      |
| **Mobile-first**        | Responsive con captura de cámara integrada en móvil                                               |
| **Temas claro/oscuro**  | Toggle persistente en localStorage                                                                |
| **Seguridad**           | JWT + bcrypt + rate limiting + headers HTTP + CORS dinámico                                       |

---

## Stack tecnológico

```
Backend          │  Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic · slowapi
Frontend         │  React 18 · Tailwind CSS 3 · Axios · React Router 6 · Vite 5
Base de datos    │  PostgreSQL 15 (full-text search en español con índice GIN)
Almacenamiento   │  MinIO (S3-compatible, self-hosted)
OCR              │  pypdf 5.4 · Tesseract OCR (lang=spa)
IA / NLP         │  HuggingFace Transformers · cross-encoder/nli-MiniLM2-L6-H768
Autenticación    │  JWT (python-jose) · bcrypt (12 rondas)
DevOps           │  Docker · docker-compose · GitHub Actions (pendiente)
```

---

## Instalación rápida

### Prerrequisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo
- [Git](https://git-scm.com/) instalado

### 1. Clonar el repositorio

```bash
git clone https://github.com/dNogueira300/docmind-ia.git
cd docmind-ia
```

### 2. Configurar variables de entorno

```bash
# Copiar la plantilla de variables
cp backend/.env.production.example .env

# Editar .env con tus valores (los valores por defecto funcionan para desarrollo local)
```

Variables mínimas requeridas en `.env`:

```env
DATABASE_URL=postgresql://docmind_user:docmind_pass_2026@db:5432/docmind_db
DATABASE_URL_LOCAL=postgresql://docmind_user:docmind_pass_2026@localhost:5433/docmind_db
SECRET_KEY=cambia-esto-por-una-clave-segura-de-64-chars-hex
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=docmind_minio
MINIO_SECRET_KEY=docmind_minio_2026
RUNNING_IN_DOCKER=true
ENVIRONMENT=development
ALLOWED_ORIGINS=["*"]
```

### 3. Configurar el archivo hosts (Windows)

```powershell
# Abrir PowerShell como Administrador
Add-Content -Path "C:\Windows\System32\drivers\etc\hosts" -Value "127.0.0.1 minio"
```

> En Linux/macOS: `echo "127.0.0.1 minio" | sudo tee -a /etc/hosts`

### 4. Levantar el stack

```bash
docker compose up -d
```

Esto inicia 4 contenedores: PostgreSQL, MinIO, Backend FastAPI y Frontend React.

### 5. Crear el usuario administrador

```bash
docker compose exec backend python scripts/create_admin.py admin@docmind.com Admin123!
```

### 6. Acceder al sistema

| Servicio          | URL                        | Credenciales                       |
| ----------------- | -------------------------- | ---------------------------------- |
| **Frontend**      | http://localhost:5173      | admin@docmind.com / Admin123!      |
| **Backend API**   | http://localhost:8000      | —                                  |
| **Swagger UI**    | http://localhost:8000/docs | —                                  |
| **MinIO Consola** | http://localhost:9001      | docmind_minio / docmind_minio_2026 |

---

## Estructura del proyecto

```
docmind-ia/
├── backend/
│   ├── app/
│   │   ├── api/              # Endpoints: auth, users, categories, documents, audit-log
│   │   ├── models/           # Modelos SQLAlchemy: 5 tablas, 3 ENUMs
│   │   ├── schemas/          # Schemas Pydantic v2
│   │   ├── services/         # OCR, NLP, pipeline, MinIO, auditoría
│   │   └── core/             # Config, JWT, deps, rate limiter
│   ├── tests/                # 24 tests automatizados
│   ├── scripts/              # create_admin.py, create_test_documents.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/       # UI/, Layout/, Document/
│   │   ├── context/          # AuthContext, ThemeContext, ToastContext
│   │   ├── pages/            # Login, Dashboard, Documents, Search, Categories, Users, Audit
│   │   └── services/api/     # auth, documents, categories, users, audit
│   ├── package.json
│   └── Dockerfile
├── db/
│   └── migrations/
│       └── 001_initial_schema.sql
├── .claude/
│   ├── CLAUDE.md             # Contexto del proyecto para Claude Code
│   └── skills/               # Skills personalizadas del equipo
├── docker-compose.yml
└── .env                      # No commitear (ver .env.production.example)
```

---

## Pipeline de documentos

```
Usuario sube archivo
        │
        ▼
┌─────────────────┐
│   Validación    │  Magic bytes + extensión + Content-Type + tamaño (máx 20MB)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Almacenamiento │  MinIO S3-compatible → stored_path en BD → status: pending
└────────┬────────┘
         │ BackgroundTask (asíncrono)
         ▼
┌─────────────────┐
│   OCR           │  pypdf si PDF digital (>50 chars) · Tesseract si imagen/escaneado
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Clasificación  │  Zero-shot NLP · candidate_labels desde BD de la organización
│  NLP            │  Modelo: cross-encoder/nli-MiniLM2-L6-H768 (~85 MB)
└────────┬────────┘
         │
         ├── score ≥ 0.70 ──▶  status: classified  (automático)
         └── score < 0.70 ──▶  status: review       (revisión humana)
```

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

### Autenticación

```http
POST /auth/login          # Form-data: username, password → JWT (8h)
GET  /auth/me             # Usuario autenticado actual
POST /auth/logout         # Logout (token stateless)
```

### Documentos

```http
POST /documents/upload              # Sube PDF/JPG/PNG — inicia pipeline IA
GET  /documents/                    # Lista con filtros: status, category_id, skip, limit
GET  /documents/search?q=texto      # Búsqueda semántica full-text
GET  /documents/{id}                # Detalle completo
GET  /documents/{id}/download-url   # URL firmada MinIO (1h de validez)
PUT  /documents/{id}/category       # Reclasificación manual
DELETE /documents/{id}              # Solo admin
```

### Administración (solo admin)

```http
GET|POST        /categories/           # Listar y crear categorías
PUT|DELETE      /categories/{id}       # Editar y eliminar
GET|POST        /users/                # Listar y crear usuarios
PUT|DELETE      /users/{id}            # Editar y desactivar
GET             /audit-log/            # Log inmutable con filtros y paginación
```

---

## Seguridad

| Medida                 | Implementación                                              |
| ---------------------- | ----------------------------------------------------------- |
| Rate limiting en login | 10 intentos/minuto por IP (slowapi)                         |
| Autenticación JWT      | python-jose · expiración 8h · HS256                         |
| Hash de contraseñas    | bcrypt · 12 rondas mínimo                                   |
| Control de roles       | `require_role()` factory en cada endpoint                   |
| Multitenancy           | `organization_id` verificado en cada query                  |
| Validación de archivos | Magic bytes + extensión + Content-Type + 20MB máx           |
| Headers HTTP           | X-Content-Type-Options · X-Frame-Options · X-XSS-Protection |
| CORS dinámico          | `ALLOWED_ORIGINS` configurable por variable de entorno      |
| Docs en producción     | `/docs` deshabilitado con `ENVIRONMENT=production`          |
| Audit log inmutable    | Solo INSERT — nunca UPDATE ni DELETE                        |

---

## Tests

```bash
# Correr todos los tests
docker compose exec backend pytest tests/ -v

# Resultado esperado
# 24 passed — auth(6) · categories(6) · pipeline(7) · users(5)
```

---

## Hitos del proyecto

| Hito                                      | Semanas | Estado         | Entregable                                          |
| ----------------------------------------- | ------- | -------------- | --------------------------------------------------- |
| **Hito 1** — Planificación y Arquitectura | 1–3     | ✅ Completado  | Diagramas PlantUML · Script BD · Propuesta aprobada |
| **Hito 2** — Infraestructura y Backend    | 4–6     | ✅ Completado  | API REST operativa · PostgreSQL · MinIO · Docker    |
| **Hito 3** — Núcleo de IA (OCR + NLP)     | 7–9     | ✅ Completado  | Pipeline OCR + clasificación · Búsqueda semántica   |
| **Hito 4** — Frontend e Integración       | 10–12   | ✅ Completado  | SPA React completa · 8 páginas · Control de roles   |
| **Hito 5** — Seguridad y Cierre           | 12–14   | 🔄 En progreso | Hardening · Despliegue Railway · Documentación      |

---

## Equipo — Error 404

| Integrante                        | Rol                  | Responsabilidades                                   |
| --------------------------------- | -------------------- | --------------------------------------------------- |
| Alva Rengifo, Anny Celeste        | Coordinadora General | Planificación · Gestión del proyecto · Comunicación |
| Nogueira Del Aguila, Elias Daniel | Backend Developer    | API REST · Docker · Arquitectura                    |
| Zumaeta Zegarra, Walter Armando   | Backend Developer    | Integración MinIO · Pipeline · Tests                |
| Cabanillas Rondona, Angie Dayana  | Frontend Developer   | React.js · UI/UX · Responsive                       |
| Romero Rosario, Niquelson Freddy  | Especialista IA      | Modelo NLP · OCR · Zero-shot classification         |
| Chasnamote Navarro, Dan Willy     | QA / Base de Datos   | PostgreSQL · Tests · Documentación técnica          |

---

## Comandos útiles

```bash
# Levantar el stack completo
docker compose up -d

# Ver logs del backend en tiempo real
docker compose logs backend -f

# Correr tests
docker compose exec backend pytest tests/ -v

# Conectar a la BD
docker compose exec db psql -U docmind_user -d docmind_db

# Ver estado de los servicios
docker compose ps

# Detener todo
docker compose down
```

---

## Licencia

Proyecto académico — Universidad Nacional de la Amazonía Peruana (UNAP)  
Curso: Gestión de Servicios en Tecnología de Información · 2026-I  
Docente: Ing. Carlos González Aspajo Mtr.

---

<div align="center">
  <sub>Desarrollado con ❤️ en Iquitos, Perú por el equipo Error 404 — UNAP 2026</sub>
</div>
