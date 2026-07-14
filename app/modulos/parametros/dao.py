"""Capa DAO del módulo parámetros."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modulos.parametros.models import Parametro


class ParametrosDAO:
    """Persistencia del almacén clave/valor de configuración."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def obtener_todos(self) -> dict[str, str]:
        """Devuelve todos los parámetros como diccionario clave → valor."""
        resultado = await self._sesion.execute(select(Parametro))
        return {p.clave: p.valor for p in resultado.scalars()}

    async def guardar_varios(self, valores: dict[str, str]) -> None:
        """Inserta o actualiza cada clave (upsert simple, commit en service)."""
        for clave, valor in valores.items():
            existente = await self._sesion.get(Parametro, clave)
            if existente is None:
                self._sesion.add(Parametro(clave=clave, valor=valor))
            else:
                existente.valor = valor
        await self._sesion.flush()
