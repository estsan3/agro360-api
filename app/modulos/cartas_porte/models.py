"""Modelos ORM del módulo cartas de porte. Prefijo de tabla: `cpe_`."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _nuevo_id() -> str:
    return str(uuid.uuid4())


def _ahora() -> datetime:
    return datetime.now(UTC)


class CartaPorte(Base):
    """Intención / registro local de una CPE (payload completo para ARCA/AFIP).

    Estados:
    - pendiente: payload armado, listo para enviar a homologación/producción
    - error: último intento de envío falló
    - procesada: CPE generada (demo o respuesta ARCA) con PDF disponible
    - autorizada: alias histórico de procesada (compatibilidad)
    - anulada: anulada ante ARCA / localmente
    """

    __tablename__ = "cpe_carta_porte"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)

    despacho_id: Mapped[str] = mapped_column(String(36), index=True)
    viaje_id: Mapped[str] = mapped_column(String(36), index=True)

    # 74 = automotor | 274 = flete corto
    tipo_cpe: Mapped[int] = mapped_column(Integer, default=74)

    nro_carta_porte: Mapped[str | None] = mapped_column(String(30), nullable=True)
    nro_ctg: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # pendiente | error | procesada | autorizada | anulada
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")

    # Snapshot para listados sin abrir el JSON.
    material: Mapped[str] = mapped_column(String(60))
    origen: Mapped[str] = mapped_column(String(200))
    destino: Mapped[str] = mapped_column(String(200))
    dominio: Mapped[str] = mapped_column(String(10))
    toneladas: Mapped[float] = mapped_column(Float)

    # Payload completo WSCPE (autorizarCPEAutomotor) listo para enviar.
    payload_afip: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # PDF de la constancia (base64). Solo cuando estado = procesada/autorizada.
    pdf_base64: Mapped[str | None] = mapped_column(Text, nullable=True)

    intentos: Mapped[int] = mapped_column(Integer, default=0)
    error_detalle: Mapped[str] = mapped_column(Text, default="")

    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)
    actualizada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_ahora, onupdate=_ahora
    )
