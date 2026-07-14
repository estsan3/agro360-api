"""Modelos ORM del módulo cartas de porte. Prefijo de tabla: `cpe_`."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _nuevo_id() -> str:
    return str(uuid.uuid4())


def _ahora() -> datetime:
    return datetime.now(UTC)


class CartaPorte(Base):
    """Registro local de una CPE emitida (o intentada) ante ARCA/AFIP."""

    __tablename__ = "cpe_carta_porte"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)

    # Referencias débiles al viaje que respalda esta carta de porte.
    despacho_id: Mapped[str] = mapped_column(String(36), index=True)
    viaje_id: Mapped[str] = mapped_column(String(36), index=True)

    # Datos devueltos por AFIP al autorizar.
    nro_carta_porte: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # CTG: Código de Trazabilidad de Granos.
    nro_ctg: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Estados locales: "pendiente" | "autorizada" | "rechazada" | "anulada".
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")

    # Snapshot de los datos con los que se pidió la autorización.
    material: Mapped[str] = mapped_column(String(60))
    origen: Mapped[str] = mapped_column(String(200))
    destino: Mapped[str] = mapped_column(String(200))
    dominio: Mapped[str] = mapped_column(String(10))
    toneladas: Mapped[float] = mapped_column(Float)

    # Detalle del error si AFIP rechazó la solicitud.
    error_detalle: Mapped[str] = mapped_column(Text, default="")

    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)
