"""Capa API del módulo lista de espera."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.core.dependencias import obtener_usuario_actual
from app.modulos.lista_espera.schemas import (
    AnotarListaRequest,
    EntradaListaResponse,
    OfertaListaResponse,
    OfertarSiguienteRequest,
    ProcesarTimeoutsRequest,
)
from app.modulos.lista_espera.service import ListaEsperaService

router = APIRouter(
    prefix="/lista-espera",
    tags=["Lista de espera"],
    dependencies=[Depends(obtener_usuario_actual)],
)

Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]


@router.get(
    "",
    response_model=list[EntradaListaResponse],
    operation_id="listar_lista_espera",
)
async def listar(
    sesion: Sesion,
    empresa_id: Annotated[str, Query()] = "default",
) -> list[EntradaListaResponse]:
    return await ListaEsperaService(sesion).listar(empresa_id)


@router.post(
    "",
    response_model=EntradaListaResponse,
    status_code=201,
    operation_id="anotar_lista_espera",
)
async def anotar(datos: AnotarListaRequest, sesion: Sesion) -> EntradaListaResponse:
    return await ListaEsperaService(sesion).anotar(datos)


@router.delete(
    "/{entrada_id}",
    status_code=204,
    operation_id="quitar_lista_espera",
)
async def quitar(entrada_id: str, sesion: Sesion) -> None:
    await ListaEsperaService(sesion).quitar(entrada_id)


@router.post(
    "/ofertar",
    response_model=OfertaListaResponse,
    operation_id="ofertar_siguiente_lista_espera",
)
async def ofertar(
    datos: OfertarSiguienteRequest, sesion: Sesion
) -> OfertaListaResponse:
    return await ListaEsperaService(sesion).ofertar_siguiente(datos)


@router.post(
    "/{entrada_id}/aceptar",
    response_model=EntradaListaResponse,
    operation_id="aceptar_oferta_lista_espera",
)
async def aceptar(
    entrada_id: str,
    sesion: Sesion,
    viaje_id: Annotated[str, Query()],
) -> EntradaListaResponse:
    return await ListaEsperaService(sesion).aceptar_oferta(entrada_id, viaje_id)


@router.post(
    "/{entrada_id}/rechazar",
    response_model=EntradaListaResponse,
    operation_id="rechazar_oferta_lista_espera",
)
async def rechazar(entrada_id: str, sesion: Sesion) -> EntradaListaResponse:
    return await ListaEsperaService(sesion).rechazar_oferta(entrada_id)


@router.post(
    "/procesar-timeouts",
    response_model=list[EntradaListaResponse],
    operation_id="procesar_timeouts_lista_espera",
)
async def procesar_timeouts(
    datos: ProcesarTimeoutsRequest, sesion: Sesion
) -> list[EntradaListaResponse]:
    return await ListaEsperaService(sesion).procesar_timeouts(
        datos.empresa_id, timeout_minutos=datos.timeout_minutos
    )
