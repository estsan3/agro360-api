"""Capa API del módulo cartas de porte."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.core.dependencias import obtener_usuario_actual
from app.modulos.cartas_porte.schemas import CartaPorteResponse, EmitirCartaPorteRequest
from app.modulos.cartas_porte.service import CartasPorteService

router = APIRouter(
    prefix="/cartas-porte",
    tags=["Cartas de Porte"],
    dependencies=[Depends(obtener_usuario_actual)],
)

Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]


@router.get("", response_model=list[CartaPorteResponse], operation_id="listar_cartas_porte")
async def listar(
    sesion: Sesion,
    despacho_id: Annotated[str | None, Query()] = None,
) -> list[CartaPorteResponse]:
    """Lista las cartas de porte emitidas, opcionalmente por campaña."""
    return await CartasPorteService(sesion).listar(despacho_id)


@router.get(
    "/{carta_id}", response_model=CartaPorteResponse, operation_id="obtener_carta_porte"
)
async def obtener(carta_id: str, sesion: Sesion) -> CartaPorteResponse:
    """Devuelve el detalle de una carta de porte."""
    return await CartasPorteService(sesion).obtener(carta_id)


@router.post(
    "", response_model=CartaPorteResponse, status_code=201, operation_id="emitir_carta_porte"
)
async def emitir(datos: EmitirCartaPorteRequest, sesion: Sesion) -> CartaPorteResponse:
    """Emite la CPE de un viaje ante ARCA/AFIP (o el simulador en dev)."""
    return await CartasPorteService(sesion).emitir(datos)


@router.post(
    "/{carta_id}/anular",
    response_model=CartaPorteResponse,
    operation_id="anular_carta_porte",
)
async def anular(carta_id: str, sesion: Sesion) -> CartaPorteResponse:
    """Anula una carta de porte autorizada."""
    return await CartasPorteService(sesion).anular(carta_id)
