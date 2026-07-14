"""DTOs del módulo cartas de porte."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

EstadoCPE = Literal["pendiente", "autorizada", "rechazada", "anulada"]


class EmitirCartaPorteRequest(BaseModel):
    """Solicitud de emisión: la CPE se genera a partir de un viaje existente."""

    despacho_id: str
    viaje_id: str


class CartaPorteResponse(BaseModel):
    id: str
    despacho_id: str
    viaje_id: str
    nro_carta_porte: str | None = None
    nro_ctg: str | None = None
    estado: EstadoCPE
    material: str
    origen: str
    destino: str
    dominio: str
    toneladas: float
    error_detalle: str
    creada_en: datetime

    model_config = {"from_attributes": True}
