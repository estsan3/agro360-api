"""Suscripciones de lista de espera a eventos de despachos."""

from app.core.database import fabrica_sesiones
from app.core.eventos import EventoDominio, bus_eventos
from app.modulos.lista_espera.service import ListaEsperaService


async def _al_completar_viaje(evento: EventoDominio) -> None:
    """Reencola al fondo la unidad que había salido de la lista por asignación."""
    viaje_id = evento.datos.get("viaje_id")
    if not viaje_id:
        return
    async with fabrica_sesiones() as sesion:
        await ListaEsperaService(sesion).reencolar_al_completar(viaje_id)


def registrar_suscripciones() -> None:
    bus_eventos.suscribir("despachos.viaje.completado", _al_completar_viaje)
