"""DTOs del módulo despachos."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

EstadoDespacho = Literal["borrador", "activo", "cerrado"]
# "borrador": viaje de una campaña aún no enviada (editable/eliminable).
# "en_busqueda_transportistas": oferta enviada a empresas, aún sin chofer.
EstadoViaje = Literal[
    "borrador",
    "en_busqueda_transportistas",
    "pendiente",
    "en_viaje",
    "retrasado",
    "completado",
]
CuandoDespacho = Literal["ahora", "manana", "fecha"]


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
    dador_viaje: str = ""
    tarifa_llena: bool = False
    tarifa_por_tn: float | None = None
    distancia_km: float | None = None
    cuando: CuandoDespacho = "ahora"
    cuando_fecha: date | None = None
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
    dador_viaje: str = Field(default="", max_length=80)
    tarifa_llena: bool = False
    tarifa_por_tn: float | None = Field(default=None, gt=0)
    distancia_km: float | None = Field(default=None, gt=0)
    cuando: CuandoDespacho = "ahora"
    cuando_fecha: date | None = None

    @model_validator(mode="after")
    def validar_cuando_y_tarifa(self) -> "CrearDespachoRequest":
        if self.cuando == "fecha" and self.cuando_fecha is None:
            raise ValueError("Indicar fecha cuando 'cuando' es fecha")
        if self.tarifa_llena and self.distancia_km is None:
            raise ValueError("Tarifa llena requiere distancia_km")
        if not self.tarifa_llena and self.tarifa_por_tn is None and self.estado == "activo":
            # En activo conviene tener tarifa; en borrador puede quedar vacío.
            pass
        return self


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


class TarifaNacionalItem(BaseModel):
    km_desde: float = Field(ge=0)
    km_hasta: float = Field(gt=0)
    precio_por_tn: float = Field(gt=0)
    vigencia: str = Field(default="2026-03", max_length=40)

    @model_validator(mode="after")
    def validar_rango(self) -> "TarifaNacionalItem":
        if self.km_hasta < self.km_desde:
            raise ValueError("km_hasta debe ser >= km_desde")
        return self


class TarifasNacionalesRequest(BaseModel):
    tramos: list[TarifaNacionalItem] = Field(min_length=1)


class TarifaNacionalResponse(BaseModel):
    id: str
    km_desde: float
    km_hasta: float
    precio_por_tn: float
    vigencia: str

    model_config = {"from_attributes": True}


class ResolverTarifaRequest(BaseModel):
    distancia_km: float = Field(gt=0)


class ResolverTarifaResponse(BaseModel):
    distancia_km: float
    precio_por_tn: float
    vigencia: str


class BuscarTransportistasRequest(BaseModel):
    """Datos de la oferta cuando aún no hay viajes cargados en la campaña.

    Si la campaña no tiene viajes, se crea uno en `en_busqueda_transportistas`
    con destino y toneladas. Si ya hay viajes, se ignoran (se marcan los
    existentes).
    """

    destino: str | None = Field(default=None, min_length=2, max_length=200)
    toneladas: float | None = Field(default=None, gt=0, le=100)
