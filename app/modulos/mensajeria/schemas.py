"""DTOs del módulo mensajería."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MensajeResponse(BaseModel):
    id: str
    autor: Literal["admin", "chofer", "sistema"]
    texto: str
    fecha: datetime

    model_config = {"from_attributes": True}


class ConversacionResumenResponse(BaseModel):
    """Item del listado de conversaciones (sin los mensajes)."""

    id: str
    chofer_id: str
    chofer_nombre: str
    dominio: str
    no_leidos: int

    model_config = {"from_attributes": True}


class ConversacionResponse(ConversacionResumenResponse):
    """Conversación completa con su historial de mensajes."""

    mensajes: list[MensajeResponse] = []


class EnviarMensajeRequest(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)
