# Plan de Desarrollo Detallado

## Sistema de Gestión Documental Inteligente con IA — *DocMind IA*

**Universidad Nacional de la Amazonía Peruana**
Facultad de Ingeniería de Sistemas e Informática
Curso: Gestión de Servicios en Tecnología de Información
Docente: Ing. Carlos González Aspajo Mtr.
Fecha de inicio: 23/03/2026 | Fecha de fin: 15/06/2026

---

## Contexto del Proyecto

### ¿Qué es DocMind IA?

DocMind IA es una plataforma SaaS de gestión documental inteligente diseñada para ser implementada en **cualquier tipo de institución u organización** — pública o privada — que genere, reciba o administre documentos físicos o digitales. Esto incluye, sin limitarse a, municipalidades, hospitales, universidades, estudios jurídicos, empresas comerciales, ONGs y entidades gubernamentales.

El sistema combina tres tecnologías clave en un solo producto:

| Tecnología                                    | Función                                                                                        |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **OCR** (Tesseract / Google Vision API)       | Convierte documentos físicos escaneados en texto digital indexable                             |
| **NLP con IA** (HuggingFace / BETO)           | Clasifica automáticamente cada documento según categorías definidas por la propia organización |
| **Búsqueda Semántica** (PostgreSQL full-text) | Permite localizar documentos por contenido, fecha, tipo o palabras clave en segundos           |

### El Problema que Resuelve

En instituciones peruanas — y latinoamericanas en general — la gestión documental sigue siendo mayoritariamente manual. Los efectos son concretos y medibles:

- Los trabajadores invierten entre **30 y 90 minutos diarios** buscando documentos físicos.
- El **30% de la jornada laboral** se pierde en búsqueda de información (IDC).
- Se producen pérdidas frecuentes de expedientes físicos sin posibilidad de trazabilidad.
- No existe registro de quién accedió a un documento, cuándo, ni qué hizo con él.

### La Solución Propuesta

DocMind IA digitaliza, clasifica y centraliza la documentación institucional, con el objetivo de **reducir en al menos un 70% el tiempo de búsqueda documental** respecto al proceso manual actual.

### Principio Clave: Categorías Personalizables por Organización

Un aspecto fundamental del diseño del sistema es que **cada institución o empresa tiene la libertad de crear, editar y gestionar sus propias categorías documentales**. No existe una taxonomía fija impuesta por el sistema. Una municipalidad podrá definir categorías como "Resoluciones", "Actas", "Expedientes de licencias"; un estudio jurídico podrá usar "Contratos", "Poderes notariales", "Demandas"; una clínica podrá organizar su documentación en "Historias clínicas", "Informes médicos", "Facturas". El motor de IA aprende y clasifica en función de las categorías que la propia organización define, haciendo al sistema verdaderamente adaptable a cualquier contexto institucional.

### Equipo del Proyecto

| Rol                     | Integrante                       | Responsabilidad Principal                           |
| ----------------------- | -------------------------------- | --------------------------------------------------- |
| Coordinadora General    | Anny Celeste Alva Rengifo        | Planificación, gestión, comunicación con el docente |
| Backend Developer       | Elias Daniel Nogueira del Aguila | API REST, integración OCR e IA                      |
| Backend Developer       | Walter Armando Zumaeta Zegarra   | API REST, lógica de clasificación, Docker           |
| Frontend Developer      | Angie Dayana Cabanillas Rondona  | Interfaz React.js, diseño responsive                |
| Especialista IA / Datos | Niquelson Freddy Romero Rosario  | Modelo NLP, entrenador del clasificador             |
| QA / Base de Datos      | Dan Willy Chasnamote Navarro     | PostgreSQL, pruebas funcionales, documentación      |

### Stack Tecnológico

```
Backend:     Python 3.11 + FastAPI
Frontend:    React.js + Tailwind CSS
Base Datos:  PostgreSQL 15 (full-text search)
OCR:         Tesseract OCR / Google Cloud Vision API
IA / NLP:    HuggingFace Transformers — modelo BETO (español)
Storage:     MinIO / Sistema de archivos local
Auth:        JWT + bcrypt
DevOps:      Docker + Railway / Render
VCS:         Git + GitHub
```

---

## Plan de Desarrollo por Hitos

---

## Hito 1 — Planificación y Diseño de Arquitectura

**Semanas:** 1 a 3 (23/03/2026 – 12/04/2026)
**Responsables principales:** Coordinadora General + Especialista IA + QA / BD

### Objetivo

Establecer las bases técnicas, funcionales y organizativas del proyecto antes de escribir una sola línea de código. Un diseño sólido en esta etapa evita retrabajo costoso en etapas posteriores.

### Entregables

- Propuesta aprobada por el docente
- Diagrama de arquitectura hardware-software
- Esquema de base de datos (entidad-relación)
- Repositorio GitHub inicializado con estructura de carpetas
- Documento de definición de categorías personalizables

---

### Paso 1.1 — Validación y refinamiento del alcance

Reunión del equipo completo para revisar el acta de constitución y acordar los límites exactos del sistema.

**Acciones:**

- Confirmar que el prototipo cubrirá los formatos JPG, PNG y PDF escaneado.
- Acordar que el sistema soportará hasta 10 categorías documentales configurables por organización (número máximo para el prototipo; en producción puede ser ilimitado).
- Definir los tres roles de usuario del sistema: `administrador`, `editor` y `consultor`.
- Documentar explícitamente qué queda **fuera del alcance** (firma digital, integración ERP, app móvil nativa, multiidioma).

---

### Paso 1.2 — Diseño de la arquitectura del sistema

Producir el diagrama de arquitectura que muestre cómo se comunican todos los componentes del sistema.

**Diagrama a construir:**

```
[Cliente (navegador)] 
        ↓ HTTPS
[Frontend React.js]
        ↓ REST API (JSON)
[Backend FastAPI]
    ├── Módulo OCR (Tesseract / Google Vision)
    ├── Motor NLP / Clasificador IA (HuggingFace BETO)
    ├── Motor de Búsqueda Semántica
    └── Módulo de Auditoría y Roles
        ↓
[PostgreSQL 15]     [MinIO / Almacenamiento de archivos]
```

**Acciones:**

- Usar una herramienta como draw.io o Lucidchart para el diagrama.
- Documentar el flujo completo de un documento: desde que un usuario lo sube hasta que queda clasificado, indexado y disponible para búsqueda.
- Definir los endpoints principales de la API (listado preliminar).

---

### Paso 1.3 — Diseño del esquema de base de datos

Diseñar el modelo relacional que sostendrá toda la lógica del sistema.

**Tablas principales:**

```sql
-- Organizaciones (multitenancy básico)
organizations (id, name, created_at)

-- Categorías personalizables por organización
categories (id, organization_id, name, description, color, created_at)

-- Usuarios del sistema
users (id, organization_id, name, email, password_hash, role, active, created_at)
-- role: 'admin' | 'editor' | 'consultor'

-- Documentos
documents (
  id, organization_id, category_id, uploaded_by,
  original_filename, stored_path, file_type, file_size_kb,
  ocr_text, ai_confidence_score, status,
  created_at, updated_at
)
-- status: 'pending' | 'processing' | 'classified' | 'error'

-- Auditoría (log inmutable de operaciones)
audit_log (
  id, document_id, user_id, action,
  detail_json, ip_address, timestamp
)
-- action: 'upload' | 'view' | 'download' | 'reclassify' | 'delete'
```

**Acciones:**

- Diagramar el modelo entidad-relación (ER).
- Definir índices de búsqueda full-text sobre la columna `ocr_text`.
- Documentar las reglas de negocio de integridad referencial.

---

### Paso 1.4 — Diseño del sistema de categorías personalizables

Definir cómo funcionará la gestión de categorías, dado que es una característica central del sistema.

**Reglas de diseño:**

- Cada organización gestiona sus propias categorías de forma independiente. No hay categorías "globales" del sistema.
- El administrador de la organización puede crear, renombrar, cambiar el color y eliminar categorías desde el panel web.
- Al eliminar una categoría, los documentos asociados no se eliminan: pasan al estado "Sin categoría" para ser reclasificados manualmente o por IA.
- El motor de IA aprende de las categorías activas de cada organización. Si se añaden categorías nuevas, el administrador puede lanzar una reclasificación en lote.
- Para el prototipo, se definirán hasta 10 categorías por organización. El sistema no impone nombres; la organización es completamente libre de nombrarlas como necesite.

**Entregable:** Documento de diseño de la funcionalidad de categorías, con mockup del panel de gestión de categorías.

---

### Paso 1.5 — Inicialización del repositorio y estructura del proyecto

Preparar el entorno de colaboración del equipo desde el primer día.

**Estructura de carpetas en GitHub:**

```
docmind-ia/
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints FastAPI
│   │   ├── models/       # Modelos SQLAlchemy
│   │   ├── services/     # Lógica de negocio (OCR, IA, auditoría)
│   │   └── core/         # Config, auth, seguridad
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/     # Llamadas a la API
│   └── package.json
├── ml/
│   ├── training/         # Scripts de entrenamiento del clasificador
│   └── models/           # Modelos exportados
├── db/
│   └── migrations/       # Scripts SQL de inicialización
├── docker-compose.yml
└── README.md
```

**Acciones:**

- Crear el repositorio en GitHub y definir la rama `main` como protegida.
- Crear ramas por módulo: `feature/backend`, `feature/frontend`, `feature/ai`.
- Definir convención de commits (ej. Conventional Commits).
- Redactar el README inicial con descripción del proyecto.

---

## Hito 2 — Infraestructura Base y Backend

**Semanas:** 4 a 6 (13/04/2026 – 03/05/2026)
**Responsables principales:** Backend Developers + QA / BD

### Objetivo

Tener el entorno de desarrollo completamente operativo, la base de datos configurada y una API funcional que acepte peticiones básicas con autenticación. Este hito es el cimiento sobre el que se construirán los módulos de IA.

### Entregables

- Entorno Docker funcional (backend + base de datos en contenedores)
- Base de datos PostgreSQL con esquema completo aplicado
- API base en FastAPI con autenticación JWT operativa
- Endpoints CRUD para: usuarios, categorías y documentos (sin OCR aún)
- Repositorio de archivos configurado (MinIO o sistema local)

---

### Paso 2.1 — Configuración del entorno Docker

Contenedorizar todos los servicios para garantizar consistencia entre los equipos del equipo de desarrollo.

**Acciones:**

- Crear el `docker-compose.yml` con los siguientes servicios:
  - `db`: PostgreSQL 15
  - `backend`: FastAPI con hot-reload
  - `storage`: MinIO (para almacenamiento de archivos)
- Definir el archivo `.env` con variables de entorno (credenciales de BD, claves JWT, configuración de APIs).
- Verificar que `docker compose up` levanta todo el stack sin errores.
- Documentar el proceso de instalación en el README.

---

### Paso 2.2 — Inicialización de la base de datos

Implementar el esquema diseñado en el Hito 1.

**Acciones:**

- Usar Alembic (herramienta de migraciones para SQLAlchemy) para versionar el esquema.
- Ejecutar la migración inicial que crea todas las tablas.
- Insertar datos semilla (seed data) para desarrollo:
  - 1 organización de prueba
  - 5 categorías de ejemplo (personalizables desde el panel)
  - 2 usuarios: un administrador y un editor
- Configurar el índice `tsvector` en PostgreSQL para búsqueda full-text sobre `ocr_text`.

---

### Paso 2.3 — Desarrollo de la API base con FastAPI

Construir el esqueleto de la API con todos los módulos necesarios, incluso si algunos aún no tienen lógica completa.

**Endpoints a implementar en este hito:**

```
AUTH
POST   /auth/login          → Retorna token JWT
POST   /auth/logout

USUARIOS (solo admin)
GET    /users               → Listar usuarios de la organización
POST   /users               → Crear usuario
PUT    /users/{id}          → Editar usuario
DELETE /users/{id}          → Desactivar usuario

CATEGORÍAS (personalizables por organización)
GET    /categories          → Listar categorías de la organización
POST   /categories          → Crear nueva categoría
PUT    /categories/{id}     → Renombrar / editar categoría
DELETE /categories/{id}     → Eliminar categoría (documentos → "sin categoría")

DOCUMENTOS
GET    /documents           → Listar documentos (con filtros)
POST   /documents/upload    → Subir documento (sin OCR aún, solo almacenamiento)
GET    /documents/{id}      → Ver detalle de un documento
DELETE /documents/{id}      → Marcar como eliminado (soft delete)
```

**Acciones:**

- Implementar el middleware de autenticación JWT en cada endpoint protegido.
- Implementar el control de acceso por roles: el `consultor` solo puede leer; el `editor` puede subir y buscar; el `administrador` tiene acceso completo.
- Agregar validación de tipos de archivo en la subida (solo PDF, JPG, PNG).
- Implementar el registro automático en `audit_log` para cada operación sobre documentos.

---

### Paso 2.4 — Configuración del repositorio de archivos

Establecer dónde y cómo se almacenan físicamente los archivos subidos por los usuarios.

**Acciones:**

- Configurar MinIO como servidor de almacenamiento de objetos compatible con S3.
- Definir la estructura de carpetas dentro de MinIO:
  
  ```
  bucket: docmind/
  └── {organization_id}/
      └── {year}/{month}/
          └── {document_id}_{original_filename}
  ```
- Implementar la función de almacenamiento en el servicio de backend.
- Verificar que los archivos subidos son recuperables mediante URL firmada (acceso temporal seguro).

---

### Paso 2.5 — Pruebas de la API con herramientas de testing

Validar que todo lo construido funciona correctamente antes de avanzar.

**Acciones:**

- Probar todos los endpoints con Postman o Insomnia.
- Escribir pruebas unitarias básicas con `pytest` para los endpoints de autenticación y usuarios.
- Verificar que un usuario con rol `consultor` no puede acceder a endpoints de administración.
- Verificar que la auditoría registra correctamente cada operación.

---

## Hito 3 — Desarrollo del Núcleo de IA (OCR y NLP)

**Semanas:** 7 a 9 (04/05/2026 – 24/05/2026)
**Responsables principales:** Especialista IA / Datos + Backend Developers

### Objetivo

Implementar el corazón inteligente del sistema: el módulo OCR que convierte imágenes en texto y el motor de clasificación automática que categoriza cada documento. Estos dos módulos son los que diferencian DocMind IA de un simple gestor de archivos.

### Entregables

- Módulo OCR funcional con precisión mínima del 85%
- Motor de clasificación NLP operativo con soporte para categorías personalizadas
- Endpoint de procesamiento asíncrono integrado en la API
- Pruebas de precisión documentadas

---

### Paso 3.1 — Implementación del módulo OCR

Extraer texto de documentos subidos (imágenes JPG/PNG y PDFs escaneados).

**Acciones:**

- Integrar **Tesseract OCR** como opción principal (open source, sin costo).
- Integrar **Google Cloud Vision API** como alternativa de mayor precisión para documentos complejos.
- Implementar lógica de selección: si el documento es un PDF con texto incrustado (no escaneado), extraer el texto directamente sin OCR (usando PyPDF2); si es una imagen o PDF escaneado, usar OCR.
- Configurar Tesseract con el paquete de idioma español (`spa`).
- Guardar el texto extraído en la columna `ocr_text` de la tabla `documents`.
- Actualizar el campo `status` del documento: `pending` → `processing` → `classified` (o `error`).

**Métrica de éxito:** El módulo debe extraer texto con una precisión mínima del 85% en documentos en español con buena calidad de escaneo.

---

### Paso 3.2 — Implementación del motor de clasificación NLP

Clasificar automáticamente cada documento en una de las categorías definidas por la organización.

**Acciones:**

**3.2.1 — Estrategia del clasificador:**
El clasificador usará el modelo **BETO** (BERT entrenado en español) de HuggingFace como base. Se implementará un pipeline de zero-shot classification o few-shot, lo que permite clasificar en categorías personalizadas sin necesidad de reentrenar el modelo completo.

- Usar el pipeline `zero-shot-classification` de HuggingFace con `candidate_labels` dinámicos.
- Los `candidate_labels` se obtienen en tiempo real desde la base de datos (categorías de la organización).
- Esto garantiza que el clasificador siempre trabaje con las categorías actuales de cada organización, sin necesidad de reentrenar cuando se añaden nuevas categorías.

**Ejemplo de llamada al clasificador:**

```python
from transformers import pipeline

classifier = pipeline("zero-shot-classification", model="cross-encoder/nli-MiniLM2-L6-H768")

# Categorías definidas por ESTA organización específica
org_categories = ["Resoluciones", "Contratos", "Memorándums", "Informes", "Facturas"]

result = classifier(ocr_text[:512], candidate_labels=org_categories)
predicted_category = result["labels"][0]
confidence_score = result["scores"][0]
```

**3.2.2 — Umbral de confianza:**

- Si el score de confianza es ≥ 0.70: clasificar automáticamente.
- Si el score es < 0.70: clasificar en "Requiere revisión manual" y notificar al editor.

**3.2.3 — Reclasificación manual y retroalimentación:**

- El editor puede corregir la clasificación asignada por la IA desde la interfaz.
- Las correcciones se registran en `audit_log` y pueden usarse para fine-tuning futuro.

---

### Paso 3.3 — Pipeline de procesamiento asíncrono

El OCR y la clasificación pueden tomar varios segundos. Deben ejecutarse en segundo plano sin bloquear la respuesta de la API.

**Acciones:**

- Implementar procesamiento asíncrono usando **BackgroundTasks** de FastAPI (para el prototipo) o una cola de tareas con **Celery + Redis** (si el volumen lo requiere).
- Flujo del pipeline:
  1. Usuario sube documento → API lo almacena en MinIO → registra en BD con `status: 'pending'` → retorna respuesta inmediata al usuario.
  2. En segundo plano: extrae texto con OCR → clasifica con NLP → actualiza `status`, `ocr_text`, `category_id` y `ai_confidence_score` en BD.
- El frontend puede hacer polling o usar websockets para mostrar el estado del procesamiento en tiempo real.

---

### Paso 3.4 — Pruebas de precisión del módulo de IA

Documentar la calidad del clasificador antes de integrarlo con el frontend.

**Acciones:**

- Preparar un conjunto de al menos 50 documentos de prueba en español, previamente categorizados manualmente.
- Ejecutar el clasificador sobre los 50 documentos y registrar:
  - Categoría predicha vs. categoría real
  - Score de confianza por documento
- Calcular métricas: precisión (accuracy), y revisar casos de error.
- Documentar los resultados en un reporte de pruebas de IA.
- Si la precisión es menor al esperado, ajustar el umbral de confianza o evaluar un modelo alternativo.

---

## Hito 4 — Desarrollo Frontend e Integración

**Semanas:** 10 a 12 (25/05/2026 – 14/06/2026)
**Responsables principales:** Frontend Developer + Backend Developers

### Objetivo

Construir la interfaz de usuario que conecte a las personas con todo el sistema. El portal debe ser intuitivo, responsive y funcional: desde la subida de un documento hasta su búsqueda y descarga.

### Entregables

- Portal web completo en React.js con todas las vistas funcionales
- Motor de búsqueda semántica integrado en el frontend
- Panel de administración de categorías operativo
- Pruebas de integración frontend-backend completadas

---

### Paso 4.1 — Configuración del proyecto React

**Acciones:**

- Inicializar el proyecto con Vite + React + Tailwind CSS.
- Configurar el cliente HTTP (Axios) con interceptores para inyectar el token JWT en cada petición.
- Configurar React Router para la navegación entre páginas.
- Definir las rutas protegidas según el rol del usuario.

---

### Paso 4.2 — Desarrollo de las vistas principales

**4.2.1 — Autenticación:**

- Pantalla de login con campos email y contraseña.
- Manejo de errores (credenciales inválidas, sesión expirada).
- Redirección al dashboard según el rol del usuario al iniciar sesión.

**4.2.2 — Dashboard principal:**

- Resumen estadístico: total de documentos, documentos procesados hoy, documentos pendientes de revisión.
- Accesos rápidos a las funciones más usadas.
- Diseño diferenciado según el rol (el consultor ve menos opciones que el administrador).

**4.2.3 — Gestor de documentos:**

- Listado de documentos con columnas: nombre, categoría, fecha, estado, usuario que subió.
- Filtros activos: por categoría, por fecha, por tipo de archivo, por estado.
- Botón de subida de documentos (drag & drop o selección de archivo).
- Indicador de procesamiento en tiempo real (estado OCR + clasificación IA).
- Opción para ver, descargar o reclasificar manualmente cada documento.

**4.2.4 — Motor de búsqueda semántica:**

- Barra de búsqueda prominente con búsqueda por palabras clave en el contenido del documento.
- Filtros combinados: categoría + rango de fechas + tipo de documento.
- Resultados ordenados por relevancia con resaltado de términos encontrados.
- Tiempo de respuesta visible: el sistema debe responder en menos de 3 segundos.

**4.2.5 — Panel de administración de categorías (solo administrador):**

- Listar todas las categorías de la organización con nombre, color y cantidad de documentos asociados.
- Formulario para crear nueva categoría: nombre + color + descripción opcional.
- Edición y eliminación de categorías existentes con confirmación de impacto.
- Mensaje de advertencia al eliminar: "X documentos serán marcados como 'Sin categoría'".

**4.2.6 — Gestión de usuarios (solo administrador):**

- Listado de usuarios con nombre, email, rol y estado (activo/inactivo).
- Formulario para crear nuevo usuario con asignación de rol.
- Opción para activar/desactivar usuarios.

**4.2.7 — Panel de auditoría:**

- Tabla con historial de operaciones: usuario, acción, documento afectado, fecha/hora, IP.
- Filtros por usuario, tipo de acción y rango de fechas.
- Exportación del log de auditoría en PDF.

---

### Paso 4.3 — Integración frontend-backend

**Acciones:**

- Conectar cada vista con su endpoint de API correspondiente.
- Implementar manejo global de errores (errores de red, errores 4xx y 5xx de la API).
- Implementar el flujo completo de subida: el usuario sube un archivo → ve el indicador de procesamiento → recibe la notificación de que el documento fue clasificado → puede buscarlo de inmediato.
- Verificar que la búsqueda semántica retorna resultados correctos en menos de 3 segundos.

---

### Paso 4.4 — Pruebas de integración

**Acciones:**

- Ejecutar el flujo completo de extremo a extremo para cada rol de usuario:
  - Administrador: crea categorías → sube documentos → busca → gestiona usuarios → revisa auditoría.
  - Editor: sube documentos → reclasifica un documento → busca → descarga.
  - Consultor: busca documentos → visualiza → intenta acceder a funciones restringidas (debe ser bloqueado).
- Verificar el comportamiento responsive en dispositivos móviles (mínimo 375px de ancho).
- Registrar y corregir todos los bugs encontrados.

---

## Hito 5 — Seguridad, Despliegue y Cierre

**Semanas:** 12 a 14 (15/06/2026 – 28/06/2026)
**Responsables principales:** Todo el equipo, liderado por QA / BD + Coordinadora General

### Objetivo

Asegurar el sistema contra amenazas comunes, desplegarlo en un entorno accesible en la nube y realizar la entrega final del proyecto con toda la documentación requerida.

### Entregables

- Sistema completo con seguridad JWT y HTTPS implementados
- Panel de auditoría finalizado y verificado
- Sistema desplegado y accesible en la nube
- Documentación técnica y manual de usuario entregados
- Presentación final al docente

---

### Paso 5.1 — Revisión y endurecimiento de seguridad

**Acciones:**

**Autenticación y sesiones:**

- Verificar que todos los endpoints de la API requieren token JWT válido (excepto el endpoint de login).
- Configurar la expiración del token JWT en 8 horas. Implementar refresh token para sesiones más largas.
- Las contraseñas deben estar hasheadas con `bcrypt` con un costo mínimo de 12 rondas.

**Control de acceso:**

- Realizar una auditoría de todos los endpoints para confirmar que los roles están correctamente restringidos.
- Probar intentos de acceso entre organizaciones distintas (un usuario de la Organización A no debe poder ver documentos de la Organización B).

**Protección de datos:**

- Verificar que los archivos en MinIO no son accesibles públicamente; solo mediante URLs firmadas con tiempo de expiración.
- Asegurarse de que los textos extraídos por OCR (que pueden contener información sensible) solo son accesibles por usuarios autorizados.

**Validación de entradas:**

- Verificar que el sistema rechaza archivos con extensiones no permitidas incluso si el Content-Type es manipulado.
- Implementar límite de tamaño de archivo (máximo sugerido: 20 MB por documento).

---

### Paso 5.2 — Despliegue en la nube

**Acciones:**

- Preparar los Dockerfiles de producción (sin hot-reload, con variables de entorno desde secretos del servidor).
- Desplegar el backend en **Railway** o **Render** (tier gratuito disponible).
- Configurar la base de datos PostgreSQL en el proveedor seleccionado (Railway ofrece PostgreSQL gestionado incluido).
- Configurar el almacenamiento de archivos (MinIO en servidor propio o migrar a un bucket S3 compatible).
- Configurar el dominio web registrado en Punto.pe para apuntar al servidor de producción.
- Habilitar HTTPS con certificado SSL (Let's Encrypt, gestionado automáticamente por Railway/Render).
- Realizar una prueba completa del sistema en el entorno de producción antes de la presentación.

---

### Paso 5.3 — Documentación técnica y manual de usuario

**Documentación técnica** (a cargo de QA / BD):

- Diagrama de arquitectura final (actualizado respecto al diseñado en el Hito 1, con los cambios realizados durante el desarrollo).
- Diagrama ER de la base de datos final.
- Documentación de los endpoints de la API (puede generarse automáticamente con la interfaz `/docs` de FastAPI — Swagger UI).
- Instrucciones de instalación y despliegue en entorno local.
- Reporte de pruebas de IA con métricas de precisión del clasificador.

**Manual de usuario** (a cargo de QA / BD + Frontend):

- Guía paso a paso para administradores: cómo crear categorías, gestionar usuarios, revisar auditoría.
- Guía para editores: cómo subir documentos, corregir clasificaciones, buscar documentos.
- Guía para consultores: cómo buscar y visualizar documentos.
- Capturas de pantalla de cada funcionalidad.

---

### Paso 5.4 — Preparación de la presentación final

**Acciones:**

- Preparar una demostración en vivo del sistema con un escenario realista:
  - Subir un documento físico escaneado (ej. una resolución o un contrato).
  - Mostrar cómo el OCR extrae el texto y la IA lo clasifica automáticamente.
  - Buscar el documento por palabras clave del contenido.
  - Demostrar la creación de una categoría personalizada desde el panel de administración.
  - Mostrar el panel de auditoría con el historial de operaciones.
- Preparar diapositivas con: contexto del problema, solución propuesta, arquitectura, demostración, resultados de precisión de IA, presupuesto real vs. estimado, lecciones aprendidas.
- Ensayar la presentación al menos una vez con el equipo completo.

---

## Resumen del Plan

| Hito                               | Semanas | Período       | Entregable Principal                                     |
| ---------------------------------- | ------- | ------------- | -------------------------------------------------------- |
| 1 — Planificación y Arquitectura   | 1–3     | 23/03 – 12/04 | Diseño completo, esquema BD, repo GitHub                 |
| 2 — Infraestructura y Backend      | 4–6     | 13/04 – 03/05 | API funcional, BD configurada, Docker operativo          |
| 3 — Núcleo de IA (OCR + NLP)       | 7–9     | 04/05 – 24/05 | Módulo OCR + clasificador por categorías personalizables |
| 4 — Frontend e Integración         | 10–12   | 25/05 – 14/06 | Portal web completo, búsqueda semántica integrada        |
| 5 — Seguridad, Despliegue y Cierre | 12–14   | 15/06 – 28/06 | Sistema en producción, documentación, presentación final |

**Presupuesto total estimado:** S/. 6,331.50
**Duración total:** 14 semanas
**Equipo:** 6 personas

---

*Plan elaborado en base al Acta de Constitución del Proyecto — Error 404 — UNAP, Iquitos 2026.*
