"""API ABM de transportistas (contrato del front /transportistas)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.core.dependencias import obtener_usuario_actual, requerir_rol
from app.modulos.catalogos.schemas_abm import (
    CambiarActivoAbm,
    GuardarCamionAbm,
    GuardarChoferAbm,
    GuardarTransportistaAbm,
    TransportistaAbm,
    TransportistaDetalleAbm,
)
from app.modulos.catalogos.service_abm import CatalogosAbmService

router = APIRouter(
    prefix="/transportistas",
    tags=["Transportistas"],
    dependencies=[Depends(obtener_usuario_actual)],
)

Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]


@router.get("", response_model=list[TransportistaAbm], operation_id="listar_transportistas_abm")
async def listar_transportistas_abm(
    sesion: Sesion,
    filtro: str = Query(default="activos"),
    busqueda: str = Query(default=""),
) -> list[TransportistaAbm]:
    """Lista empresas de transporte para la pantalla admin."""
    return await CatalogosAbmService(sesion).listar_transportistas(filtro, busqueda)


@router.get(
    "/{transportista_id}",
    response_model=TransportistaDetalleAbm,
    operation_id="obtener_transportista_abm",
)
async def obtener_transportista_abm(
    transportista_id: str, sesion: Sesion
) -> TransportistaDetalleAbm:
    """Detalle con flota y choferes."""
    return await CatalogosAbmService(sesion).obtener_transportista(transportista_id)


@router.post(
    "",
    response_model=TransportistaDetalleAbm,
    status_code=201,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="crear_transportista_abm",
)
async def crear_transportista_abm(
    datos: GuardarTransportistaAbm, sesion: Sesion
) -> TransportistaDetalleAbm:
    return await CatalogosAbmService(sesion).crear_transportista(datos)


@router.put(
    "/{transportista_id}",
    response_model=TransportistaDetalleAbm,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="actualizar_transportista_abm",
)
async def actualizar_transportista_abm(
    transportista_id: str, datos: GuardarTransportistaAbm, sesion: Sesion
) -> TransportistaDetalleAbm:
    return await CatalogosAbmService(sesion).actualizar_transportista(transportista_id, datos)


@router.patch(
    "/{transportista_id}/activo",
    response_model=TransportistaDetalleAbm,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="cambiar_activo_transportista_abm",
)
async def cambiar_activo_transportista_abm(
    transportista_id: str, datos: CambiarActivoAbm, sesion: Sesion
) -> TransportistaDetalleAbm:
    return await CatalogosAbmService(sesion).cambiar_activo_transportista(
        transportista_id, datos
    )


@router.delete(
    "/{transportista_id}",
    status_code=204,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="eliminar_transportista_abm",
)
async def eliminar_transportista_abm(transportista_id: str, sesion: Sesion) -> None:
    await CatalogosAbmService(sesion).eliminar_transportista(transportista_id)


@router.post(
    "/{transportista_id}/choferes",
    response_model=TransportistaDetalleAbm,
    status_code=201,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="crear_chofer_transportista_abm",
)
async def crear_chofer_transportista_abm(
    transportista_id: str, datos: GuardarChoferAbm, sesion: Sesion
) -> TransportistaDetalleAbm:
    return await CatalogosAbmService(sesion).crear_chofer(transportista_id, datos)


@router.put(
    "/{transportista_id}/choferes/{chofer_id}",
    response_model=TransportistaDetalleAbm,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="actualizar_chofer_transportista_abm",
)
async def actualizar_chofer_transportista_abm(
    transportista_id: str,
    chofer_id: str,
    datos: GuardarChoferAbm,
    sesion: Sesion,
) -> TransportistaDetalleAbm:
    return await CatalogosAbmService(sesion).actualizar_chofer(
        transportista_id, chofer_id, datos
    )


@router.patch(
    "/{transportista_id}/choferes/{chofer_id}/activo",
    response_model=TransportistaDetalleAbm,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="cambiar_activo_chofer_transportista_abm",
)
async def cambiar_activo_chofer_transportista_abm(
    transportista_id: str,
    chofer_id: str,
    datos: CambiarActivoAbm,
    sesion: Sesion,
) -> TransportistaDetalleAbm:
    return await CatalogosAbmService(sesion).cambiar_activo_chofer(
        transportista_id, chofer_id, datos
    )


@router.delete(
    "/{transportista_id}/choferes/{chofer_id}",
    response_model=TransportistaDetalleAbm,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="eliminar_chofer_transportista_abm",
)
async def eliminar_chofer_transportista_abm(
    transportista_id: str, chofer_id: str, sesion: Sesion
) -> TransportistaDetalleAbm:
    return await CatalogosAbmService(sesion).eliminar_chofer(transportista_id, chofer_id)


@router.post(
    "/{transportista_id}/camiones",
    response_model=TransportistaDetalleAbm,
    status_code=201,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="crear_camion_transportista_abm",
)
async def crear_camion_transportista_abm(
    transportista_id: str, datos: GuardarCamionAbm, sesion: Sesion
) -> TransportistaDetalleAbm:
    return await CatalogosAbmService(sesion).crear_camion(transportista_id, datos)


@router.put(
    "/{transportista_id}/camiones/{camion_id}",
    response_model=TransportistaDetalleAbm,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="actualizar_camion_transportista_abm",
)
async def actualizar_camion_transportista_abm(
    transportista_id: str,
    camion_id: str,
    datos: GuardarCamionAbm,
    sesion: Sesion,
) -> TransportistaDetalleAbm:
    return await CatalogosAbmService(sesion).actualizar_camion(
        transportista_id, camion_id, datos
    )


@router.patch(
    "/{transportista_id}/camiones/{camion_id}/activo",
    response_model=TransportistaDetalleAbm,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="cambiar_activo_camion_transportista_abm",
)
async def cambiar_activo_camion_transportista_abm(
    transportista_id: str,
    camion_id: str,
    datos: CambiarActivoAbm,
    sesion: Sesion,
) -> TransportistaDetalleAbm:
    return await CatalogosAbmService(sesion).cambiar_activo_camion(
        transportista_id, camion_id, datos
    )


@router.delete(
    "/{transportista_id}/camiones/{camion_id}",
    response_model=TransportistaDetalleAbm,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="eliminar_camion_transportista_abm",
)
async def eliminar_camion_transportista_abm(
    transportista_id: str, camion_id: str, sesion: Sesion
) -> TransportistaDetalleAbm:
    return await CatalogosAbmService(sesion).eliminar_camion(transportista_id, camion_id)
