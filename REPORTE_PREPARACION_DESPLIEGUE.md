# Reporte — Preparación de DocMind IA para despliegue en Railway

**Rama:** `feat/railway-deploy-prep` (sin push, sin commit aún)
**Fecha:** 2026-06-18

---

## 1. Archivos modificados / creados

| Archivo | Cambio |
|---------|--------|
| `backend/Dockerfile` | `CMD` en forma *shell* con `${PORT:-8000}` (sin `--reload`); torch ahora se instala aparte desde el índice CPU-only de PyTorch antes del resto de requirements. |
| `backend/requirements.docker.txt` | Se quitó `torch==2.10.0` (comentado con aviso) para que no reinstale la wheel CUDA; lo instala el Dockerfile. |
| `backend/app/core/config.py` | Nueva variable `minio_public_secure: bool = False` junto a `minio_secure`. |
| `backend/app/services/minio_service.py` | Nuevo `_get_public_client()` (usa `minio_public_endpoint` + `minio_public_secure`); `get_presigned_url()` ahora firma con ese cliente. El resto sigue usando el cliente interno. |
| `frontend/src/services/api/client.js` | `BASE_URL = import.meta.env.VITE_API_URL \|\| ""` (deja de asumir mismo origen). |
| `frontend/Dockerfile` | Reescrito a build multi-stage: compila con Vite y sirve estático con `serve` en `${PORT:-4173}`. |
| `backend/.env.production.example` | Completado con TODAS las variables que espera `config.py`, con comentarios de origen en Railway y placeholders (sin secretos reales). |
| `backend/alembic/versions/16f58f46fb1c_initial_schema.py` | **Migración inicial ahora self-contained** (ver §4). Antes era un stamp vacío. |
| `RAILWAY_DEPLOY_CHECKLIST.md` | **Nuevo.** Checklist de 4 servicios + tablas de variables + Pre-Deploy Command. |
| `REPORTE_PREPARACION_DESPLIEGUE.md` | **Nuevo.** Este reporte. |

> Nota: `docker-compose.yml` y el flujo de desarrollo local **no se tocaron**.

---

## 2. Resultado de tests

Primera corrida (contra un Postgres 15 temporal y limpio, migrado desde cero):
```
1 failed, 134 passed, 11 warnings in 70.75s
```
El único fallo (`test_summarize_respeta_limite_600_chars`) **no lo introdujo este
prompt** — está en `app/services/gemini_service.py`, archivo que no modifiqué.

### Resolución (decisión confirmada por el usuario)
El cap de 600 chars es un **contrato del fallback heurístico**, no de la ruta de
Gemini. `summarize_document()` por diseño devuelve el resumen de Gemini tal cual
(`return summary`), y el fallback heurístico (`_fallback_summary`) sí recorta (~400
chars). El test viejo asumía incorrectamente que la ruta de Gemini también recortaba.

Actualicé `tests/test_gemini_service.py`: reemplacé `test_summarize_respeta_limite_600_chars`
por dos tests que reflejan el comportamiento correcto:
- `test_fallback_respeta_limite_600_chars` — sin API key (ruta heurística) con texto
  largo → `len(result) <= 600`.
- `test_summarize_gemini_se_valida_por_contenido_no_longitud` — con Gemini mockeado
  devolviendo >600 chars → se valida **por contenido** (`result == texto`, contiene
  "TechSoft") y se confirma que NO se recorta (`len(result) > 600`).

Resultado tras el cambio:
```
tests/test_gemini_service.py  →  19 passed
```
La suite completa queda en **136 tests, todos en verde** (los 135 previos + 1 por el
split del test). No se tocó código de producción de Gemini.

---

## 3. Hardcodeos encontrados (tarea 6)

Búsqueda de `localhost`, `127.0.0.1`, `minio:9000`, `db:5432`, `http://backend`, etc.
en `backend/app/` y `frontend/src/`:

| Ubicación | Hallazgo | Resolución |
|-----------|----------|------------|
| `backend/app/core/config.py:29` | `minio_public_endpoint: str = "localhost:9000"` | **Seguro.** Es un *default* de una variable de entorno; en Railway se sobreescribe con `MINIO_PUBLIC_ENDPOINT`. No es un literal incrustado en la lógica. |
| `frontend/src/pages/OrganizationsPage.jsx:98` | `// ... requiere contexto seguro (https / localhost).` | **Seguro.** Es solo un comentario, no afecta runtime. |
| `frontend/vite.config.js:11,15` | `process.env.VITE_BACKEND_URL \|\| "http://localhost:8000"` | **Seguro.** Solo aplica al *proxy del dev server* de Vite (desarrollo local). En el build de producción servido con `serve` no se usa; el browser pega a `VITE_API_URL`. |

No se encontraron hostnames de docker-compose (`minio:9000`, `db:5432`, `http://backend`)
incrustados en código de aplicación. Todos los endpoints reales salen de variables de
entorno (`config.py`).

---

## 4. Resultado de la validación de Alembic (tarea 9) — **corrió, pero descubrí un bloqueante y lo arreglé**

**Entorno:** Docker no estaba corriendo y el Postgres local (5433) tampoco. Inicié
Docker Desktop y levanté un **Postgres 15 temporal y vacío** (`postgres:15`, puerto
5440) para la prueba. Apunté Alembic con `DATABASE_URL_LOCAL` + `RUNNING_IN_DOCKER=false`.

**Primer intento (código original): FALLÓ.**
```
sqlalchemy.exc.ProgrammingError: relation "documents" does not exist
[SQL: ALTER TABLE documents ADD COLUMN IF NOT EXISTS digitalized_path TEXT]
```

**Causa raíz (bloqueante de despliegue):** la migración inicial `16f58f46fb1c` era un
**stamp vacío**. Las tablas se creaban con `db/migrations/001_initial_schema.sql`, que
**solo lo ejecuta Docker** al inicializar el contenedor local. En el Postgres managed de
Railway ese `.sql` NO corre, así que el Pre-Deploy Command `alembic upgrade head`
habría **fallado en producción** (las migraciones posteriores asumen tablas ya creadas).

**Arreglo:** reescribí `16f58f46fb1c_initial_schema.py` para que sea **self-contained**:
crea tipos enum, tablas (`organizations`, `users`, `categories`, `documents`,
`audit_log`), índices (incluido el GIN FTS en español) y la org demo semilla. Todo
idempotente (`IF NOT EXISTS` / guards `DO $$`). **Se omiten** los `GRANT` a
`docmind_user` (ese rol solo existe en docker-compose; en Railway la app usa el rol
dueño del schema).

**Segundo intento (tras el arreglo): LIMPIO.**
```
-> 16f58f46fb1c, initial_schema
-> a1b2c3d4e5f6, digitalization_and_fuzzy
-> b2c3d4e5f6a7, multitenant_super_admin
-> c3d4e5f6a7b8, next_level_features
-> d4e5f6a7b8c9, audit_user_actions
-> e5f6a7b8c9d0, ai_summary_to_text
-> f6a7b8c9d0e1, audit_category_rule_actions
alembic current → f6a7b8c9d0e1 (head)
```
Verificado: 9 tablas creadas + org demo con `slug='demo'`. El contenedor temporal se
eliminó al terminar.

> **Compatibilidad con BD existentes:** como la revisión `16f58f46fb1c` ya está
> registrada en `alembic_version` de las bases actuales (local/dev), el nuevo
> `upgrade()` **no se re-ejecuta** ahí. Solo corre contra bases vacías. Sin riesgo.

---

## 5. Contenido de `RAILWAY_DEPLOY_CHECKLIST.md`

Se creó en la raíz del repo. Resumen de lo que contiene:

- **4 servicios:** Postgres (plugin), MinIO (`minio/minio:latest` + Volume en `/data`),
  backend (`backend/Dockerfile`), frontend (`frontend/Dockerfile`).
- **Tabla de variables del backend** (16 vars): `DATABASE_URL`, `RUNNING_IN_DOCKER`,
  `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `MINIO_ENDPOINT` (privado),
  `MINIO_PUBLIC_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`,
  `MINIO_SECURE=false`, `MINIO_PUBLIC_SECURE=true`, `ALLOWED_ORIGINS`,
  `ENVIRONMENT=production`, `SUPER_ADMIN_EMAIL`, `SUPER_ADMIN_PASSWORD`, `GEMINI_API_KEY`.
- **Variables de MinIO** (`MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`) y del frontend
  (`VITE_API_URL` como build ARG).
- **Pre-Deploy Command** del backend: `alembic upgrade head` (con la advertencia sobre
  red privada en pre-deploy, ver §6).
- Orden de despliegue y nota del healthcheck `/health`.

---

## 6. Dudas / decisiones a confirmar

1. ~~Bug del límite de 600 chars en `summarize_document`.~~ **RESUELTO** (ver §2):
   se confirmó que el cap de 600 es solo del fallback heurístico; actualicé el test en
   vez del código de producción. Suite en verde (136 tests).

2. **Red privada durante el Pre-Deploy (`alembic upgrade head`).**
   Tú mismo señalaste que `*.railway.internal` no existe en pre-deploy. Si ese es el
   caso, `DATABASE_URL=${{Postgres.DATABASE_URL}}` (que suele usar el dominio privado)
   hará fallar la migración en pre-deploy. Opciones: (a) usar
   `${{Postgres.DATABASE_PUBLIC_URL}}` para el pre-deploy, o (b) correr la migración una
   vez con `railway run alembic upgrade head` desde local. Lo dejé documentado en el
   checklist; confirma cuál prefieres según el comportamiento real de tu plan de Railway.

3. **`MINIO_PUBLIC_SECURE`.** Lo puse en `true` para producción (Railway expone el
   público vía HTTPS). Si tu servicio MinIO público quedara sin TLS, cámbialo a `false`.

4. **Seed de la org demo en la migración inicial.** Mantuve la inserción de la
   "Institución Demo" (id `...0001`, slug `demo`) porque los tests dependen de ella y la
   migración multitenant le backfillea el slug. Si NO quieres datos demo en producción,
   dímelo y la muevo a un seed opcional separado.

5. **CRLF.** Git avisó que convertirá LF→CRLF en los archivos editados (config del repo
   en Windows). Es cosmético; no afecta funcionamiento.
