"""Capa DAO del módulo despachos."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modulos.despachos.models import Despacho, Viaje


class DespachoDAO:
    """Persistencia de campañas y viajes."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def listar(self, estado: str | None = None) -> list[Despacho]:
        """Lista campañas, opcionalmente filtradas por estado."""
        consulta = select(Despacho).order_by(Despacho.fecha_inicio.desc())
        if estado is not None:
            consulta = consulta.where(Despacho.estado == estado)
        resultado = await self._sesion.execute(consulta)
        return list(resultado.scalars())

    async def buscar_por_id(self, despacho_id: str) -> Despacho | None:
        return await self._sesion.get(Despacho, despacho_id)

    async def buscar_viaje(self, despacho_id: str, viaje_id: str) -> Viaje | None:
        """Busca un viaje verificando que pertenezca a la campaña indicada."""
        resultado = await self._sesion.execute(
            select(Viaje).where(Viaje.id == viaje_id, Viaje.despacho_id == despacho_id)
        )
        return resultado.scalar_one_or_none()

    async def guardar(self, despacho: Despacho) -> Despacho:
        self._sesion.add(despacho)
        await self._sesion.flush()
        return despacho

    async def eliminar(self, despacho: Despacho) -> None:
        """Elimina la campaña y sus viajes (cascade definido en el modelo)."""
        await self._sesion.delete(despacho)
        await self._sesion.flush()
