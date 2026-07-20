"""Capa API del módulo liquidaciones."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.core.dependencias import obtener_usuario_actual, requerir_rol
from app.modulos.liquidaciones.schemas import (
    ActualizarMovimientoRequest,
    CrearFleteRequest,
    CrearMovimientoManualRequest,
    CuentaResumenItem,
    MovimientoResponse,
    ParametrosLiquidacion,
    ResumenCuentaResponse,
)
from app.modulos.liquidaciones.service import LiquidacionesService

router = APIRouter(
    prefix="/liquidaciones",
    tags=["Liquidaciones"],
    dependencies=[Depends(obtener_usuario_actual)],
)

Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]


@router.get(
    "/parametros",
    response_model=ParametrosLiquidacion,
    operation_id="obtener_parametros_liquidacion",
)
async def obtener_parametros(sesion: Sesion) -> ParametrosLiquidacion:
    return await LiquidacionesService(sesion).obtener_parametros()


@router.put(
    "/parametros",
    response_model=ParametrosLiquidacion,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="guardar_parametros_liquidacion",
)
async def guardar_parametros(
    datos: ParametrosLiquidacion, sesion: Sesion
) -> ParametrosLiquidacion:
    return await LiquidacionesService(sesion).guardar_parametros(datos)


@router.get(
    "/cuentas",
    response_model=list[CuentaResumenItem],
    operation_id="listar_cuentas_corrientes",
)
async def listar_cuentas(sesion: Sesion) -> list[CuentaResumenItem]:
    return await LiquidacionesService(sesion).listar_cuentas()


@router.get(
    "/cuentas/{transportista_id}",
    response_model=ResumenCuentaResponse,
    operation_id="obtener_resumen_cuenta",
)
async def obtener_resumen(
    transportista_id: str,
    sesion: Sesion,
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
) -> ResumenCuentaResponse:
    return await LiquidacionesService(sesion).listar_resumen(
        transportista_id, desde=desde, hasta=hasta
    )


@router.post(
    "/fletes",
    response_model=list[MovimientoResponse],
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="crear_flete_ctacte",
)
async def crear_flete(
    datos: CrearFleteRequest, sesion: Sesion
) -> list[MovimientoResponse]:
    """
    Carga un flete y genera automáticamente:
    Haber: flete + IVA flete (a favor del transportista).
    Debe: comisión + IVA comisión + Imp. Ley 25.413 (cargo transportadora).
    """
    return await LiquidacionesService(sesion).registrar_flete(datos)


@router.post(
    "/movimientos",
    response_model=MovimientoResponse,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="crear_movimiento_ctacte",
)
async def crear_movimiento(
    datos: CrearMovimientoManualRequest, sesion: Sesion
) -> MovimientoResponse:
    return await LiquidacionesService(sesion).crear_movimiento_manual(datos)


@router.put(
    "/movimientos/{movimiento_id}",
    response_model=MovimientoResponse,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="actualizar_movimiento_ctacte",
)
async def actualizar_movimiento(
    movimiento_id: str, datos: ActualizarMovimientoRequest, sesion: Sesion
) -> MovimientoResponse:
    return await LiquidacionesService(sesion).actualizar_movimiento(movimiento_id, datos)


@router.delete(
    "/movimientos/{movimiento_id}",
    status_code=204,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="eliminar_movimiento_ctacte",
)
async def eliminar_movimiento(movimiento_id: str, sesion: Sesion) -> None:
    await LiquidacionesService(sesion).eliminar_movimiento(movimiento_id)
