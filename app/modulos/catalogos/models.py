"""Modelos ORM del módulo catálogos. Prefijo de tabla: `catalogos_`."""

import uuid
from typing import Any

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _nuevo_id() -> str:
    return str(uuid.uuid4())


class Productor(Base):
    """Dueño del campo / de la carga (ej: Agro SA). No es usuario de login."""

    __tablename__ = "catalogos_productor"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    cuit: Mapped[str | None] = mapped_column(String(13), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    # Campos extra de la UI ABM (email, notas, vendedor_id, etc.).
    datos_ui: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    campos: Mapped[list["Campo"]] = relationship(
        back_populates="productor", cascade="all, delete-orphan", lazy="selectin"
    )
    responsables: Mapped[list["ResponsableProductor"]] = relationship(
        back_populates="productor", cascade="all, delete-orphan", lazy="selectin"
    )


class Campo(Base):
    """Lugar físico de carga, siempre asociado a un productor."""

    __tablename__ = "catalogos_campo"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    nombre: Mapped[str] = mapped_column(String(120))
    productor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("catalogos_productor.id")
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    datos_ui: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    productor: Mapped[Productor] = relationship(back_populates="campos")
    puntos_entrada: Mapped[list["PuntoEntrada"]] = relationship(
        back_populates="campo", cascade="all, delete-orphan", lazy="selectin"
    )


class PuntoEntrada(Base):
    """Referencia geográfica para que el chofer llegue al acceso del campo."""

    __tablename__ = "catalogos_punto_entrada"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    campo_id: Mapped[str] = mapped_column(String(36), ForeignKey("catalogos_campo.id"))
    nombre: Mapped[str] = mapped_column(String(120), default="Entrada")
    orden: Mapped[int] = mapped_column(Integer, default=1)
    latitud: Mapped[float] = mapped_column(Float, default=0.0)
    longitud: Mapped[float] = mapped_column(Float, default=0.0)
    observacion: Mapped[str] = mapped_column(Text, default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    campo: Mapped[Campo] = relationship(back_populates="puntos_entrada")


class ResponsableProductor(Base):
    """Contacto operativo del productor en la UI ABM."""

    __tablename__ = "catalogos_responsable_productor"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    productor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("catalogos_productor.id")
    )
    nombre: Mapped[str] = mapped_column(String(80), default="")
    apellido: Mapped[str] = mapped_column(String(80), default="")
    telefono: Mapped[str] = mapped_column(String(40), default="")
    documento: Mapped[str] = mapped_column(String(20), default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    productor: Mapped[Productor] = relationship(back_populates="responsables")


class Material(Base):
    """Grano a transportar (Soja, Maíz, Girasol, Trigo, ...)."""

    __tablename__ = "catalogos_material"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)
    # Código de grano según tabla de ARCA/AFIP (para la carta de porte).
    codigo_grano_afip: Mapped[int | None] = mapped_column(nullable=True)


class Chofer(Base):
    """Conductor vinculado a una empresa de transporte."""

    __tablename__ = "catalogos_chofer"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    nombre: Mapped[str] = mapped_column(String(120))
    transportista_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("catalogos_transportista.id"), nullable=True
    )
    # Legacy: se mantiene nullable para datos viejos; la patente vive en Camion.
    dominio: Mapped[str | None] = mapped_column(String(10), nullable=True)
    modelo: Mapped[str | None] = mapped_column(String(80), nullable=True)
    cuit: Mapped[str | None] = mapped_column(String(13), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    camion_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("catalogos_camion.id"), nullable=True
    )
    datos_ui: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    transportista: Mapped["Transportista | None"] = relationship(
        back_populates="choferes", lazy="selectin"
    )


class Transportista(Base):
    """Empresa de transporte (flota + choferes)."""

    __tablename__ = "catalogos_transportista"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    cuit: Mapped[str | None] = mapped_column(String(13), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    datos_ui: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    camiones: Mapped[list["Camion"]] = relationship(
        back_populates="transportista",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    choferes: Mapped[list[Chofer]] = relationship(
        back_populates="transportista",
        lazy="selectin",
    )


class Camion(Base):
    """Camión de la flota de un transportista."""

    __tablename__ = "catalogos_camion"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    dominio: Mapped[str] = mapped_column(String(10), unique=True)
    modelo: Mapped[str] = mapped_column(String(80), default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    datos_ui: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    transportista_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("catalogos_transportista.id")
    )

    transportista: Mapped[Transportista] = relationship(back_populates="camiones")
