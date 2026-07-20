"""Modelos ORM del módulo liquidaciones. Prefijo: `liquidaciones_`."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _nuevo_id() -> str:
    return str(uuid.uuid4())


class MovimientoCtacte(Base):
    """Renglón de la cuenta corriente de un transportista."""

    __tablename__ = "liquidaciones_movimiento"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    transportista_id: Mapped[str] = mapped_column(String(36), index=True)
    fecha: Mapped[date] = mapped_column(Date)
    concepto: Mapped[str] = mapped_column(String(40))
    comprobante: Mapped[str] = mapped_column(String(40), default="")
    detalle: Mapped[str] = mapped_column(String(240), default="")
    dador_viaje: Mapped[str] = mapped_column(String(120), default="")
    toneladas: Mapped[float | None] = mapped_column(Float, nullable=True)
    tarifa: Mapped[float | None] = mapped_column(Float, nullable=True)
    debe: Mapped[float] = mapped_column(Float, default=0.0)
    haber: Mapped[float] = mapped_column(Float, default=0.0)
    viaje_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    despacho_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ParametroLiquidacion(Base):
    """Parámetros clave/valor propios del módulo (tarifas y alícuotas)."""

    __tablename__ = "liquidaciones_parametro"

    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[str] = mapped_column(String(200))
