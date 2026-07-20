"""Punto de entrada de la API Agro360.

Composición de la aplicación: registra los routers de cada módulo, los
handlers de errores, las suscripciones a eventos y (opcionalmente) el
servidor MCP para agentes de IA.

Ejecutar en desarrollo:
    poetry run uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import obtener_configuracion
from app.core.database import crear_tablas
from app.core.excepciones import ErrorDeNegocio, manejar_error_de_negocio
from app.modulos.auth.router import router as auth_router
from app.modulos.auth.router import router_usuarios, router_vendedores
from app.modulos.cartas_porte.router import router as cartas_porte_router
from app.modulos.catalogos.router import router as catalogos_router
from app.modulos.catalogos.router_productores_abm import router as productores_abm_router
from app.modulos.catalogos.router_transportistas_abm import router as transportistas_abm_router
from app.modulos.despachos.router import router as despachos_router
from app.modulos.liquidaciones.eventos import (
    registrar_suscripciones as registrar_suscripciones_liquidaciones,
)
from app.modulos.liquidaciones.router import router as liquidaciones_router
from app.modulos.mensajeria.eventos import registrar_suscripciones
from app.modulos.mensajeria.router import router as mensajeria_router
from app.modulos.parametros.router import router as parametros_router
from app.modulos.reporteria.router import router as reporteria_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Inicialización al arrancar: tablas, eventos y seed de demo."""
    config = obtener_configuracion()

    # En dev/test las tablas se crean directo; en prod, migraciones Alembic.
    await crear_tablas()

    # Suscripciones al bus de eventos (mensajería y liquidaciones escuchan a despachos).
    registrar_suscripciones()
    registrar_suscripciones_liquidaciones()

    # Datos de demo si la base está vacía (equivalente al mock del front).
    if config.seed_al_iniciar and not config.es_produccion:
        from scripts.seed import sembrar_datos_demo

        await sembrar_datos_demo()

    logger.info("Agro360 API iniciada (entorno: %s)", config.entorno)
    yield


def crear_aplicacion() -> FastAPI:
    """Fábrica de la aplicación FastAPI con todos los módulos registrados."""
    config = obtener_configuracion()

    app = FastAPI(
        title="Agro360 API",
        description=(
            "Backend modular de Agro360: gestión logística de despachos de granos. "
            "Módulos: auth, catálogos, despachos, mensajería, cartas de porte, "
            "parámetros y reportería."
        ),
        version="0.1.0",
        lifespan=ciclo_de_vida,
    )

    # CORS para el front Angular.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins_lista,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Errores de negocio → respuesta JSON unificada.
    app.add_exception_handler(ErrorDeNegocio, manejar_error_de_negocio)  # type: ignore[arg-type]

    # Un router por módulo, todos bajo /api/v1.
    prefijo = "/api/v1"
    app.include_router(auth_router, prefix=prefijo)
    app.include_router(router_usuarios, prefix=prefijo)
    # Antes que catálogos: /catalogos/vendedores debe matchear primero.
    app.include_router(router_vendedores, prefix=prefijo)
    app.include_router(catalogos_router, prefix=prefijo)
    app.include_router(transportistas_abm_router, prefix=prefijo)
    app.include_router(productores_abm_router, prefix=prefijo)
    app.include_router(despachos_router, prefix=prefijo)
    app.include_router(mensajeria_router, prefix=prefijo)
    app.include_router(cartas_porte_router, prefix=prefijo)
    app.include_router(parametros_router, prefix=prefijo)
    app.include_router(liquidaciones_router, prefix=prefijo)
    app.include_router(reporteria_router, prefix=prefijo)

    @app.get("/health", tags=["Infraestructura"], operation_id="health")
    async def health() -> dict[str, str]:
        """Chequeo de vida para orquestadores (Docker, Kubernetes)."""
        return {"status": "ok"}

    # Servidor MCP opcional: expone los endpoints como tools para agentes de IA.
    if config.mcp_habilitado:
        _montar_mcp(app)

    return app


def _montar_mcp(app: FastAPI) -> None:
    """Monta el servidor MCP en /mcp (requiere `poetry install --with mcp`)."""
    try:
        from fastapi_mcp import FastApiMCP

        mcp = FastApiMCP(app, name="Agro360")
        mcp.mount()
        logger.info("Servidor MCP montado en /mcp")
    except ImportError:
        logger.warning(
            "AGRO360_MCP_HABILITADO=true pero falta fastapi-mcp. "
            "Instalar con: poetry install --with mcp"
        )


app = crear_aplicacion()
