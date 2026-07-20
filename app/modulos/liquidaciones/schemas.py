"""DTOs del módulo liquidaciones."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ConceptoManual = Literal["gasoil", "transferencia", "cheque", "anticipo", "ajuste"]


class ParametrosLiquidacion(BaseModel):
    """Tarifas y alícuotas para liquidar fletes al transportista."""

    tarifa_flete_por_tn: float = Field(gt=0, description="Tarifa neta por tonelada")
    comision_porcentaje: float = Field(ge=0, le=100)
    iva_alicuota: float = Field(ge=0, le=100)
    ley_25413_porcentaje: float = Field(ge=0, le=100)
    nombre_transportadora: str = Field(
        default="Transportadora",
        min_length=1,
        max_length=120,
        description="Empresa que administra la cuenta (saldo a favor transportadora)",
    )


class MovimientoResponse(BaseModel):
    id: str
    transportista_id: str
    fecha: date
    concepto: str
    comprobante: str
    detalle: str
    dador_viaje: str
    toneladas: float | None
    tarifa: float | None
    debe: float
    haber: float
    saldo: float = 0.0
    viaje_id: str | None
    despacho_id: str | None
    creado_en: datetime

    model_config = {"from_attributes": True}


class ResumenCuentaResponse(BaseModel):
    transportista_id: str
    transportista_nombre: str
    desde: date | None
    hasta: date | None
    saldo_inicial: float
    saldo_final: float
    totales_debe: float
    totales_haber: float
    movimientos: list[MovimientoResponse]


class CrearMovimientoManualRequest(BaseModel):
    transportista_id: str
    concepto: ConceptoManual
    detalle: str = Field(min_length=1, max_length=240)
    debe: float = Field(ge=0, default=0)
    haber: float = Field(ge=0, default=0)
    fecha: date | None = None
    toneladas: float | None = Field(default=None, gt=0)
    dador_viaje: str = ""

    @model_validator(mode="after")
    def validar_debe_haber(self) -> "CrearMovimientoManualRequest":
        if (self.debe > 0) == (self.haber > 0):
            raise ValueError("Indicar exactamente un importe en debe o en haber")
        return self


class CrearFleteRequest(BaseModel):
    """Alta de flete: genera automáticamente IVA flete, comisión, IVA comisión e Imp. Ley."""

    transportista_id: str
    detalle: str = Field(min_length=1, max_length=240)
    toneladas: float = Field(gt=0)
    tarifa: float | None = Field(default=None, gt=0)
    dador_viaje: str = ""
    fecha: date | None = None
    viaje_id: str | None = None
    despacho_id: str | None = None


class ActualizarMovimientoRequest(BaseModel):
    """Edición de un renglón de cuenta corriente."""

    fecha: date
    detalle: str = Field(min_length=1, max_length=240)
    dador_viaje: str = ""
    comprobante: str = Field(default="", max_length=40)
    toneladas: float | None = Field(default=None, gt=0)
    tarifa: float | None = Field(default=None, gt=0)
    debe: float = Field(ge=0, default=0)
    haber: float = Field(ge=0, default=0)

    @model_validator(mode="after")
    def validar_debe_haber(self) -> "ActualizarMovimientoRequest":
        if (self.debe > 0) == (self.haber > 0):
            raise ValueError("Indicar exactamente un importe en debe o en haber")
        return self


class CuentaResumenItem(BaseModel):
    transportista_id: str
    transportista_nombre: str
    saldo_actual: float
    cantidad_movimientos: int
