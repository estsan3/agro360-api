"""Capa DAO del módulo cartas de porte."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modulos.cartas_porte.models import CartaPorte


class CartaPorteDAO:
    """Persistencia del registro local de CPE emitidas."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def listar(self, despacho_id: str | None = None) -> list[CartaPorte]:
        consulta = select(CartaPorte).order_by(CartaPorte.creada_en.desc())
        if despacho_id is not None:
            consulta = consulta.where(CartaPorte.despacho_id == despacho_id)
        resultado = await self._sesion.execute(consulta)
        return list(resultado.scalars())

    async def buscar_por_id(self, carta_id: str) -> CartaPorte | None:
        return await self._sesion.get(CartaPorte, carta_id)

    async def buscar_autorizada_por_viaje(self, viaje_id: str) -> CartaPorte | None:
        """Busca una CPE vigente (autorizada) para el viaje indicado."""
        resultado = await self._sesion.execute(
            select(CartaPorte).where(
                CartaPorte.viaje_id == viaje_id,
                CartaPorte.estado == "autorizada",
            )
        )
        return resultado.scalar_one_or_none()

    async def guardar(self, carta: CartaPorte) -> CartaPorte:
        self._sesion.add(carta)
        await self._sesion.flush()
        return carta
