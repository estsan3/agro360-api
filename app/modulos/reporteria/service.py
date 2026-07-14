"""Capa SERVICE del módulo reportería.

Reportería es un módulo de solo lectura que COMPONE datos de otros
módulos a través de sus contratos públicos (despachos) y services
(parámetros). No tiene DAO ni BO propios porque no posee datos.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modulos.despachos.contrato import ContratoDespachos, DespachosLocal
from app.modulos.parametros.service import ParametrosService
from app.modulos.reporteria.schemas import KpisResponse


class ReporteriaService:
    """Casos de uso de métricas y KPIs."""

    def __init__(
        self,
        sesion: AsyncSession,
        despachos: ContratoDespachos | None = None,
    ) -> None:
        self._despachos = despachos or DespachosLocal(sesion)
        self._parametros = ParametrosService(sesion)

    async def obtener_kpis(self) -> KpisResponse:
        """Combina métricas de despachos con la valorización de parámetros."""
        metricas = await self._despachos.calcular_metricas()
        negocio = await self._parametros.obtener_negocio()

        avance = (
            metricas.toneladas_completadas / metricas.toneladas_totales * 100
            if metricas.toneladas_totales > 0
            else 0.0
        )
        return KpisResponse(
            campanias_activas=metricas.campanias_activas,
            viajes_totales=metricas.viajes_totales,
            viajes_completados=metricas.viajes_completados,
            viajes_en_curso=metricas.viajes_en_curso,
            viajes_retrasados=metricas.viajes_retrasados,
            toneladas_totales=metricas.toneladas_totales,
            toneladas_completadas=metricas.toneladas_completadas,
            avance_porcentaje=round(avance, 2),
            valor_transportado=round(
                metricas.toneladas_completadas * negocio.precio_por_tonelada, 2
            ),
            moneda=negocio.moneda,
        )
