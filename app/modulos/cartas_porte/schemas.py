"""DTOs del módulo cartas de porte."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

EstadoCPE = Literal["pendiente", "error", "procesada", "autorizada", "anulada"]
TipoCPE = Literal[74, 274]


class EmitirCartaPorteRequest(BaseModel):
    """Crea una intención de CPE con el payload AFIP completo (sin enviar aún)."""

    despacho_id: str
    viaje_id: str


class CartaPorteResponse(BaseModel):
    id: str
    despacho_id: str
    viaje_id: str
    tipo_cpe: int
    nro_carta_porte: str | None = None
    nro_ctg: str | None = None
    estado: EstadoCPE
    material: str
    origen: str
    destino: str
    dominio: str
    toneladas: float
    payload_afip: dict[str, Any] = Field(default_factory=dict)
    intentos: int = 0
    error_detalle: str
    # True si hay PDF para visualizar/descargar (no se envía el binario en el listado).
    tiene_documento: bool = False
    creada_en: datetime
    actualizada_en: datetime | None = None

    model_config = {"from_attributes": True}
