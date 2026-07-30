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
    transportista_id: str | None = None
    camion_id: str | None = None


@dataclass(frozen=True)
class TransportistaResumen:
    """Datos mínimos de una empresa transportista."""

    id: str
    nombre: str
    es_flota_propia: bool = False


@dataclass(frozen=True)
class UnidadFlotaResumen:
    """Chofer + camión listos para despacho (propia o terceros)."""

    transportista_id: str
    transportista_nombre: str
    es_flota_propia: bool
    chofer_id: str
    chofer_nombre: str
    camion_id: str
    dominio: str
    capacidad_tn: float | None
    tipo_unidad: str


class ContratoCatalogos(Protocol):
    """Interfaz que catálogos garantiza al resto del sistema."""

    async def existe_productor_con_campo(self, productor_id: str, campo_id: str) -> bool:
        """¿El campo pertenece a ese productor?"""
        ...

    async def existe_material(self, nombre: str) -> bool: ...

    async def obtener_chofer(self, chofer_id: str) -> ChoferResumen | None: ...

    async def obtener_nombre_transportista(self, transportista_id: str) -> str | None: ...

    async def listar_transportistas_activos(self) -> list[TransportistaResumen]: ...

    async def obtener_unidad(self, camion_id: str) -> UnidadFlotaResumen | None:
        """Datos de compatibilidad de un camión (con chofer vinculado si hay)."""
        ...

    async def listar_unidades_propias(self) -> list[UnidadFlotaResumen]:
        """Unidades de flota propia activas con chofer asignado al camión."""
        ...

    async def obtener_unidad_por_chofer_camion(
        self, chofer_id: str, camion_id: str
    ) -> UnidadFlotaResumen | None:
        """Valida el trío chofer/camión/transportista para anotar en lista."""
        ...


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
        camion_id = chofer.camion_id
        if camion_id:
            camion = await self._dao.buscar_camion(camion_id)
            if camion and camion.activo:
                dominio = camion.dominio
        elif chofer.transportista_id:
            transportista = await self._dao.buscar_transportista(chofer.transportista_id)
            if transportista and transportista.camiones:
                activos = [c for c in transportista.camiones if c.activo]
                if activos:
                    dominio = activos[0].dominio
                    camion_id = activos[0].id
        return ChoferResumen(
            id=chofer.id,
            nombre=chofer.nombre,
            dominio=dominio,
            transportista_id=chofer.transportista_id,
            camion_id=camion_id,
        )

    async def obtener_nombre_transportista(self, transportista_id: str) -> str | None:
        transportista = await self._dao.buscar_transportista(transportista_id)
        return transportista.nombre if transportista else None

    async def listar_transportistas_activos(self) -> list[TransportistaResumen]:
        filas = await self._dao.listar_transportistas(solo_activos=True)
        return [
            TransportistaResumen(
                id=t.id, nombre=t.nombre, es_flota_propia=bool(t.es_flota_propia)
            )
            for t in filas
        ]

    async def obtener_unidad(self, camion_id: str) -> UnidadFlotaResumen | None:
        camion = await self._dao.buscar_camion(camion_id)
        if camion is None or not camion.activo:
            return None
        transportista = await self._dao.buscar_transportista(camion.transportista_id)
        if transportista is None or not transportista.activo:
            return None
        chofer = next(
            (c for c in transportista.choferes if c.camion_id == camion.id and c.activo),
            None,
        )
        if chofer is None:
            return None
        return UnidadFlotaResumen(
            transportista_id=transportista.id,
            transportista_nombre=transportista.nombre,
            es_flota_propia=bool(transportista.es_flota_propia),
            chofer_id=chofer.id,
            chofer_nombre=chofer.nombre,
            camion_id=camion.id,
            dominio=camion.dominio,
            capacidad_tn=camion.capacidad_tn,
            tipo_unidad=camion.tipo_unidad or "tolva",
        )

    async def listar_unidades_propias(self) -> list[UnidadFlotaResumen]:
        filas = await self._dao.listar_transportistas(solo_activos=True)
        unidades: list[UnidadFlotaResumen] = []
        for t in filas:
            if not t.es_flota_propia:
                continue
            camiones_por_id = {c.id: c for c in t.camiones if c.activo}
            for chofer in t.choferes:
                if not chofer.activo or not chofer.camion_id:
                    continue
                camion = camiones_por_id.get(chofer.camion_id)
                if camion is None:
                    continue
                unidades.append(
                    UnidadFlotaResumen(
                        transportista_id=t.id,
                        transportista_nombre=t.nombre,
                        es_flota_propia=True,
                        chofer_id=chofer.id,
                        chofer_nombre=chofer.nombre,
                        camion_id=camion.id,
                        dominio=camion.dominio,
                        capacidad_tn=camion.capacidad_tn,
                        tipo_unidad=camion.tipo_unidad or "tolva",
                    )
                )
        return unidades

    async def obtener_unidad_por_chofer_camion(
        self, chofer_id: str, camion_id: str
    ) -> UnidadFlotaResumen | None:
        chofer = await self._dao.buscar_chofer(chofer_id)
        camion = await self._dao.buscar_camion(camion_id)
        if chofer is None or camion is None:
            return None
        if not chofer.activo or not camion.activo:
            return None
        if chofer.camion_id and chofer.camion_id != camion_id:
            return None
        if chofer.transportista_id != camion.transportista_id:
            return None
        transportista = await self._dao.buscar_transportista(camion.transportista_id)
        if transportista is None or not transportista.activo:
            return None
        return UnidadFlotaResumen(
            transportista_id=transportista.id,
            transportista_nombre=transportista.nombre,
            es_flota_propia=bool(transportista.es_flota_propia),
            chofer_id=chofer.id,
            chofer_nombre=chofer.nombre,
            camion_id=camion.id,
            dominio=camion.dominio,
            capacidad_tn=camion.capacidad_tn,
            tipo_unidad=camion.tipo_unidad or "tolva",
        )
