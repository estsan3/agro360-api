"""Infraestructura de base de datos (SQLAlchemy 2.0 async).

Decisiones de diseño pensadas para la futura división en microservicios:

- Cada módulo declara sus tablas con un PREFIJO propio (ej: `despachos_viaje`),
  que actúa como "schema lógico" en SQLite. Al migrar a PostgreSQL, esos
  prefijos se convierten en schemas reales (`despachos.viaje`) y cada módulo
  puede llevarse sus tablas a una base propia sin tocar a los demás.
- Ningún DAO de un módulo consulta tablas de otro módulo: si necesita datos
  ajenos, los pide a través del contrato público del otro módulo.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import obtener_configuracion


class Base(DeclarativeBase):
    """Base declarativa común para todos los modelos ORM del sistema."""


# Motor y fábrica de sesiones únicos para todo el proceso.
_config = obtener_configuracion()
engine = create_async_engine(_config.database_url, echo=False)
fabrica_sesiones = async_sessionmaker(engine, expire_on_commit=False)


async def obtener_sesion() -> AsyncIterator[AsyncSession]:
    """Dependencia FastAPI: abre una sesión por request y la cierra al final.

    El commit/rollback es responsabilidad de la capa service (que define
    los límites transaccionales de cada caso de uso).
    """
    async with fabrica_sesiones() as sesion:
        yield sesion


async def crear_tablas() -> None:
    """Crea todas las tablas declaradas. Para desarrollo con SQLite.

    En producción (PostgreSQL) esto se reemplaza por migraciones Alembic,
    una carpeta de migraciones por módulo.
    """
    # Importamos los modelos de todos los módulos para que queden
    # registrados en la metadata de `Base` antes de crear las tablas.
    from app.modulos.auth import models as _auth_models  # noqa: F401
    from app.modulos.cartas_porte import models as _cpe_models  # noqa: F401
    from app.modulos.catalogos import models as _catalogos_models  # noqa: F401
    from app.modulos.despachos import models as _despachos_models  # noqa: F401
    from app.modulos.liquidaciones import models as _liquidaciones_models  # noqa: F401
    from app.modulos.lista_espera import models as _lista_espera_models  # noqa: F401
    from app.modulos.mensajeria import models as _mensajeria_models  # noqa: F401
    from app.modulos.parametros import models as _parametros_models  # noqa: F401

    async with engine.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)
        await conexion.run_sync(_agregar_columnas_sqlite_si_faltan)


def _agregar_columnas_sqlite_si_faltan(conexion_sync) -> None:
    """SQLite no altera tablas ya creadas; agrega columnas nuevas de CPE."""
    if conexion_sync.dialect.name != "sqlite":
        return
    from sqlalchemy import inspect, text

    inspector = inspect(conexion_sync)
    pendientes = (
        ("despachos_despacho", "cpe_nro_renspa", "VARCHAR(40)"),
        ("despachos_despacho", "cpe_codigo_turno", "VARCHAR(80)"),
        ("despachos_despacho", "cpe_hora_partida", "VARCHAR(5)"),
        ("despachos_despacho", "cpe_cuit_remitente_comercial_vs2", "VARCHAR(13)"),
        ("despachos_despacho", "cpe_cuit_remitente_comercial_productor", "VARCHAR(13)"),
        ("despachos_viaje", "cpe_codigo_turno", "VARCHAR(80)"),
        ("despachos_viaje", "cpe_dominio_acoplado", "VARCHAR(10)"),
        ("despachos_viaje", "checklist_gasoil", "BOOLEAN DEFAULT 0"),
        ("despachos_viaje", "checklist_efectivo", "BOOLEAN DEFAULT 0"),
        ("catalogos_campo", "nro_renspa", "VARCHAR(40)"),
    )
    for tabla, columna, tipo in pendientes:
        if tabla not in inspector.get_table_names():
            continue
        existentes = {c["name"] for c in inspector.get_columns(tabla)}
        if columna not in existentes:
            conexion_sync.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}"))
