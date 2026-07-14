"""DTOs del módulo parámetros: dan forma tipada al almacén clave/valor."""

from typing import Literal

from pydantic import BaseModel, Field


class ParametrosNegocio(BaseModel):
    """Parámetros comerciales que usa el front en gestión y reportería."""

    precio_por_tonelada: float = Field(gt=0)
    moneda: Literal["ARS", "USD"]


class PreferenciasNotificacion(BaseModel):
    """Qué avisos quiere recibir el equipo admin."""

    viaje_retrasado: bool
    viaje_completado: bool
    mensaje_chofer: bool
