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
    "cancelado",
]
CuandoDespacho = Literal["ahora", "manana", "fecha"]
TipoAdjuntoViaje = Literal["ticket_gasoil", "cpe_escaneada", "otro"]


class ViajeAdjuntoResponse(BaseModel):
    id: str
    viaje_id: str
    tipo: TipoAdjuntoViaje
    nombre: str
    mime: str
    creado_en: str

    model_config = {"from_attributes": True}


class ViajeAdjuntoDetalleResponse(ViajeAdjuntoResponse):
    data_url: str


class SubirAdjuntoViajeRequest(BaseModel):
    tipo: TipoAdjuntoViaje
    nombre: str = Field(min_length=1, max_length=200)
    mime: str = Field(default="application/octet-stream", max_length=120)
    data_url: str = Field(min_length=1)


class ViajeResponse(BaseModel):
    id: str
    chofer_id: str | None = None
    chofer_nombre: str
    dominio: str
    destino: str
    toneladas: float
    cpe_destino_cuit: str | None = None
    cpe_destino_es_campo: bool | None = None
    cpe_destino_cod_provincia: int | None = None
    cpe_destino_cod_localidad: int | None = None
    cpe_destino_planta: int | None = None
    cpe_peso_bruto_kg: int | None = None
    cpe_peso_tara_kg: int | None = None
    cpe_codigo_turno: str | None = None
    cpe_dominio_acoplado: str | None = None
    checklist_gasoil: bool = False
    checklist_efectivo: bool = False
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
    cpe_habilitada: bool = False
    cpe_tipo: int | None = None
    cpe_sucursal: int | None = None
    cpe_cosecha: int | None = None
    cpe_cuit_solicitante: str | None = None
    cpe_origen_cod_provincia: int | None = None
    cpe_origen_cod_localidad: int | None = None
    cpe_origen_planta: int | None = None
    cpe_nro_renspa: str | None = None
    cpe_codigo_turno: str | None = None
    cpe_hora_partida: str | None = None
    cpe_corresponde_retiro_productor: bool = True
    cpe_es_solicitante_campo: bool = True
    cpe_destino_cuit: str | None = None
    cpe_destino_es_campo: bool = False
    cpe_destino_cod_provincia: int | None = None
    cpe_destino_cod_localidad: int | None = None
    cpe_destino_planta: int | None = None
    cpe_peso_tara_kg_default: int | None = None
    cpe_mercaderia_fumigada: bool = False
    cpe_cuit_pagador_flete: str | None = None
    cpe_cuit_intermediario_flete: str | None = None
    cpe_cuit_remitente_comercial_vp: str | None = None
    cpe_cuit_remitente_comercial_vs: str | None = None
    cpe_cuit_mercado_a_termino: str | None = None
    cpe_cuit_corredor_vp: str | None = None
    cpe_cuit_corredor_vs: str | None = None
    cpe_cuit_representante_entregador: str | None = None
    cpe_cuit_representante_recibidor: str | None = None
    cpe_cuit_remitente_comercial_vs2: str | None = None
    cpe_cuit_remitente_comercial_productor: str | None = None
    viajes: list[ViajeResponse] = []

    model_config = {"from_attributes": True}


class CrearViajeRequest(BaseModel):
    """Datos de un viaje al crearlo dentro de una campaña."""

    # Presente al editar para regenerar una intención CPE (preserva el id).
    id: str | None = None
    chofer_id: str | None = None
    # Patente del camión para este viaje (puede diferir del dominio del catálogo).
    dominio: str | None = Field(default=None, max_length=10)
    destino: str = Field(min_length=2, max_length=200)
    toneladas: float = Field(gt=0, le=100, description="Toneladas del viaje (máx. 100)")
    observaciones: str = ""
    cpe_destino_cuit: str | None = Field(default=None, max_length=13)
    cpe_destino_es_campo: bool | None = None
    cpe_destino_cod_provincia: int | None = Field(default=None, ge=1, le=99)
    cpe_destino_cod_localidad: int | None = Field(default=None, ge=1)
    cpe_destino_planta: int | None = Field(default=None, ge=1, le=999_999)
    cpe_peso_bruto_kg: int | None = Field(default=None, ge=1, le=88_000)
    cpe_peso_tara_kg: int | None = Field(default=None, ge=0, le=88_000)
    cpe_codigo_turno: str | None = Field(default=None, max_length=80)
    cpe_dominio_acoplado: str | None = Field(default=None, max_length=10)


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

    # Carta de porte (opcional; si cpe_habilitada, se validan campos mínimos).
    cpe_habilitada: bool = False
    cpe_tipo: int | None = Field(default=None, description="74 automotor | 274 flete corto")
    cpe_sucursal: int | None = Field(default=None, ge=1, le=99_999)
    cpe_cosecha: int | None = Field(default=None, ge=1000, le=9999)
    cpe_cuit_solicitante: str | None = Field(default=None, max_length=13)
    cpe_origen_cod_provincia: int | None = Field(default=None, ge=1, le=99)
    cpe_origen_cod_localidad: int | None = Field(default=None, ge=1)
    cpe_origen_planta: int | None = Field(default=None, ge=1, le=999_999)
    cpe_nro_renspa: str | None = Field(default=None, max_length=40)
    cpe_codigo_turno: str | None = Field(default=None, max_length=80)
    cpe_hora_partida: str | None = Field(
        default=None, max_length=5, description="Hora local HH:MM de partida"
    )
    cpe_corresponde_retiro_productor: bool = True
    cpe_es_solicitante_campo: bool = True
    cpe_destino_cuit: str | None = Field(default=None, max_length=13)
    cpe_destino_es_campo: bool = False
    cpe_destino_cod_provincia: int | None = Field(default=None, ge=1, le=99)
    cpe_destino_cod_localidad: int | None = Field(default=None, ge=1)
    cpe_destino_planta: int | None = Field(default=None, ge=1, le=999_999)
    cpe_peso_tara_kg_default: int | None = Field(default=None, ge=0, le=88_000)
    cpe_mercaderia_fumigada: bool = False
    cpe_cuit_pagador_flete: str | None = Field(default=None, max_length=13)
    cpe_cuit_intermediario_flete: str | None = Field(default=None, max_length=13)
    cpe_cuit_remitente_comercial_vp: str | None = Field(default=None, max_length=13)
    cpe_cuit_remitente_comercial_vs: str | None = Field(default=None, max_length=13)
    cpe_cuit_mercado_a_termino: str | None = Field(default=None, max_length=13)
    cpe_cuit_corredor_vp: str | None = Field(default=None, max_length=13)
    cpe_cuit_corredor_vs: str | None = Field(default=None, max_length=13)
    cpe_cuit_representante_entregador: str | None = Field(default=None, max_length=13)
    cpe_cuit_representante_recibidor: str | None = Field(default=None, max_length=13)
    cpe_cuit_remitente_comercial_vs2: str | None = Field(default=None, max_length=13)
    cpe_cuit_remitente_comercial_productor: str | None = Field(default=None, max_length=13)

    @model_validator(mode="after")
    def validar_cuando_y_tarifa(self) -> "CrearDespachoRequest":
        if self.cuando == "fecha" and self.cuando_fecha is None:
            raise ValueError("Indicar fecha cuando 'cuando' es fecha")
        if self.tarifa_llena and self.distancia_km is None:
            raise ValueError("Tarifa llena requiere distancia_km")
        if not self.tarifa_llena and self.tarifa_por_tn is None and self.estado == "activo":
            # En activo conviene tener tarifa; en borrador puede quedar vacío.
            pass
        if self.cpe_habilitada:
            if self.cpe_tipo not in (74, 274):
                raise ValueError("cpe_tipo debe ser 74 (automotor) o 274 (flete corto)")
            faltantes = [
                nombre
                for nombre, valor in (
                    ("cpe_sucursal", self.cpe_sucursal),
                    ("cpe_cosecha", self.cpe_cosecha),
                    ("cpe_origen_cod_provincia", self.cpe_origen_cod_provincia),
                    ("cpe_origen_cod_localidad", self.cpe_origen_cod_localidad),
                    ("cpe_destino_cuit", self.cpe_destino_cuit),
                    ("cpe_destino_cod_provincia", self.cpe_destino_cod_provincia),
                    ("cpe_destino_cod_localidad", self.cpe_destino_cod_localidad),
                )
                if valor is None or valor == ""
            ]
            if faltantes:
                raise ValueError(
                    "Con CPE habilitada faltan campos: " + ", ".join(faltantes)
                )
            if not self.cpe_destino_es_campo and self.cpe_destino_planta is None:
                raise ValueError(
                    "Destino a planta requiere cpe_destino_planta (o marcar destino a campo)"
                )
            if self.distancia_km is None:
                raise ValueError("CPE habilitada requiere distancia_km (km a recorrer)")
            if self.cpe_hora_partida:
                hora = self.cpe_hora_partida.strip()
                partes = hora.split(":")
                if (
                    len(partes) != 2
                    or not partes[0].isdigit()
                    or not partes[1].isdigit()
                    or not (0 <= int(partes[0]) <= 23)
                    or not (0 <= int(partes[1]) <= 59)
                ):
                    raise ValueError("cpe_hora_partida debe ser HH:MM (00:00 a 23:59)")
        return self


class ActualizarViajeRequest(BaseModel):
    """Actualización parcial de un viaje (asignación, estado, progreso)."""

    chofer_id: str | None = None
    estado: EstadoViaje | None = None
    progreso: int | None = Field(default=None, ge=0, le=100)
    observaciones: str | None = None


class IniciarViajeRequest(BaseModel):
    """Confirmación operativa previa a salir a ruta."""

    checklist_gasoil: bool = False
    checklist_efectivo: bool = False


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


class AsignarPorListaRequest(BaseModel):
    """Parámetros opcionales para asignación por flota propia / lista FIFO."""

    empresa_id: str = "default"
    tipo_unidad: str | None = Field(default=None, max_length=40)
