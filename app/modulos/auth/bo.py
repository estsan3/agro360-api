"""Capa BO (Business Object) del módulo auth: reglas de negocio puras.

Los BO no tocan la base de datos ni HTTP: reciben entidades/valores,
validan reglas y lanzan excepciones de negocio. Esto los hace triviales
de testear de forma unitaria.
"""

from app.core.excepciones import NoAutenticado, ReglaDeNegocioViolada
from app.core.seguridad import verificar_password
from app.modulos.auth.models import Usuario

ROLES_VALIDOS = {"administrador", "vendedor"}


class UsuarioBO:
    """Reglas de negocio sobre usuarios y credenciales."""

    def validar_credenciales(self, usuario: Usuario | None, password: str) -> Usuario:
        """Verifica que el usuario exista y la contraseña coincida.

        Devuelve el mismo mensaje genérico en ambos fallos para no revelar
        si el email está registrado o no.
        """
        if usuario is None or not verificar_password(password, usuario.password_hash):
            raise NoAutenticado("Email o contraseña incorrectos")
        return usuario

    def validar_alta(self, email_ya_registrado: bool, rol: str) -> None:
        """Reglas para dar de alta un usuario nuevo."""
        if email_ya_registrado:
            raise ReglaDeNegocioViolada("Ya existe un usuario con ese email")
        if rol not in ROLES_VALIDOS:
            raise ReglaDeNegocioViolada(f"Rol inválido: {rol}")

    def validar_baja(self, es_el_mismo_usuario: bool, es_ultimo_administrador: bool) -> None:
        """Reglas para dar de baja un usuario."""
        if es_el_mismo_usuario:
            raise ReglaDeNegocioViolada("No podés darte de baja a vos mismo")
        if es_ultimo_administrador:
            raise ReglaDeNegocioViolada("No se puede eliminar al último administrador")
