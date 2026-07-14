# Guía para agentes de IA — Agro360 API

Backend FastAPI **en español** (código, comentarios, docstrings y mensajes de error). Monolito modular preparado para dividirse en microservicios.

## Mapa del repo

- `app/core/`: infraestructura compartida (config, DB, JWT, bus de eventos, excepciones). **No lleva lógica de negocio.**
- `app/modulos/<modulo>/`: un paquete por módulo de negocio, siempre con la misma estructura: `router.py` (API) → `service.py` (casos de uso) → `bo.py` (reglas puras) + `dao.py` (datos) + `models.py` (ORM) + `schemas.py` (DTOs) + opcional `contrato.py` (interfaz pública).
- `scripts/seed.py`: datos de demo. `tests/`: pytest (unitarios de BO + integración de API).

## Reglas de arquitectura (OBLIGATORIAS)

1. **Nunca** importar service/bo/dao/models de un módulo desde otro módulo. Para consumir datos ajenos usar el `contrato.py` del otro módulo (Protocol inyectable en el constructor del service).
2. **Nunca** crear ForeignKey entre tablas de módulos distintos; usar IDs "débiles" (String) y validar vía contrato.
3. Las tablas llevan prefijo del módulo: `despachos_viaje`, `auth_usuario`, `cpe_carta_porte`.
4. El **commit** solo ocurre en la capa service. Los DAO hacen `flush()`, nunca `commit()`.
5. Los BO son funciones/clases puras: sin sesión de DB, sin HTTP. Lanzan excepciones de `app.core.excepciones`.
6. Los routers no llevan lógica: reciben DTO, llaman al service, devuelven DTO.
7. Efectos secundarios entre módulos → publicar `EventoDominio` en `app.core.eventos` (convención de nombre: `modulo.entidad.accion`). Suscripciones en `eventos.py` del módulo que escucha, registradas en `main.py`.
8. Integraciones externas (AFIP, etc.) siempre detrás de un puerto (`puerto.py` + `adaptadores/`), nunca llamadas directas desde el service.

## Convenciones de código

- Español para todo: nombres, comentarios, docstrings, mensajes de error.
- Endpoints con `operation_id` explícito en snake_case (`crear_despacho`) — lo usan MCP y las tools de agentes.
- DTOs Pydantic con sufijos `Request` / `Response`; ORM con `Mapped[...]` (SQLAlchemy 2.0).
- Errores de negocio: lanzar `RecursoNoEncontrado`, `ReglaDeNegocioViolada`, `NoAutenticado` o `NoAutorizado`; un handler global los convierte a JSON `{"error": {"codigo", "mensaje"}}`.
- IDs: UUID4 en texto (portables entre SQLite y PostgreSQL).

## Cómo agregar un módulo nuevo

1. Crear `app/modulos/<nombre>/` con la estructura estándar (copiar `parametros` como base simple o `despachos` como base completa).
2. Prefijo de tablas: `<nombre>_`.
3. Registrar los models en `crear_tablas()` (`app/core/database.py`) y el router en `crear_aplicacion()` (`app/main.py`).
4. Si otros módulos necesitan sus datos, definir `contrato.py` con un Protocol + implementación local.
5. Tests: reglas en `tests/test_bo_<nombre>.py`, flujo API en integración.

## Comandos

```bash
poetry install                          # dependencias
poetry run uvicorn app.main:app --reload  # dev server (puerto 8000)
poetry run pytest                       # tests
poetry run ruff check . --fix           # lint
poetry run python -m scripts.seed       # seed manual
```

Login demo: `admin@agro360.com` / `demo12345`. Docs interactivas en `/docs`.
