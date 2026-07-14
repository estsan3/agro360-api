"""Dependencias FastAPI transversales (autenticación y autorización).

El usuario autenticado se reconstruye SOLO desde los claims del JWT
(sin ir a la base de datos), de modo que cualquier módulo —incluso
extraído como microservicio— pueda autorizar requests con solo conocer
el secreto de firma.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.excepciones import NoAutenticado, NoAutorizado
from app.core.seguridad import decodificar_token

# `auto_error=False` para devolver nuestro error unificado en vez del 403 default.
_esquema_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class UsuarioActual:
    """Identidad del usuario autenticado, tomada de los claims del token."""

    id: str
    email: str
    rol: str


def obtener_usuario_actual(
    credenciales: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_esquema_bearer)
    ],
) -> UsuarioActual:
    """Dependencia: exige un Bearer token válido y devuelve la identidad."""
    if credenciales is None:
        raise NoAutenticado("Falta el token de autenticación")

    claims = decodificar_token(credenciales.credentials)
    return UsuarioActual(
        id=claims.get("sub", ""),
        email=claims.get("email", ""),
        rol=claims.get("rol", ""),
    )


def requerir_rol(*roles_permitidos: str):
    """Fábrica de dependencias: exige que el usuario tenga alguno de los roles.

    Uso:
        @router.post("/", dependencies=[Depends(requerir_rol("administrador"))])
    """

    def _verificar(
        usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)],
    ) -> UsuarioActual:
        if usuario.rol not in roles_permitidos:
            raise NoAutorizado("No tenés permisos para realizar esta operación")
        return usuario

    return _verificar
