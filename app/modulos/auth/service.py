"""Capa SERVICE del módulo auth: casos de uso y límites transaccionales.

El service orquesta DAO + BO + infraestructura (tokens) y es el único
lugar donde se hace commit. Los routers solo lo invocan.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excepciones import RecursoNoEncontrado
from app.core.seguridad import crear_token_acceso, hashear_password
from app.modulos.auth.bo import UsuarioBO
from app.modulos.auth.dao import UsuarioDAO
from app.modulos.auth.models import Usuario
from app.modulos.auth.schemas import (
    CrearUsuarioRequest,
    LoginRequest,
    LoginResponse,
    UsuarioResponse,
)


class AuthService:
    """Casos de uso de autenticación y gestión de usuarios."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion
        self._dao = UsuarioDAO(sesion)
        self._bo = UsuarioBO()

    async def login(self, datos: LoginRequest) -> LoginResponse:
        """Valida credenciales y emite un JWT con la identidad del usuario."""
        usuario = await self._dao.buscar_por_email(datos.email)
        usuario = self._bo.validar_credenciales(usuario, datos.password)

        # Los claims extra (email, rol) permiten autorizar sin ir a la base.
        token = crear_token_acceso(
            subject=usuario.id,
            datos_extra={"email": usuario.email, "rol": usuario.rol},
        )
        return LoginResponse(
            access_token=token,
            usuario=UsuarioResponse.model_validate(usuario),
        )

    async def crear_usuario(self, datos: CrearUsuarioRequest) -> UsuarioResponse:
        """Alta de usuario del backoffice."""
        existente = await self._dao.buscar_por_email(datos.email)
        self._bo.validar_alta(email_ya_registrado=existente is not None, rol=datos.rol)

        usuario = Usuario(
            nombre=datos.nombre,
            dni=datos.dni,
            email=datos.email,
            password_hash=hashear_password(datos.password),
            rol=datos.rol,
        )
        await self._dao.guardar(usuario)
        await self._sesion.commit()
        return UsuarioResponse.model_validate(usuario)

    async def listar_usuarios(self) -> list[UsuarioResponse]:
        usuarios = await self._dao.listar()
        return [UsuarioResponse.model_validate(u) for u in usuarios]

    async def obtener_usuario(self, usuario_id: str) -> UsuarioResponse:
        usuario = await self._dao.buscar_por_id(usuario_id)
        if usuario is None:
            raise RecursoNoEncontrado("Usuario no encontrado")
        return UsuarioResponse.model_validate(usuario)
