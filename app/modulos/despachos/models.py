"""Modelos ORM del módulo despachos. Prefijo de tabla: `despachos_`.

Referencias a otros módulos (productor, campo, chofer) se guardan como
IDs "débiles" (sin ForeignKey entre módulos): la integridad se valida en
la capa service a través del contrato de catálogos. Esto permite mover
cada módulo a su propia base de datos sin romper claves foráneas.
"""

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
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
    observaciones: Mapped[str] = mapped_column(Text, default="")

    # Estados: "borrador" | "activo" | "cerrado".
    estado: Mapped[str] = mapped_column(String(20), default="borrador")

    # Oferta comercial de la campaña (editables en borrador / búsqueda).
    dador_viaje: Mapped[str] = mapped_column(String(80), default="")
    tarifa_llena: Mapped[bool] = mapped_column(Boolean, default=False)
    tarifa_por_tn: Mapped[float | None] = mapped_column(Float, nullable=True)
    distancia_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    # "ahora" | "manana" | "fecha"
    cuando: Mapped[str] = mapped_column(String(20), default="ahora")
    cuando_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)

    viajes: Mapped[list["Viaje"]] = relationship(
        back_populates="despacho", cascade="all, delete-orphan", lazy="selectin"
    )


class TarifaNacional(Base):
    """Tramo de tarifa FADEEAC orientativa ($/tn por distancia)."""

    __tablename__ = "despachos_tarifa_nacional"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    km_desde: Mapped[float] = mapped_column(Float)
    km_hasta: Mapped[float] = mapped_column(Float)
    precio_por_tn: Mapped[float] = mapped_column(Float)
    vigencia: Mapped[str] = mapped_column(String(40), default="2026-03")


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

    # Estados: borrador | en_busqueda_transportistas | pendiente | en_viaje | ...
    estado: Mapped[str] = mapped_column(String(40), default="pendiente")
    # Avance del viaje: 0 a 100.
    progreso: Mapped[int] = mapped_column(Integer, default=0)
    observaciones: Mapped[str] = mapped_column(Text, default="")

    despacho: Mapped[Despacho] = relationship(back_populates="viajes")
