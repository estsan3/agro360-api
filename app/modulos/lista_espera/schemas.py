"""DTOs del módulo lista de espera."""

from datetime import datetime

from pydantic import BaseModel, Field


class AnotarListaRequest(BaseModel):
    chofer_id: str
    camion_id: str
    empresa_id: str = "default"


class EntradaListaResponse(BaseModel):
    id: str
    empresa_id: str
    transportista_id: str
    camion_id: str
    chofer_id: str
    transportista_nombre: str
    chofer_nombre: str
    dominio: str
    capacidad_tn: float | None = None
    tipo_unidad: str
    estado: str
    anotado_en: datetime
    viaje_ofertado_id: str | None = None
    ofertado_en: datetime | None = None
    viaje_asignado_id: str | None = None

    model_config = {"from_attributes": True}


class OfertarSiguienteRequest(BaseModel):
    viaje_id: str
    toneladas: float = Field(gt=0)
    tipo_unidad: str | None = None
    empresa_id: str = "default"


class OfertaListaResponse(BaseModel):
    entrada: EntradaListaResponse | None
    mensaje: str


class ProcesarTimeoutsRequest(BaseModel):
    empresa_id: str = "default"
    timeout_minutos: int = Field(default=15, ge=1, le=1440)
