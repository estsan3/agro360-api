"""Configuración central de la aplicación.

Todas las variables se leen del entorno (o de un archivo `.env`) con el
prefijo `AGRO360_`. Ver `.env.example` en la raíz del repo.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Raíz del repo (app/core/config.py → parents[2] = agro360-api/).
_RAIZ_REPO = Path(__file__).resolve().parents[2]
_DB_SQLITE_DEFAULT = _RAIZ_REPO / "data" / "agro360.db"


class Configuracion(BaseSettings):
    """Variables de configuración tipadas y validadas por Pydantic."""

    model_config = SettingsConfigDict(
        env_prefix="AGRO360_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Entorno de ejecución: dev | test | prod
    entorno: str = "dev"

    # URL de conexión SQLAlchemy (async). SQLite en path absoluto en dev
    # (evita bases distintas según el cwd de uvicorn).
    database_url: str = f"sqlite+aiosqlite:///{_DB_SQLITE_DEFAULT}"

    # Seguridad / JWT
    jwt_secreto: str = "cambiar-este-secreto-en-produccion"
    jwt_algoritmo: str = "HS256"
    jwt_expiracion_minutos: int = 480

    # Orígenes permitidos para CORS, separados por coma.
    cors_origins: str = "http://localhost:4200"

    # Sembrar datos de demo al iniciar si la base está vacía (solo dev).
    seed_al_iniciar: bool = True

    # Exponer la API como servidor MCP para agentes de IA.
    mcp_habilitado: bool = False

    @property
    def cors_origins_lista(self) -> list[str]:
        """Devuelve los orígenes CORS como lista limpia."""
        return [origen.strip() for origen in self.cors_origins.split(",") if origen.strip()]

    @property
    def es_produccion(self) -> bool:
        return self.entorno == "prod"


@lru_cache
def obtener_configuracion() -> Configuracion:
    """Instancia única de configuración (cacheada para todo el proceso)."""
    return Configuracion()
