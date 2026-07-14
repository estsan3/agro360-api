"""Capa DAO del módulo auth: acceso a datos, sin lógica de negocio."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modulos.auth.models import Usuario


class UsuarioDAO:
    """Operaciones de persistencia sobre la tabla `auth_usuario`."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def buscar_por_email(self, email: str) -> Usuario | None:
        """Busca un usuario por email (único). Devuelve None si no existe."""
        resultado = await self._sesion.execute(
            select(Usuario).where(Usuario.email == email)
        )
        return resultado.scalar_one_or_none()

    async def buscar_por_id(self, usuario_id: str) -> Usuario | None:
        return await self._sesion.get(Usuario, usuario_id)

    async def listar(self) -> list[Usuario]:
        resultado = await self._sesion.execute(select(Usuario).order_by(Usuario.nombre))
        return list(resultado.scalars())

    async def guardar(self, usuario: Usuario) -> Usuario:
        """Agrega el usuario a la sesión. El commit lo hace la capa service."""
        self._sesion.add(usuario)
        await self._sesion.flush()
        return usuario

    async def contar(self) -> int:
        """Cantidad total de usuarios (usado por el seed inicial)."""
        resultado = await self._sesion.execute(select(Usuario))
        return len(list(resultado.scalars()))
