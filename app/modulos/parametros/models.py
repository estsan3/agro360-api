"""Modelos ORM del módulo parámetros. Prefijo de tabla: `parametros_`.

Se modela como clave/valor tipado simple: alcanza para precio por
tonelada, moneda y flags de notificación, y no requiere migración por
cada parámetro nuevo.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Parametro(Base):
    """Un parámetro de configuración global del sistema."""

    __tablename__ = "parametros_parametro"

    # La clave es el identificador natural (ej: "precio_por_tonelada").
    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    # Valor serializado como texto; el tipo real lo define el schema Pydantic.
    valor: Mapped[str] = mapped_column(String(200))
