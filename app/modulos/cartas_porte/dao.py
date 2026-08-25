"""Capa DAO del módulo cartas de porte."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modulos.cartas_porte.models import CartaPorte


class CartaPorteDAO:
    """Persistencia de intenciones / CPE locales."""

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

    async def buscar_vigente_por_viaje(self, viaje_id: str) -> CartaPorte | None:
        """Intención/CPE no anulada asociada al viaje."""
        resultado = await self._sesion.execute(
            select(CartaPorte).where(
                CartaPorte.viaje_id == viaje_id,
                CartaPorte.estado.in_(
                    ("pendiente", "error", "procesada", "autorizada")
                ),
            )
        )
        return resultado.scalar_one_or_none()

    async def guardar(self, carta: CartaPorte) -> CartaPorte:
        self._sesion.add(carta)
        await self._sesion.flush()
        return carta

    async def proximo_nro_orden(self, sucursal: int) -> int:
        """Siguiente nroOrden WSCPE para la sucursal (único por CUIT/sucursal)."""
        resultado = await self._sesion.execute(select(CartaPorte))
        usados: list[int] = []
        for carta in resultado.scalars():
            payload = carta.payload_afip or {}
            if int(payload.get("sucursal") or 0) != sucursal:
                continue
            valor = payload.get("nro_orden")
            if valor is None or valor == "":
                continue
            try:
                usados.append(int(valor))
            except (TypeError, ValueError):
                continue
        return max(usados, default=0) + 1

    async def eliminar(self, carta: CartaPorte) -> None:
        await self._sesion.delete(carta)
        await self._sesion.flush()
