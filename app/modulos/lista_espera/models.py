"""Modelos ORM del módulo lista de espera. Prefijo: `lista_espera_`."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _nuevo_id() -> str:
    return str(uuid.uuid4())


class EntradaLista(Base):
    """Unidad anotada en la lista de espera de una empresa logística."""

    __tablename__ = "lista_espera_entrada"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    # ID débil del operador logístico (tenant); hoy un solo valor "default".
    empresa_id: Mapped[str] = mapped_column(String(36), index=True, default="default")

    # Referencias débiles a catálogos (sin FK entre módulos).
    transportista_id: Mapped[str] = mapped_column(String(36))
    camion_id: Mapped[str] = mapped_column(String(36))
    chofer_id: Mapped[str] = mapped_column(String(36))

    # Copias para listar sin consultar catálogos.
    transportista_nombre: Mapped[str] = mapped_column(String(120), default="")
    chofer_nombre: Mapped[str] = mapped_column(String(120), default="")
    dominio: Mapped[str] = mapped_column(String(10), default="-")
    capacidad_tn: Mapped[float | None] = mapped_column(Float, nullable=True)
    tipo_unidad: Mapped[str] = mapped_column(String(40), default="tolva")

    # en_espera | ofertado | fuera
    estado: Mapped[str] = mapped_column(String(20), default="en_espera", index=True)
    anotado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    viaje_ofertado_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ofertado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    viaje_asignado_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
