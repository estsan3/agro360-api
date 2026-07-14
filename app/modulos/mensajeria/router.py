"""Capa API del módulo mensajería."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.core.dependencias import obtener_usuario_actual
from app.modulos.mensajeria.schemas import (
    ConversacionResponse,
    EnviarMensajeRequest,
    MensajeResponse,
)
from app.modulos.mensajeria.service import MensajeriaService

# Sin prefijo de módulo: el front consume /conversaciones directo.
router = APIRouter(
    tags=["Mensajería"],
    dependencies=[Depends(obtener_usuario_actual)],
)

Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]


@router.get(
    "/conversaciones",
    response_model=list[ConversacionResponse],
    operation_id="listar_conversaciones",
)
async def listar_conversaciones(sesion: Sesion) -> list[ConversacionResponse]:
    """Lista las conversaciones completas (las no leídas primero)."""
    return await MensajeriaService(sesion).listar_conversaciones()


@router.get(
    "/conversaciones/{conversacion_id}",
    response_model=ConversacionResponse,
    operation_id="obtener_conversacion",
)
async def obtener_conversacion(conversacion_id: str, sesion: Sesion) -> ConversacionResponse:
    """Devuelve el hilo completo y marca sus mensajes como leídos."""
    return await MensajeriaService(sesion).obtener_conversacion(conversacion_id)


@router.post(
    "/conversaciones/{conversacion_id}/mensajes",
    response_model=MensajeResponse,
    status_code=201,
    operation_id="enviar_mensaje",
)
async def enviar_mensaje(
    conversacion_id: str, datos: EnviarMensajeRequest, sesion: Sesion
) -> MensajeResponse:
    """Envía un mensaje del admin al chofer y devuelve el mensaje creado."""
    return await MensajeriaService(sesion).enviar_mensaje(conversacion_id, datos)


@router.post(
    "/conversaciones/chofer/{chofer_id}",
    response_model=ConversacionResponse,
    status_code=201,
    operation_id="iniciar_conversacion",
)
async def iniciar_conversacion(chofer_id: str, sesion: Sesion) -> ConversacionResponse:
    """Crea (o devuelve si ya existe) la conversación con un chofer."""
    return await MensajeriaService(sesion).iniciar_conversacion(chofer_id)
