"""Modelos ORM del módulo despachos. Prefijo de tabla: `despachos_`.

Referencias a otros módulos (productor, campo, chofer) se guardan como
IDs "débiles" (sin ForeignKey entre módulos): la integridad se valida en
la capa service a través del contrato de catálogos. Esto permite mover
cada módulo a su propia base de datos sin romper claves foráneas.
"""

import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _nuevo_id() -> str:
    return str(uuid.uuid4())


class Despacho(Base):
    """Campaña de despacho: agrupa origen, material, fechas y N viajes."""

    __tablename__ = "despachos_despacho"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    nombre: Mapped[str] = mapped_column(String(120))

    # Referencias débiles a catálogos (ver docstring del módulo).
    productor_id: Mapped[str] = mapped_column(String(36))
    campo_id: Mapped[str] = mapped_column(String(36))
    administrador_id: Mapped[str] = mapped_column(String(36))
    vendedor_id: Mapped[str] = mapped_column(String(36))

    origen: Mapped[str] = mapped_column(String(200))
    # Descripción de la entrada al campo (puede incluir coordenadas).
    entrada_campo: Mapped[str] = mapped_column(String(200), default="")
    # Nombre del material (grano); se valida contra catálogos al crear.
    material: Mapped[str] = mapped_column(String(60))

    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_llegada_estimada: Mapped[date] = mapped_column(Date)

    # Estados: "borrador" (editable) | "activo" (operativo).
    estado: Mapped[str] = mapped_column(String(20), default="borrador")

    viajes: Mapped[list["Viaje"]] = relationship(
        back_populates="despacho", cascade="all, delete-orphan", lazy="selectin"
    )


class Viaje(Base):
    """Un traslado concreto en camión dentro de una campaña."""

    __tablename__ = "despachos_viaje"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    despacho_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("despachos_despacho.id")
    )

    # Chofer asignado (referencia débil a catálogos); None = sin asignar.
    chofer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Copias desnormalizadas para mostrar sin consultar catálogos.
    chofer_nombre: Mapped[str] = mapped_column(String(120), default="Sin asignar")
    dominio: Mapped[str] = mapped_column(String(10), default="-")

    destino: Mapped[str] = mapped_column(String(200))
    toneladas: Mapped[float] = mapped_column(Float)

    # Estados: "pendiente" | "en_viaje" | "retrasado" | "completado".
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")
    # Avance del viaje: 0 a 100.
    progreso: Mapped[int] = mapped_column(Integer, default=0)
    observaciones: Mapped[str] = mapped_column(Text, default="")

    despacho: Mapped[Despacho] = relationship(back_populates="viajes")
