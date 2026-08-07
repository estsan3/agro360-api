"""Capa API del módulo cartas de porte."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import Response as FastAPIResponse
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
    """Lista intenciones/CPE, opcionalmente filtradas por campaña."""
    return await CartasPorteService(sesion).listar(despacho_id)


@router.get(
    "/{carta_id}", response_model=CartaPorteResponse, operation_id="obtener_carta_porte"
)
async def obtener(carta_id: str, sesion: Sesion) -> CartaPorteResponse:
    """Detalle de una intención/CPE (incluye payload AFIP completo)."""
    return await CartasPorteService(sesion).obtener(carta_id)


@router.get(
    "/{carta_id}/documento",
    operation_id="descargar_documento_carta_porte",
    responses={200: {"content": {"application/pdf": {}}}},
)
async def descargar_documento(carta_id: str, sesion: Sesion) -> FastAPIResponse:
    """Descarga el PDF de una CPE procesada."""
    contenido, nombre = await CartasPorteService(sesion).obtener_documento(carta_id)
    return FastAPIResponse(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{nombre}"'},
    )


@router.post(
    "",
    response_model=CartaPorteResponse,
    status_code=201,
    operation_id="crear_intencion_carta_porte",
)
async def crear_intencion(
    datos: EmitirCartaPorteRequest, sesion: Sesion
) -> CartaPorteResponse:
    """Crea la intención de CPE con todo el payload requerido por AFIP (sin enviar)."""
    return await CartasPorteService(sesion).crear_intencion(datos)


@router.post(
    "/{carta_id}/reintentar",
    response_model=CartaPorteResponse,
    operation_id="reintentar_carta_porte",
)
async def reintentar(carta_id: str, sesion: Sesion) -> CartaPorteResponse:
    """Reconstruye el payload desde el despacho/viaje actual y deja la intención pendiente."""
    return await CartasPorteService(sesion).reintentar(carta_id)


@router.delete(
    "/{carta_id}",
    status_code=204,
    operation_id="eliminar_carta_porte",
)
async def eliminar(carta_id: str, sesion: Sesion) -> Response:
    """Elimina una intención pendiente o en error (no procesadas)."""
    await CartasPorteService(sesion).eliminar(carta_id)
    return Response(status_code=204)
