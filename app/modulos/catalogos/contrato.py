"""Contrato público del módulo catálogos.

Otros módulos (ej: despachos) consumen SOLO esta interfaz, nunca los
DAO/models internos. Cuando catálogos se extraiga como microservicio,
se reemplaza la implementación local por un cliente HTTP que cumpla el
mismo Protocol, sin tocar a los consumidores.
"""

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.modulos.catalogos.dao import CatalogosDAO


@dataclass(frozen=True)
class ChoferResumen:
    """Datos mínimos de un chofer que otros módulos necesitan conocer."""

    id: str
    nombre: str
    dominio: str


class ContratoCatalogos(Protocol):
    """Interfaz que catálogos garantiza al resto del sistema."""

    async def existe_productor_con_campo(self, productor_id: str, campo_id: str) -> bool:
        """¿El campo pertenece a ese productor?"""
        ...

    async def existe_material(self, nombre: str) -> bool: ...

    async def obtener_chofer(self, chofer_id: str) -> ChoferResumen | None: ...


class CatalogosLocal:
    """Implementación local del contrato (mismo proceso, misma base)."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._dao = CatalogosDAO(sesion)

    async def existe_productor_con_campo(self, productor_id: str, campo_id: str) -> bool:
        campo = await self._dao.buscar_campo(campo_id)
        return campo is not None and campo.productor_id == productor_id

    async def existe_material(self, nombre: str) -> bool:
        return await self._dao.buscar_material_por_nombre(nombre) is not None

    async def obtener_chofer(self, chofer_id: str) -> ChoferResumen | None:
        chofer = await self._dao.buscar_chofer(chofer_id)
        if chofer is None:
            return None
        dominio = chofer.dominio or ""
        if not dominio and chofer.transportista_id:
            transportista = await self._dao.buscar_transportista(chofer.transportista_id)
            if transportista and transportista.camiones:
                activos = [c for c in transportista.camiones if c.activo]
                if activos:
                    dominio = activos[0].dominio
        return ChoferResumen(id=chofer.id, nombre=chofer.nombre, dominio=dominio)
