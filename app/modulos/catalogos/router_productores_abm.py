"""API ABM de productores (contrato del front /productores)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.core.dependencias import obtener_usuario_actual, requerir_rol
from app.modulos.catalogos.schemas_abm import (
    CambiarActivoAbm,
    GuardarCampoAbm,
    GuardarProductorAbm,
    GuardarResponsableAbm,
    ProductorAbm,
    ProductorDetalleAbm,
    VendedorOptionAbm,
)
from app.modulos.catalogos.service_abm import CatalogosAbmService

router = APIRouter(
    prefix="/productores",
    tags=["Productores"],
    dependencies=[Depends(obtener_usuario_actual)],
)

Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]


@router.get("/vendedores", response_model=list[VendedorOptionAbm], operation_id="listar_vendedores_abm")
async def listar_vendedores_abm(sesion: Sesion) -> list[VendedorOptionAbm]:
    return await CatalogosAbmService(sesion).listar_vendedores()


@router.get("", response_model=list[ProductorAbm], operation_id="listar_productores_abm")
async def listar_productores_abm(
    sesion: Sesion,
    filtro: str = Query(default="activos"),
    busqueda: str = Query(default=""),
) -> list[ProductorAbm]:
    return await CatalogosAbmService(sesion).listar_productores(filtro, busqueda)


@router.get(
    "/{productor_id}",
    response_model=ProductorDetalleAbm,
    operation_id="obtener_productor_abm",
)
async def obtener_productor_abm(productor_id: str, sesion: Sesion) -> ProductorDetalleAbm:
    return await CatalogosAbmService(sesion).obtener_productor(productor_id)


@router.post(
    "",
    response_model=ProductorDetalleAbm,
    status_code=201,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="crear_productor_abm",
)
async def crear_productor_abm(
    datos: GuardarProductorAbm, sesion: Sesion
) -> ProductorDetalleAbm:
    return await CatalogosAbmService(sesion).crear_productor(datos)


@router.put(
    "/{productor_id}",
    response_model=ProductorDetalleAbm,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="actualizar_productor_abm",
)
async def actualizar_productor_abm(
    productor_id: str, datos: GuardarProductorAbm, sesion: Sesion
) -> ProductorDetalleAbm:
    return await CatalogosAbmService(sesion).actualizar_productor(productor_id, datos)


@router.patch(
    "/{productor_id}/activo",
    response_model=ProductorDetalleAbm,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="cambiar_activo_productor_abm",
)
async def cambiar_activo_productor_abm(
    productor_id: str, datos: CambiarActivoAbm, sesion: Sesion
) -> ProductorDetalleAbm:
    return await CatalogosAbmService(sesion).cambiar_activo_productor(productor_id, datos)


@router.delete(
    "/{productor_id}",
    status_code=204,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="eliminar_productor_abm",
)
async def eliminar_productor_abm(productor_id: str, sesion: Sesion) -> None:
    await CatalogosAbmService(sesion).eliminar_productor(productor_id)


@router.post(
    "/{productor_id}/responsables",
    response_model=ProductorDetalleAbm,
    status_code=201,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="crear_responsable_abm",
)
async def crear_responsable_abm(
    productor_id: str, datos: GuardarResponsableAbm, sesion: Sesion
) -> ProductorDetalleAbm:
    return await CatalogosAbmService(sesion).crear_responsable(productor_id, datos)


@router.put(
    "/{productor_id}/responsables/{responsable_id}",
    response_model=ProductorDetalleAbm,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="actualizar_responsable_abm",
)
async def actualizar_responsable_abm(
    productor_id: str,
    responsable_id: str,
    datos: GuardarResponsableAbm,
    sesion: Sesion,
) -> ProductorDetalleAbm:
    return await CatalogosAbmService(sesion).actualizar_responsable(
        productor_id, responsable_id, datos
    )


@router.patch(
    "/{productor_id}/responsables/{responsable_id}/activo",
    response_model=ProductorDetalleAbm,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="cambiar_activo_responsable_abm",
)
async def cambiar_activo_responsable_abm(
    productor_id: str,
    responsable_id: str,
    datos: CambiarActivoAbm,
    sesion: Sesion,
) -> ProductorDetalleAbm:
    return await CatalogosAbmService(sesion).cambiar_activo_responsable(
        productor_id, responsable_id, datos
    )


@router.delete(
    "/{productor_id}/responsables/{responsable_id}",
    response_model=ProductorDetalleAbm,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="eliminar_responsable_abm",
)
async def eliminar_responsable_abm(
    productor_id: str, responsable_id: str, sesion: Sesion
) -> ProductorDetalleAbm:
    return await CatalogosAbmService(sesion).eliminar_responsable(productor_id, responsable_id)


@router.post(
    "/{productor_id}/campos",
    response_model=ProductorDetalleAbm,
    status_code=201,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="crear_campo_abm",
)
async def crear_campo_abm(
    productor_id: str, datos: GuardarCampoAbm, sesion: Sesion
) -> ProductorDetalleAbm:
    return await CatalogosAbmService(sesion).crear_campo(productor_id, datos)


@router.put(
    "/{productor_id}/campos/{campo_id}",
    response_model=ProductorDetalleAbm,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="actualizar_campo_abm",
)
async def actualizar_campo_abm(
    productor_id: str, campo_id: str, datos: GuardarCampoAbm, sesion: Sesion
) -> ProductorDetalleAbm:
    return await CatalogosAbmService(sesion).actualizar_campo(productor_id, campo_id, datos)


@router.patch(
    "/{productor_id}/campos/{campo_id}/activo",
    response_model=ProductorDetalleAbm,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="cambiar_activo_campo_abm",
)
async def cambiar_activo_campo_abm(
    productor_id: str, campo_id: str, datos: CambiarActivoAbm, sesion: Sesion
) -> ProductorDetalleAbm:
    return await CatalogosAbmService(sesion).cambiar_activo_campo(
        productor_id, campo_id, datos
    )


@router.delete(
    "/{productor_id}/campos/{campo_id}",
    response_model=ProductorDetalleAbm,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="eliminar_campo_abm",
)
async def eliminar_campo_abm(
    productor_id: str, campo_id: str, sesion: Sesion
) -> ProductorDetalleAbm:
    return await CatalogosAbmService(sesion).eliminar_campo(productor_id, campo_id)
