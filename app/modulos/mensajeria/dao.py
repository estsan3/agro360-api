"""Capa DAO del módulo mensajería."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modulos.mensajeria.models import Conversacion, Mensaje


class MensajeriaDAO:
    """Persistencia de conversaciones y mensajes."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def listar_conversaciones(self) -> list[Conversacion]:
        """Lista conversaciones, primero las que tienen mensajes sin leer."""
        resultado = await self._sesion.execute(
            select(Conversacion).order_by(Conversacion.no_leidos.desc())
        )
        return list(resultado.scalars())

    async def buscar_conversacion(self, conversacion_id: str) -> Conversacion | None:
        return await self._sesion.get(Conversacion, conversacion_id)

    async def buscar_por_chofer(self, chofer_id: str) -> Conversacion | None:
        resultado = await self._sesion.execute(
            select(Conversacion).where(Conversacion.chofer_id == chofer_id)
        )
        return resultado.scalar_one_or_none()

    async def guardar_conversacion(self, conversacion: Conversacion) -> Conversacion:
        self._sesion.add(conversacion)
        await self._sesion.flush()
        return conversacion

    async def agregar_mensaje(self, mensaje: Mensaje) -> Mensaje:
        self._sesion.add(mensaje)
        await self._sesion.flush()
        return mensaje
