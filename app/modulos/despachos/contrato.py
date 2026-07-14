"""Contrato público del módulo despachos.

Lo consumen reportería (métricas) y cartas de porte (datos del viaje).
Al extraer despachos como microservicio, se implementa este mismo
Protocol con un cliente HTTP.
"""

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.modulos.despachos.dao import DespachoDAO


@dataclass(frozen=True)
class ViajeResumen:
    """Datos de un viaje que otros módulos necesitan (ej: para la carta de porte)."""

    id: str
    despacho_id: str
    chofer_id: str | None
    chofer_nombre: str
    dominio: str
    destino: str
    toneladas: float
    estado: str
    material: str
    origen: str


@dataclass(frozen=True)
class MetricasDespachos:
    """Números agregados para reportería / dashboard."""

    campanias_activas: int
    viajes_totales: int
    viajes_completados: int
    viajes_en_curso: int
    viajes_retrasados: int
    toneladas_totales: float
    toneladas_completadas: float


class ContratoDespachos(Protocol):
    """Interfaz que despachos garantiza al resto del sistema."""

    async def obtener_viaje(self, despacho_id: str, viaje_id: str) -> ViajeResumen | None: ...

    async def calcular_metricas(self) -> MetricasDespachos: ...


class DespachosLocal:
    """Implementación local del contrato (mismo proceso, misma base)."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._dao = DespachoDAO(sesion)

    async def obtener_viaje(self, despacho_id: str, viaje_id: str) -> ViajeResumen | None:
        viaje = await self._dao.buscar_viaje(despacho_id, viaje_id)
        if viaje is None:
            return None
        despacho = await self._dao.buscar_por_id(despacho_id)
        assert despacho is not None  # El viaje pertenece a la campaña.
        return ViajeResumen(
            id=viaje.id,
            despacho_id=despacho.id,
            chofer_id=viaje.chofer_id,
            chofer_nombre=viaje.chofer_nombre,
            dominio=viaje.dominio,
            destino=viaje.destino,
            toneladas=viaje.toneladas,
            estado=viaje.estado,
            material=despacho.material,
            origen=despacho.origen,
        )

    async def calcular_metricas(self) -> MetricasDespachos:
        """Agrega métricas recorriendo las campañas activas."""
        despachos = await self._dao.listar(estado="activo")
        viajes = [v for d in despachos for v in d.viajes]
        completados = [v for v in viajes if v.estado == "completado"]
        return MetricasDespachos(
            campanias_activas=len(despachos),
            viajes_totales=len(viajes),
            viajes_completados=len(completados),
            viajes_en_curso=sum(1 for v in viajes if v.estado == "en_viaje"),
            viajes_retrasados=sum(1 for v in viajes if v.estado == "retrasado"),
            toneladas_totales=sum(v.toneladas for v in viajes),
            toneladas_completadas=sum(v.toneladas for v in completados),
        )
