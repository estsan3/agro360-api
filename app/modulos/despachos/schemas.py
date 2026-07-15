"""DTOs del módulo despachos."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

EstadoDespacho = Literal["borrador", "activo", "cerrado"]
# "borrador": viaje de una campaña aún no enviada (editable/eliminable).
EstadoViaje = Literal["borrador", "pendiente", "en_viaje", "retrasado", "completado"]


class ViajeResponse(BaseModel):
    id: str
    chofer_id: str | None = None
    chofer_nombre: str
    dominio: str
    destino: str
    toneladas: float
    estado: EstadoViaje
    progreso: int
    observaciones: str

    model_config = {"from_attributes": True}


class DespachoResponse(BaseModel):
    id: str
    nombre: str
    productor_id: str
    campo_id: str
    origen: str
    entrada_campo: str
    material: str
    administrador_id: str
    vendedor_id: str
    fecha_inicio: date
    fecha_llegada_estimada: date
    observaciones: str = ""
    estado: EstadoDespacho
    viajes: list[ViajeResponse] = []

    model_config = {"from_attributes": True}


class CrearViajeRequest(BaseModel):
    """Datos de un viaje al crearlo dentro de una campaña."""

    chofer_id: str | None = None
    # Patente del camión para este viaje (puede diferir del dominio del catálogo).
    dominio: str | None = Field(default=None, max_length=10)
    destino: str = Field(min_length=2, max_length=200)
    toneladas: float = Field(gt=0, le=100, description="Toneladas del viaje (máx. 100)")
    observaciones: str = ""


class CrearDespachoRequest(BaseModel):
    """Alta o edición de una campaña.

    El front envía `estado`: "borrador" (guardar) o "activo" (enviar).
    """

    nombre: str = Field(min_length=2, max_length=120)
    productor_id: str
    campo_id: str
    origen: str = Field(min_length=2, max_length=200)
    entrada_campo: str = ""
    material: str
    administrador_id: str
    vendedor_id: str
    fecha_inicio: date
    fecha_llegada_estimada: date | None = None
    viajes: list[CrearViajeRequest] = []
    estado: EstadoDespacho = "borrador"


class ActualizarViajeRequest(BaseModel):
    """Actualización parcial de un viaje (asignación, estado, progreso)."""

    chofer_id: str | None = None
    estado: EstadoViaje | None = None
    progreso: int | None = Field(default=None, ge=0, le=100)
    observaciones: str | None = None


class ActualizarMetadatosDespachoRequest(BaseModel):
    """Ajuste acotado de una campaña activa (fechas y notas operativas)."""

    fecha_llegada_estimada: date
    observaciones: str = Field(default="", max_length=2000)


class DuplicarDespachoRequest(BaseModel):
    """Opcional: nombre de la copia; si no se envía se deriva del original."""

    nombre: str | None = Field(default=None, min_length=2, max_length=120)
