"""Modelos ORM del módulo catálogos. Prefijo de tabla: `catalogos_`."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String
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

    # Un productor tiene N campos; se borran en cascada con él.
    campos: Mapped[list["Campo"]] = relationship(
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

    productor: Mapped[Productor] = relationship(back_populates="campos")


class Material(Base):
    """Grano a transportar (Soja, Maíz, Girasol, Trigo, ...)."""

    __tablename__ = "catalogos_material"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)
    # Código de grano según tabla de ARCA/AFIP (para la carta de porte).
    codigo_grano_afip: Mapped[int | None] = mapped_column(nullable=True)


class Chofer(Base):
    """Conductor del camión. En este backoffice solo es dato de catálogo."""

    __tablename__ = "catalogos_chofer"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    nombre: Mapped[str] = mapped_column(String(120))
    # Dominio (patente) del camión habitual del chofer.
    dominio: Mapped[str] = mapped_column(String(10))
    # Modelo del camión (ej: "Scania R450"); dato informativo para el front.
    modelo: Mapped[str] = mapped_column(String(80), default="")
    cuit: Mapped[str | None] = mapped_column(String(13), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Transportista(Base):
    """Empresa de transporte (flota + choferes)."""

    __tablename__ = "catalogos_transportista"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    cuit: Mapped[str | None] = mapped_column(String(13), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    camiones: Mapped[list["Camion"]] = relationship(
        back_populates="transportista",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Camion(Base):
    """Camión de la flota de un transportista."""

    __tablename__ = "catalogos_camion"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    dominio: Mapped[str] = mapped_column(String(10), unique=True)
    modelo: Mapped[str] = mapped_column(String(80), default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    transportista_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("catalogos_transportista.id")
    )

    transportista: Mapped[Transportista] = relationship(back_populates="camiones")
