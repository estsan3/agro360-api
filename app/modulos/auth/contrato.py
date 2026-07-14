"""Contrato público del módulo auth.

Otros módulos (ej: catálogos, para componer administradores y vendedores
en su respuesta agregada) consumen SOLO esta interfaz, nunca los
DAO/models internos.
"""

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.modulos.auth.dao import UsuarioDAO


@dataclass(frozen=True)
class UsuarioResumen:
    """Datos mínimos de un usuario que otros módulos necesitan conocer."""

    id: str
    nombre: str
    rol: str


class ContratoAuth(Protocol):
    """Interfaz que auth garantiza al resto del sistema."""

    async def listar_por_rol(self, rol: str) -> list[UsuarioResumen]:
        """Usuarios activos con el rol dado (ej: 'vendedor')."""
        ...


class AuthLocal:
    """Implementación local del contrato (mismo proceso, misma base)."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._dao = UsuarioDAO(sesion)

    async def listar_por_rol(self, rol: str) -> list[UsuarioResumen]:
        usuarios = await self._dao.listar_por_rol(rol)
        return [UsuarioResumen(id=u.id, nombre=u.nombre, rol=u.rol) for u in usuarios]
