"""DTOs del módulo reportería."""

from pydantic import BaseModel


class KpisResponse(BaseModel):
    """KPIs del dashboard de gestión operativa."""

    campanias_activas: int
    viajes_totales: int
    viajes_completados: int
    viajes_en_curso: int
    viajes_retrasados: int
    toneladas_totales: float
    toneladas_completadas: float
    # Porcentaje de avance global: toneladas completadas / totales.
    avance_porcentaje: float
    # Valorización según precio por tonelada configurado en parámetros.
    valor_transportado: float
    moneda: str
