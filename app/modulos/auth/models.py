"""Modelos ORM del módulo auth. Prefijo de tabla: `auth_`."""

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _nuevo_id() -> str:
    """Genera un identificador único (UUID4 en texto, portable entre motores)."""
    return str(uuid.uuid4())


class Usuario(Base):
    """Usuario del backoffice (administrador o vendedor)."""

    __tablename__ = "auth_usuario"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_nuevo_id)
    nombre: Mapped[str] = mapped_column(String(120))
    dni: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    # Hash bcrypt; NUNCA se almacena la contraseña en texto plano.
    password_hash: Mapped[str] = mapped_column(String(100))
    # Rol de negocio: "administrador" | "vendedor".
    rol: Mapped[str] = mapped_column(String(20))
