# RAILWAY DEPLOY CHECKLIST — DocMind IA

Guía operativa para desplegar DocMind IA en Railway. **Todo lo de este documento se
ejecuta manualmente en el dashboard de Railway** — el código ya quedó preparado en la
rama `feat/railway-deploy-prep`.

> Regla de oro: **nunca** pegues secretos reales en el repo. Solo se cargan como
> Variables en el dashboard de Railway.

---

## 1. Servicios a crear (un solo proyecto Railway)

| # | Servicio     | Origen                                  | Notas |
|---|--------------|-----------------------------------------|-------|
| 1 | **Postgres** | Plugin managed de Railway (`+ New → Database → PostgreSQL`) | Genera `DATABASE_URL` automáticamente. NO se usa `db/migrations/`. |
| 2 | **MinIO**    | Docker image `minio/minio:latest`        | Requiere **Volume** persistente montado en `/data`. Habilitar **public networking** (para URLs firmadas) además del dominio privado. |
| 3 | **backend**  | Este repo, root `backend/`, su `Dockerfile` | Configurar **Pre-Deploy Command** (ver §4). |
| 4 | **frontend** | Este repo, root `frontend/`, su `Dockerfile` | `VITE_API_URL` se inyecta en **build** (ARG). |

### Orden recomendado de creación
Postgres → MinIO → backend → frontend (para poder referenciar variables encadenadas).

### Config de cada servicio
- **MinIO**: Start Command override (en Settings → Deploy): `server /data --console-address ":9001"`.
  Exponer el puerto `9000` como dominio público. Crear el bucket `docmind-docs` una vez
  arrancado (consola web de MinIO en `:9001`, o el backend lo crea solo al iniciar si tiene permisos).
- **backend / frontend**: Railway detecta el `Dockerfile` automáticamente. No definir Start
  Command (los `CMD` ya expanden `${PORT}` en runtime).

---

## 2. Variables de entorno — servicio **backend**

| Variable | Valor (en Railway) | De dónde sale |
|----------|--------------------|---------------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Lo genera el plugin Postgres. Ver nota de Pre-Deploy en §4. |
| `RUNNING_IN_DOCKER` | `true` | Fuerza a `config.py` a usar `DATABASE_URL` (no la local). |
| `SECRET_KEY` | *(64 hex)* | Generar: `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `ALGORITHM` | `HS256` | Opcional (default ya es HS256). |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Opcional (default 480 = 8 h). |
| `MINIO_ENDPOINT` | `${{MinIO.RAILWAY_PRIVATE_DOMAIN}}:9000` | Endpoint **interno** (red privada) para subir/leer/borrar. |
| `MINIO_PUBLIC_ENDPOINT` | `<dominio-público-minio>` (host sin `https://`) | Endpoint **público** solo para firmar URLs de descarga que abre el browser. |
| `MINIO_ACCESS_KEY` | *(root user de MinIO)* | Igual a `MINIO_ROOT_USER` del servicio MinIO. |
| `MINIO_SECRET_KEY` | *(root password de MinIO)* | Igual a `MINIO_ROOT_PASSWORD` del servicio MinIO. |
| `MINIO_BUCKET` | `docmind-docs` | Nombre del bucket. |
| `MINIO_SECURE` | `false` | Endpoint interno sin TLS (red privada). |
| `MINIO_PUBLIC_SECURE` | `true` | Endpoint público vía HTTPS de Railway. |
| `ALLOWED_ORIGINS` | `["https://<dominio-frontend>"]` | Lista JSON. Limitar al dominio del frontend. |
| `ENVIRONMENT` | `production` | Desactiva `/docs`, `/redoc`, `/openapi.json`. |
| `SUPER_ADMIN_EMAIL` | *(email admin)* | Usuario super admin creado al primer arranque. |
| `SUPER_ADMIN_PASSWORD` | *(contraseña fuerte)* | **Obligatorio** en producción (sin él no se crea el admin). |
| `GEMINI_API_KEY` | *(API key)* | https://aistudio.google.com/apikey — resumen + chatbot. |

## 3. Variables de entorno — servicio **MinIO**

| Variable | Valor | Nota |
|----------|-------|------|
| `MINIO_ROOT_USER` | *(usuario)* | Debe coincidir con `MINIO_ACCESS_KEY` del backend. |
| `MINIO_ROOT_PASSWORD` | *(contraseña)* | Debe coincidir con `MINIO_SECRET_KEY` del backend. |

## Variables de entorno — servicio **frontend**

| Variable | Valor | Nota |
|----------|-------|------|
| `VITE_API_URL` | `https://<dominio-backend>` | **Build-time** (ARG en el Dockerfile). Si Railway no la pasa al build, declararla como Build Arg / Variable antes de desplegar. |

> `VITE_BACKEND_URL` (en `vite.config.js`) solo aplica al proxy del **dev server** local;
> en el build de producción no se usa. No hace falta en Railway.

## Variables — servicio **Postgres**
Las gestiona Railway automáticamente. No tocar.

---

## 4. Pre-Deploy Command (servicio backend)

Configurar en **backend → Settings → Deploy → Pre-Deploy Command**:

```bash
alembic upgrade head
```

Esto crea/actualiza todo el esquema desde cero. La migración inicial
(`16f58f46fb1c`) ahora es **self-contained** (crea tablas, tipos enum, índices y la
org demo), por lo que corre limpio contra el Postgres vacío de Railway.

> ⚠️ **Importante (red privada en pre-deploy):** si el pre-deploy NO tiene acceso a la
> red privada de Railway, `alembic` no podrá resolver `*.railway.internal` y fallará al
> conectar a Postgres. En ese caso, apunta la migración a la URL pública de Postgres:
> usa `${{Postgres.DATABASE_PUBLIC_URL}}` para el pre-deploy (o ejecútala una vez en
> local con `railway run alembic upgrade head`). Ver "Dudas a confirmar" en el reporte.

---

## 5. Orden de despliegue

1. Crear Postgres y MinIO; esperar a que estén `Active`.
2. En MinIO: crear el bucket `docmind-docs`.
3. Crear el servicio backend con todas sus variables + Pre-Deploy Command.
   Verificar en logs que `alembic upgrade head` corre sin error y que `/health`
   responde 200.
4. Tomar el dominio público del backend → setear `VITE_API_URL` en el frontend.
5. Crear el frontend; tras el build, setear `ALLOWED_ORIGINS` del backend con el
   dominio del frontend y redesplegar el backend.
6. Login con `SUPER_ADMIN_EMAIL` / `SUPER_ADMIN_PASSWORD` y validar subida + descarga
   de un documento (prueba la firma de URL pública de MinIO).

---

## 6. Healthcheck

- Path: `/health` (GET, sin auth). Responde 200 sin depender de Postgres/MinIO.
- Railway lo usa para enrutar tráfico tras el deploy.
