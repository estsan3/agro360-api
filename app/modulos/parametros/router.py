"""Capa API del módulo parámetros."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.core.dependencias import obtener_usuario_actual, requerir_rol
from app.modulos.parametros.schemas import ParametrosNegocio, PreferenciasNotificacion
from app.modulos.parametros.service import ParametrosService

# Sin prefijo de módulo: el front consume /parametros y /preferencias
# como recursos de primer nivel.
router = APIRouter(
    tags=["Parámetros"],
    dependencies=[Depends(obtener_usuario_actual)],
)

Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]


@router.get("/parametros", response_model=ParametrosNegocio, operation_id="obtener_parametros")
async def obtener_negocio(sesion: Sesion) -> ParametrosNegocio:
    """Devuelve los parámetros comerciales (precio por tonelada, moneda)."""
    return await ParametrosService(sesion).obtener_negocio()


@router.put(
    "/parametros",
    response_model=ParametrosNegocio,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="guardar_parametros",
)
async def guardar_negocio(datos: ParametrosNegocio, sesion: Sesion) -> ParametrosNegocio:
    """Actualiza los parámetros comerciales. Solo administradores."""
    return await ParametrosService(sesion).guardar_negocio(datos)


@router.get(
    "/preferencias",
    response_model=PreferenciasNotificacion,
    operation_id="obtener_preferencias",
)
async def obtener_preferencias(sesion: Sesion) -> PreferenciasNotificacion:
    """Devuelve las preferencias de notificación del equipo."""
    return await ParametrosService(sesion).obtener_preferencias()


@router.put(
    "/preferencias",
    response_model=PreferenciasNotificacion,
    operation_id="guardar_preferencias",
)
async def guardar_preferencias(
    datos: PreferenciasNotificacion, sesion: Sesion
) -> PreferenciasNotificacion:
    """Actualiza las preferencias de notificación."""
    return await ParametrosService(sesion).guardar_preferencias(datos)


@router.get(
    "/parametria/tipos-vehiculo",
    response_model=list[str],
    operation_id="listar_tipos_vehiculo",
)
async def listar_tipos_vehiculo() -> list[str]:
    """Tipos de vehículo para la UI de transportistas."""
    return ["Tractor", "Camión", "Semi-remolque", "Bitren", "Acoplado"]


@router.get(
    "/parametria/tipos-licencia",
    response_model=list[str],
    operation_id="listar_tipos_licencia",
)
async def listar_tipos_licencia() -> list[str]:
    """Tipos de licencia de conducir."""
    return ["B1", "B2", "C", "D1", "D2", "E1", "E2"]
