"""Fixtures compartidas de los tests.

Los tests de API usan una base SQLite en memoria y el ciclo de vida real
de la aplicación (tablas + suscripciones), pero sin seed de demo.
"""

import os

# Configuración de test ANTES de importar la app (config se cachea).
os.environ["AGRO360_DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["AGRO360_SEED_AL_INICIAR"] = "false"
os.environ["AGRO360_ENTORNO"] = "test"

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import fabrica_sesiones
from app.core.seguridad import hashear_password
from app.main import app
from app.modulos.auth.models import Usuario


@pytest.fixture
async def cliente():
    """Cliente HTTP contra la app, con el lifespan ejecutado (crea tablas)."""
    from asgi_lifespan import LifespanManager

    async with LifespanManager(app):
        transporte = ASGITransport(app=app)
        async with AsyncClient(transport=transporte, base_url="http://test") as http:
            yield http


@pytest.fixture
async def token_admin(cliente) -> str:
    """Crea (si no existe) un usuario administrador y devuelve su token.

    La base SQLite en memoria persiste durante toda la corrida, por eso
    el alta es idempotente.
    """
    async with fabrica_sesiones() as sesion:
        from app.modulos.auth.dao import UsuarioDAO

        if await UsuarioDAO(sesion).buscar_por_email("admin@test.com") is None:
            sesion.add(
                Usuario(
                    nombre="Admin Test",
                    dni="11111111",
                    email="admin@test.com",
                    password_hash=hashear_password("password123"),
                    rol="administrador",
                )
            )
            await sesion.commit()

    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "password123"},
    )
    return respuesta.json()["access_token"]


@pytest.fixture
def auth_headers(token_admin: str) -> dict[str, str]:
    """Headers con el Bearer token del admin de prueba."""
    return {"Authorization": f"Bearer {token_admin}"}
