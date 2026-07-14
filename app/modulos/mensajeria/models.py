"""Modelos ORM del módulo mensajería. Prefijo de tabla: `mensajeria_`."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _nuevo_id() -> str:
    return str(uuid.uuid4())


def _ahora() -> datetime:
    return datetime.now(UTC)


class Conversacion(Base):
    """Hilo de chat entre el equipo admin y un chofer (por chofer/patente)."""

    __tablename__ = "mensajeria_conversacion"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    # Referencia débil al chofer de catálogos + copias para mostrar.
    chofer_id: Mapped[str] = mapped_column(String(36), index=True)
    chofer_nombre: Mapped[str] = mapped_column(String(120))
    dominio: Mapped[str] = mapped_column(String(10))
    # Referencia débil al viaje que originó el chat (para el contexto del front).
    despacho_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    viaje_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Copias del recorrido para mostrar sin consultar despachos.
    origen: Mapped[str] = mapped_column(String(200), default="")
    destino: Mapped[str] = mapped_column(String(200), default="")
    # Mensajes del chofer que el admin todavía no leyó.
    no_leidos: Mapped[int] = mapped_column(Integer, default=0)

    mensajes: Mapped[list["Mensaje"]] = relationship(
        back_populates="conversacion",
        cascade="all, delete-orphan",
        order_by="Mensaje.fecha",
        lazy="selectin",
    )


class Mensaje(Base):
    """Mensaje individual dentro de una conversación."""

    __tablename__ = "mensajeria_mensaje"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    conversacion_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("mensajeria_conversacion.id")
    )
    # Quién escribió: "admin" | "chofer" | "sistema" (avisos automáticos).
    autor: Mapped[str] = mapped_column(String(10))
    texto: Mapped[str] = mapped_column(Text)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)
    # Si el admin ya lo leyó (los del admin nacen leídos).
    leido: Mapped[bool] = mapped_column(Boolean, default=False)

    conversacion: Mapped[Conversacion] = relationship(back_populates="mensajes")
