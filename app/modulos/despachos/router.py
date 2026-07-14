"""Capa API del módulo despachos."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.core.dependencias import obtener_usuario_actual
from app.modulos.despachos.schemas import (
    ActualizarViajeRequest,
    CrearDespachoRequest,
    CrearViajeRequest,
    DespachoResponse,
)
from app.modulos.despachos.service import DespachosService

router = APIRouter(
    prefix="/despachos",
    tags=["Despachos"],
    dependencies=[Depends(obtener_usuario_actual)],
)

Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]


@router.get("", response_model=list[DespachoResponse], operation_id="listar_despachos")
async def listar(
    sesion: Sesion,
    estado: Annotated[str | None, Query(pattern="^(borrador|activo)$")] = None,
) -> list[DespachoResponse]:
    """Lista las campañas de despacho, opcionalmente filtradas por estado."""
    return await DespachosService(sesion).listar(estado)


@router.get("/{despacho_id}", response_model=DespachoResponse, operation_id="obtener_despacho")
async def obtener(despacho_id: str, sesion: Sesion) -> DespachoResponse:
    """Devuelve una campaña con todos sus viajes."""
    return await DespachosService(sesion).obtener(despacho_id)


@router.post("", response_model=DespachoResponse, status_code=201, operation_id="crear_despacho")
async def crear(datos: CrearDespachoRequest, sesion: Sesion) -> DespachoResponse:
    """Crea una campaña. Con `activar=true` queda operativa en un solo paso."""
    return await DespachosService(sesion).crear(datos)


@router.post(
    "/{despacho_id}/activar", response_model=DespachoResponse, operation_id="activar_despacho"
)
async def activar(despacho_id: str, sesion: Sesion) -> DespachoResponse:
    """Activa una campaña en borrador (requiere al menos un viaje)."""
    return await DespachosService(sesion).activar(despacho_id)


@router.delete("/{despacho_id}", status_code=204, operation_id="eliminar_despacho")
async def eliminar(despacho_id: str, sesion: Sesion) -> None:
    """Elimina una campaña en borrador. Las activas no se pueden eliminar."""
    await DespachosService(sesion).eliminar(despacho_id)


@router.post(
    "/{despacho_id}/viajes",
    response_model=DespachoResponse,
    status_code=201,
    operation_id="agregar_viaje",
)
async def agregar_viaje(
    despacho_id: str, datos: CrearViajeRequest, sesion: Sesion
) -> DespachoResponse:
    """Agrega un viaje a una campaña existente."""
    return await DespachosService(sesion).agregar_viaje(despacho_id, datos)


@router.patch(
    "/{despacho_id}/viajes/{viaje_id}",
    response_model=DespachoResponse,
    operation_id="actualizar_viaje",
)
async def actualizar_viaje(
    despacho_id: str, viaje_id: str, datos: ActualizarViajeRequest, sesion: Sesion
) -> DespachoResponse:
    """Actualiza un viaje: asignar chofer, cambiar estado, progreso u observaciones."""
    return await DespachosService(sesion).actualizar_viaje(despacho_id, viaje_id, datos)
