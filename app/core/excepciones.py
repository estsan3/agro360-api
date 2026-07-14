"""Excepciones de negocio y su traducción a respuestas HTTP.

Las capas service/bo/dao lanzan estas excepciones sin conocer HTTP;
un handler global (registrado en `main.py`) las convierte en respuestas
JSON con el formato de error unificado de la API:

    { "error": { "codigo": "...", "mensaje": "..." } }
"""

from fastapi import Request
from fastapi.responses import JSONResponse


class ErrorDeNegocio(Exception):
    """Base de todos los errores de negocio de la aplicación."""

    codigo = "error_negocio"
    http_status = 400

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class RecursoNoEncontrado(ErrorDeNegocio):
    """La entidad solicitada no existe."""

    codigo = "no_encontrado"
    http_status = 404


class ReglaDeNegocioViolada(ErrorDeNegocio):
    """La operación viola una regla del dominio (ej: activar despacho sin viajes)."""

    codigo = "regla_violada"
    http_status = 422


class NoAutenticado(ErrorDeNegocio):
    """Credenciales inválidas o token ausente/expirado."""

    codigo = "no_autenticado"
    http_status = 401


class NoAutorizado(ErrorDeNegocio):
    """El usuario está autenticado pero no tiene permisos para la operación."""

    codigo = "no_autorizado"
    http_status = 403


async def manejar_error_de_negocio(_request: Request, exc: ErrorDeNegocio) -> JSONResponse:
    """Handler global: convierte un ErrorDeNegocio en la respuesta JSON unificada."""
    return JSONResponse(
        status_code=exc.http_status,
        content={"error": {"codigo": exc.codigo, "mensaje": exc.mensaje}},
    )
