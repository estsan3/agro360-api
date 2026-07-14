"""Utilidades de seguridad: hashing de contraseñas y tokens JWT.

Módulo de infraestructura pura: no conoce usuarios ni roles del dominio,
solo firma/verifica tokens y hashea contraseñas.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import obtener_configuracion
from app.core.excepciones import NoAutenticado


def hashear_password(password: str) -> str:
    """Devuelve el hash bcrypt de una contraseña en texto plano."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password: str, hash_almacenado: str) -> bool:
    """Compara una contraseña en texto plano contra su hash almacenado."""
    return bcrypt.checkpw(password.encode("utf-8"), hash_almacenado.encode("utf-8"))


def crear_token_acceso(subject: str, datos_extra: dict[str, Any] | None = None) -> str:
    """Genera un JWT firmado.

    `subject` es el identificador del usuario (va en el claim `sub`);
    `datos_extra` permite agregar claims propios (ej: rol, email).
    """
    config = obtener_configuracion()
    expira = datetime.now(UTC) + timedelta(minutes=config.jwt_expiracion_minutos)
    payload: dict[str, Any] = {"sub": subject, "exp": expira, **(datos_extra or {})}
    return jwt.encode(payload, config.jwt_secreto, algorithm=config.jwt_algoritmo)


def decodificar_token(token: str) -> dict[str, Any]:
    """Valida firma y expiración de un JWT. Lanza NoAutenticado si es inválido."""
    config = obtener_configuracion()
    try:
        return jwt.decode(token, config.jwt_secreto, algorithms=[config.jwt_algoritmo])
    except jwt.ExpiredSignatureError as exc:
        raise NoAutenticado("El token expiró, iniciá sesión nuevamente") from exc
    except jwt.InvalidTokenError as exc:
        raise NoAutenticado("Token inválido") from exc
