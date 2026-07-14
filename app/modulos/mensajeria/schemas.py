"""DTOs del módulo mensajería.

La forma de `ConversacionResponse` es el contrato que consume el front:
incluye el contexto del viaje (origen, destino, estado) además del hilo.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EstadoViajeChat = Literal["pendiente", "en_viaje", "retrasado", "completado"]


class MensajeResponse(BaseModel):
    id: str
    autor: Literal["admin", "chofer", "sistema"]
    texto: str
    fecha: datetime
    leido: bool = False

    model_config = {"from_attributes": True}


class ConversacionResponse(BaseModel):
    """Conversación con su contexto de viaje y el historial de mensajes."""

    id: str
    # El front consume el nombre del chofer en el campo `chofer`.
    chofer: str
    dominio: str
    viaje_id: str = ""
    origen: str = ""
    destino: str = ""
    estado_viaje: EstadoViajeChat = "pendiente"
    # Sin app mobile todavía, el chofer nunca figura en línea.
    en_linea: bool = False
    no_leidos: int
    mensajes: list[MensajeResponse] = []


class EnviarMensajeRequest(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)
