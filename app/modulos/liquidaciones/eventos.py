"""Suscripciones de liquidaciones a eventos de despachos."""

from app.core.database import fabrica_sesiones
from app.core.eventos import EventoDominio, bus_eventos
from app.modulos.liquidaciones.service import LiquidacionesService


async def _al_completar_viaje(evento: EventoDominio) -> None:
    async with fabrica_sesiones() as sesion:
        await LiquidacionesService(sesion).registrar_viaje_completado(
            despacho_id=evento.datos["despacho_id"],
            viaje_id=evento.datos["viaje_id"],
        )


def registrar_suscripciones() -> None:
    bus_eventos.suscribir("despachos.viaje.completado", _al_completar_viaje)
