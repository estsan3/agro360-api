# Agro360 API

Backend de **Agro360**, sistema de gestión logística de despachos de granos del agro argentino. Es la contraparte del front admin Angular ([`agro360-web`](../agro360-web)) y el futuro backend de la app mobile del chofer.

Construido como **monolito modular** con FastAPI: cada módulo de negocio es autónomo y puede extraerse como microservicio independiente sin reescritura cuando el sistema escale.

---

## Tabla de contenidos

1. [Alcance](#alcance)
2. [Arquitectura](#arquitectura)
3. [Módulos](#modulos)
4. [Tecnología](#tecnologia)
5. [Cómo correrlo paso a paso](#correrlo)
6. [Configuración](#configuracion)
7. [API y autenticación](#api)
8. [Testing y calidad](#testing)
9. [Integración con agentes de IA](#ia)
10. [Roadmap de escalado](#roadmap)

---

<a id="alcance"></a>

## 1. Alcance

### Qué resuelve

En la logística de granos, una **campaña de despacho** implica sacar toneladas desde un **campo** hacia un **destino de descarga** (puerto, terminal) con múltiples **viajes en camión**. Esta API cubre:

- Planificación de campañas (productor, campo, material, fechas, responsables).
- Asignación de choferes y patentes a cada viaje, con seguimiento de estado.
- Mensajería entre el equipo admin y los choferes en ruta.
- **Emisión de Cartas de Porte Electrónicas (CPE)** para respaldar cada viaje, con integración a ARCA/AFIP (RG 5017/2021).
- Catálogos maestros, parámetros comerciales y KPIs de reportería.

### Qué incluye este repo / qué no

| Incluido | No incluido (por ahora) |
|----------|-------------------------|
| API REST completa con autenticación JWT y roles | App mobile del chofer |
| Persistencia (SQLite en dev, PostgreSQL al escalar) | Tracking GPS |
| Emisión de CPE con adaptador simulado + esqueleto AFIP real | Facturación / liquidación (WSLPG) |
| Seed con los mismos datos de demo que el front | WebSockets (el chat funciona con REST + polling) |
| Docker + tests + servidor MCP opcional | Migraciones Alembic (las tablas se crean directo en dev) |

---

<a id="arquitectura"></a>

## 2. Arquitectura

### Visión general

**Monolito modular**: una sola aplicación FastAPI, pero organizada en módulos aislados que se comportan como microservicios internos. La regla de oro es que **ningún módulo conoce los detalles internos de otro**.

```text
                    ┌──────────────────────────────────────────┐
                    │              FastAPI (main.py)           │
                    │   registra routers, errores y eventos    │
                    └──────────────────────────────────────────┘
                                        │
   ┌─────────┬──────────┬───────────┬──┴──────────┬────────────┬────────────┐
   ▼         ▼          ▼           ▼             ▼            ▼            ▼
┌──────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐
│ auth │ │catalogos│ │despachos│ │mensajeria│ │cartas_   │ │parametros│ │reporteria│
│      │ │         │ │         │ │          │ │porte     │ │         │ │          │
└──────┘ └─────────┘ └─────────┘ └──────────┘ └──────────┘ └─────────┘ └──────────┘
                │           │            ▲            │                      │
                │ contrato  │  eventos   │            │ puerto/adaptador     │ contratos
                └───────────┤  de dominio│            ▼                      │
                            └────────────┘      ARCA/AFIP (WSCPE)  ◄─────────┘
```

### Capas dentro de cada módulo

```text
HTTP → router.py → service.py → bo.py
        (API)      (casos de     (reglas de
                    uso, tx)      negocio puras)
                       │
                       └────→ dao.py → models.py → DB
                              (acceso    (ORM)
                               a datos)
```

| Capa | Archivo | Responsabilidad | Qué NO hace |
|------|---------|-----------------|-------------|
| **API** | `router.py` | Endpoints HTTP, validación de entrada con DTOs | Lógica de negocio |
| **Service** | `service.py` | Casos de uso, orquestación, **commit/rollback** (límite transaccional) | SQL directo |
| **BO** | `bo.py` | Reglas de negocio puras, testeables sin base de datos ni HTTP | Tocar DB o HTTP |
| **DAO** | `dao.py` | Consultas y persistencia con SQLAlchemy (`flush`, nunca `commit`) | Validar negocio |
| **Modelos** | `models.py` | Tablas ORM con prefijo del módulo | — |
| **Schemas** | `schemas.py` | DTOs Pydantic de entrada (`*Request`) y salida (`*Response`) | — |
| **Contrato** | `contrato.py` | Interfaz pública (`Protocol`) que otros módulos pueden consumir | Exponer internals |

### Reglas de diseño para la escisión futura en microservicios

1. **Comunicación sincrónica por contratos.** Un módulo nunca importa el service/bo/dao/models de otro: consume su `contrato.py`, una interfaz `Protocol` que se inyecta en el constructor del service. Al extraer un módulo, el contrato se reimplementa como cliente HTTP y los consumidores no cambian ni una línea.

2. **Comunicación asincrónica por eventos de dominio.** `core/eventos.py` implementa un bus publish/subscribe en memoria. Convención de nombres: `modulo.entidad.accion` (ej: `despachos.viaje.retrasado`). Al escalar, el bus se reemplaza por un broker (RabbitMQ / Redis Streams) manteniendo la misma interfaz `publicar`/`suscribir`. Ejemplo real en el código: mensajería escucha los eventos de viajes y agrega avisos de sistema en el chat del chofer.

3. **Referencias entre módulos por ID "débil".** Sin ForeignKey entre tablas de módulos distintos; la integridad se valida en la capa service a través del contrato. Cada módulo puede llevarse sus tablas a una base propia.

4. **Schemas lógicos por prefijo de tabla.** `despachos_viaje`, `auth_usuario`, `cpe_carta_porte`. Al migrar a PostgreSQL se convierten en schemas reales, y de ahí a bases separadas.

5. **Integraciones externas detrás de puertos.** `cartas_porte/puerto.py` define la interfaz `ProveedorCPE`; los adaptadores (`simulado`, `afip`) son intercambiables por inyección. El negocio nunca llama a un SDK directamente.

6. **Autorización sin estado compartido.** La identidad viaja completa en los claims del JWT (id, email, rol), por lo que cualquier módulo extraído puede autorizar requests con solo conocer el secreto de firma, sin consultar la base de usuarios.

### Estructura de carpetas

```text
agro360-api/
├── app/
│   ├── main.py                # Composición: routers, CORS, errores, eventos, MCP
│   ├── core/                  # Infraestructura compartida (SIN negocio)
│   │   ├── config.py          #   Variables de entorno tipadas (AGRO360_*)
│   │   ├── database.py        #   Engine async, sesiones, Base declarativa
│   │   ├── seguridad.py       #   JWT + hashing bcrypt
│   │   ├── dependencias.py    #   Usuario actual y requerir_rol() para FastAPI
│   │   ├── eventos.py         #   Bus de eventos de dominio (en memoria)
│   │   └── excepciones.py     #   Errores de negocio → respuesta HTTP unificada
│   └── modulos/
│       ├── auth/              # Usuarios, login, JWT, roles
│       ├── catalogos/         # Productores, campos, materiales, choferes
│       ├── despachos/         # Campañas y viajes (núcleo del dominio)
│       ├── mensajeria/        # Chat admin ↔ chofer
│       ├── cartas_porte/      # CPE con puerto/adaptadores hacia ARCA/AFIP
│       ├── parametros/        # Config comercial y preferencias
│       └── reporteria/        # KPIs (solo lectura, compone contratos)
├── scripts/seed.py            # Datos de demo (espejo del mock del front)
├── tests/                     # Unitarios (BO) + integración (API completa)
├── Dockerfile                 # Build multi-etapa con Poetry
├── docker-compose.yml         # API + Postgres comentado para el futuro
├── pyproject.toml             # Dependencias y tooling (Poetry)
├── .env.example               # Plantilla de configuración
└── AGENTS.md                  # Guía de convenciones para agentes de IA
```

---

<a id="modulos"></a>

## 3. Módulos

### `auth` — Autenticación y usuarios

Gestiona los usuarios del backoffice (roles `administrador` y `vendedor`), el login y la emisión de JWT. Las contraseñas se almacenan con bcrypt; el token lleva id, email y rol en los claims para autorizar sin consultar la base.

Endpoints: `POST /auth/login`, `GET /auth/me`, `GET|POST /auth/usuarios` (solo admin).

### `catalogos` — Maestros

Cuatro catálogos: **productores** (con sus **campos**), **materiales** (granos, con el código de grano de ARCA/AFIP para la CPE) y **choferes** (con dominio/patente validada contra los formatos argentinos `ABC123` y `AB123CD`).

Expone `contrato.py` con `existe_productor_con_campo()`, `existe_material()` y `obtener_chofer()`, que consumen despachos y mensajería.

Endpoints: `GET|POST /catalogos/productores`, `POST /catalogos/productores/{id}/campos`, `GET|POST /catalogos/materiales`, `GET|POST /catalogos/choferes`.

### `despachos` — Campañas y viajes (núcleo)

Una **campaña** agrupa origen, material, fechas, responsables y N **viajes**. Reglas de negocio implementadas en el BO:

- Campaña: nace en `borrador`, pasa a `activo` al enviarse; no se activa sin viajes; no se elimina si está activa; la llegada estimada no puede ser anterior al inicio.
- Viaje: máquina de estados `pendiente → en_viaje → retrasado/completado` (con vueltas de `retrasado` a `en_viaje`); `completado` es final y fuerza progreso 100.

Publica eventos de dominio (`despachos.viaje.completado`, `despachos.viaje.retrasado`, `despachos.despacho.activado`) y expone `contrato.py` con `obtener_viaje()` y `calcular_metricas()` para cartas de porte y reportería.

Endpoints: `GET|POST /despachos`, `GET|DELETE /despachos/{id}`, `POST /despachos/{id}/activar`, `POST /despachos/{id}/viajes`, `PATCH /despachos/{id}/viajes/{viaje_id}`.

### `mensajeria` — Chat admin ↔ chofer

Conversaciones por chofer con contador de no leídos (solo suman los mensajes del chofer y del sistema). Abrir una conversación marca los mensajes como leídos. Se suscribe a los eventos de despachos: cuando un viaje se retrasa o completa, inserta automáticamente un aviso de "sistema" en el hilo del chofer, sin acoplarse al módulo despachos.

Endpoints: `GET /mensajeria/conversaciones`, `GET /mensajeria/conversaciones/{id}`, `POST /mensajeria/conversaciones/{id}/mensajes`, `POST /mensajeria/conversaciones/chofer/{chofer_id}`.

### `cartas_porte` — Carta de Porte Electrónica (CPE)

El diferencial del sistema: emite la CPE que respalda legalmente cada viaje de granos (RG 5017/2021). Diseñado con **puerto y adaptadores**:

- `puerto.py`: interfaz `ProveedorCPE` (`autorizar_cpe_automotor`, `anular_cpe`) con DTOs normalizados.
- `adaptadores/simulado.py`: genera números de CPE y CTG ficticios con formato real — permite desarrollar y testear sin certificado digital.
- `adaptadores/afip.py`: esqueleto documentado de la integración real vía **PyAfipWs** (WSAA para el ticket de acceso + WSCPE para autorizar). Incluye el pseudocódigo completo y los endpoints de homologación/producción de ARCA. Se activa cuando haya certificado digital.

**Trazabilidad SENASA (RENSPA).** SENASA no publica un webservice propio para cartas de porte: su integración se materializa **dentro de la misma CPE**, informando el **RENSPA** (Registro Nacional Sanitario de Productores Agropecuarios) del campo de origen como campo de procedencia del WSCPE (vigente desde julio 2025 vía VISEC + SENASA + ARCA, clave para trazabilidad y EUDR). Por eso no existe un puerto separado hacia SENASA: cuando se complete el adaptador real de AFIP, el RENSPA del productor/campo viajará en la solicitud de autorización de la CPE. Queda pendiente agregar el campo RENSPA al catálogo de campos (módulo `catalogos`) como parte de ese trabajo.

Reglas de negocio: un viaje solo puede tener una CPE autorizada vigente, debe tener chofer/dominio asignado y no estar completado. Cada intento (autorizado o rechazado) queda registrado para auditoría. Publica `cartas_porte.cpe.autorizada`.

Endpoints: `GET|POST /cartas-porte`, `GET /cartas-porte/{id}`, `POST /cartas-porte/{id}/anular`.

### `parametros` — Configuración de negocio

Almacén clave/valor tipado: precio por tonelada y moneda (`ARS`/`USD`), y preferencias de notificación (viaje retrasado, viaje completado, mensaje de chofer). Sin BO: la validación de tipos la hacen los schemas Pydantic.

Endpoints: `GET|PUT /parametros/negocio`, `GET|PUT /parametros/preferencias`.

### `reporteria` — KPIs

Módulo de **solo lectura y sin tablas propias**: compone datos de otros módulos a través de sus contratos. Calcula campañas activas, viajes por estado, toneladas totales/completadas, porcentaje de avance y valorización según el precio por tonelada configurado.

Endpoint: `GET /reporteria/kpis`.

---

<a id="tecnologia"></a>

## 4. Tecnología

| Componente | Elección | Nota |
|------------|----------|------|
| Lenguaje | Python 3.11+ | Todo el código y los comentarios en español |
| Framework | FastAPI | OpenAPI automático en `/docs`, async nativo |
| ORM | SQLAlchemy 2.0 (async) | Estilo `Mapped[...]`, sesiones por request |
| Base de datos | SQLite (dev) → PostgreSQL (prod) | Driver `aiosqlite`; `asyncpg` comentado en pyproject |
| Validación | Pydantic v2 + pydantic-settings | DTOs y configuración tipada |
| Auth | PyJWT + bcrypt | JWT con claims de rol; hashing de contraseñas |
| Servidor | Uvicorn | — |
| Dependencias | Poetry | `poetry.lock` versionado |
| Tests | pytest + pytest-asyncio + httpx | Unitarios de BO + integración de API |
| Lint | ruff | Reglas E, F, I (imports), UP |
| Contenedores | Docker + docker-compose | Build multi-etapa, usuario sin privilegios |
| Agentes de IA | AGENTS.md + fastapi-mcp (opcional) | Servidor MCP en `/mcp` |
| Integración AFIP | PyAfipWs (a instalar con el certificado) | WSAA + WSCPE, RG 5017/2021 |

---

<a id="correrlo"></a>

## 5. Cómo correrlo paso a paso

### Opción A: local con Poetry (recomendada para desarrollo)

**Paso 1 — Requisitos.** Python 3.11 o superior y Poetry. Si no tenés Poetry:

```bash
pip3 install --user poetry
# Verificar:
poetry --version
```

**Paso 2 — Clonar / ubicarse en el repo.**

```bash
cd ~/agro360-api
```

**Paso 3 — Instalar dependencias.**

```bash
poetry install
```

**Paso 4 — Configuración (opcional).** Por defecto funciona sin configurar nada. Para personalizar:

```bash
cp .env.example .env
# editar .env con tus valores
```

**Paso 5 — Levantar la API.**

```bash
poetry run uvicorn app.main:app --reload
```

Al iniciar en dev se crean las tablas (SQLite en `data/agro360.db`) y se siembran datos de demo automáticamente.

**Paso 6 — Verificar.**

- Salud: [http://localhost:8000/health](http://localhost:8000/health)
- Documentación interactiva (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
- Login de demo:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@agro360.com", "password": "demo12345"}'
```

**Paso 7 — Usar el token.** Copiar el `access_token` de la respuesta y enviarlo en cada request:

```bash
curl http://localhost:8000/api/v1/despachos \
  -H "Authorization: Bearer <access_token>"
```

### Opción B: con Docker

**Paso 1 — Requisitos.** Docker Desktop (o Docker Engine + Compose).

**Paso 2 — Levantar.**

```bash
cd ~/agro360-api
docker compose up --build
```

**Paso 3 — Verificar.** Igual que la opción A: la API queda en `http://localhost:8000`, docs en `/docs`, mismas credenciales de demo. La base SQLite persiste en el volumen `agro360-data`.

**Para bajarla:**

```bash
docker compose down          # conserva los datos
docker compose down -v       # borra también la base
```

### Conectar el front Angular

El front (`agro360-web`) corre en `http://localhost:4200` y ya está permitido por CORS. Cuando se desactive el mock del front (`mockApi: false`), apuntar su `apiUrl` a `http://localhost:8000/api/v1`.

### Comandos útiles

```bash
poetry run pytest                        # correr los tests
poetry run ruff check . --fix            # lint con autofix
poetry run python -m scripts.seed        # sembrar datos de demo manualmente
```

---

<a id="configuracion"></a>

## 6. Configuración

Todas las variables llevan el prefijo `AGRO360_` y se leen del entorno o de `.env` (ver `.env.example`):

| Variable | Default | Descripción |
|----------|---------|-------------|
| `AGRO360_ENTORNO` | `dev` | `dev` \| `test` \| `prod` |
| `AGRO360_DATABASE_URL` | SQLite local | Cambiar a `postgresql+asyncpg://...` al escalar |
| `AGRO360_JWT_SECRETO` | (inseguro) | **Obligatorio** cambiarlo en producción: `openssl rand -hex 32` |
| `AGRO360_JWT_EXPIRACION_MINUTOS` | `480` | Validez del token de acceso |
| `AGRO360_CORS_ORIGINS` | `http://localhost:4200` | Orígenes permitidos, separados por coma |
| `AGRO360_SEED_AL_INICIAR` | `true` | Datos de demo si la base está vacía (ignorado en prod) |
| `AGRO360_MCP_HABILITADO` | `false` | Expone el servidor MCP en `/mcp` |

---

<a id="api"></a>

## 7. API y autenticación

- Todos los endpoints de negocio viven bajo **`/api/v1`** y requieren `Authorization: Bearer <token>` (excepto `POST /auth/login` y `GET /health`).
- Las operaciones de escritura sobre catálogos, usuarios y parámetros comerciales exigen rol `administrador`.
- La documentación viva está en `/docs` (Swagger UI) y `/redoc`.
- Errores de negocio con formato unificado y códigos estables:

```json
{ "error": { "codigo": "regla_violada", "mensaje": "No se puede activar una campaña sin viajes cargados" } }
```

| Código | HTTP | Significado |
|--------|------|-------------|
| `no_autenticado` | 401 | Token ausente, inválido o credenciales incorrectas |
| `no_autorizado` | 403 | Autenticado pero sin permisos (rol) |
| `no_encontrado` | 404 | La entidad no existe |
| `regla_violada` | 422 | La operación viola una regla del dominio |

---

<a id="testing"></a>

## 8. Testing y calidad

```bash
poetry run pytest          # suite completa
poetry run ruff check .    # lint
```

Dos niveles de tests:

- **Unitarios de BO** (`tests/test_bo_despachos.py`): prueban las reglas de negocio con objetos en memoria, sin base de datos — la ventaja directa de separar la capa BO.
- **Integración de API** (`tests/test_api_flujo_completo.py`): levantan la app completa contra SQLite en memoria y recorren el flujo real de negocio: login → catálogos → campaña con viaje → activación → emisión de carta de porte → KPIs. Sirven como documentación ejecutable de la API.

---

<a id="ia"></a>

## 9. Integración con agentes de IA

- **`AGENTS.md`**: mapa del repo, reglas de arquitectura obligatorias y receta para agregar módulos. Es lo primero que lee un agente de código (Cursor, etc.) al trabajar en este repo.
- **OpenAPI con `operation_id` legibles** (`crear_despacho`, `emitir_carta_porte`): los agentes pueden consumir la API como tools con nombres claros.
- **Servidor MCP opcional**: expone los endpoints como herramientas MCP en `/mcp`.

```bash
poetry install --with mcp
AGRO360_MCP_HABILITADO=true poetry run uvicorn app.main:app
```

---

<a id="roadmap"></a>

## 10. Roadmap de escalado

1. **PostgreSQL**: cambiar `AGRO360_DATABASE_URL`, descomentar `asyncpg` en `pyproject.toml` y el servicio `db` en `docker-compose.yml`. Agregar Alembic con una carpeta de migraciones por módulo.
2. **Broker de eventos**: reemplazar el `BusEventos` en memoria por un adaptador a RabbitMQ o Redis Streams, manteniendo la interfaz `publicar`/`suscribir`. Los módulos no cambian.
3. **Extraer el primer microservicio**: mover la carpeta del módulo a un servicio nuevo, reimplementar su `contrato.py` como cliente HTTP en los consumidores y llevarse sus tablas (ya aisladas por prefijo) a su propia base.
4. **CPE real contra ARCA/AFIP**: obtener el certificado digital, dar de alta el servicio `wscpe` en WSAA (homologación primero), instalar PyAfipWs, completar `cartas_porte/adaptadores/afip.py` e inyectarlo por configuración en lugar del simulado. Incluye la trazabilidad SENASA: agregar el RENSPA a los campos del catálogo e informarlo como procedencia en la CPE.
5. **WebSockets** para mensajería y estados de viaje en tiempo real (hoy REST + polling desde el front).
6. **Guards por rol más granulares** y auditoría de operaciones.
