"""Suscripciones de mensajería a eventos de dominio de otros módulos.

Mensajería NO importa el service de despachos: solo reacciona a los
eventos publicados en el bus. Si mañana despachos es un microservicio
que publica en RabbitMQ, este archivo pasa a ser el consumer del broker
con la misma lógica.
"""

from app.core.database import fabrica_sesiones
from app.core.eventos import EventoDominio, bus_eventos
from app.modulos.despachos.dao import DespachoDAO
from app.modulos.mensajeria.service import MensajeriaService


async def _al_cambiar_estado_viaje(evento: EventoDominio) -> None:
    """Inserta un aviso de sistema en el chat del chofer del viaje afectado.

    Abre su propia sesión: los manejadores de eventos corren fuera de la
    transacción del caso de uso que originó el evento.
    """
    async with fabrica_sesiones() as sesion:
        viaje = await DespachoDAO(sesion).buscar_viaje(
            evento.datos["despacho_id"], evento.datos["viaje_id"]
        )
        if viaje is None:
            return

        if evento.nombre == "despachos.viaje.completado":
            texto = f"El viaje a {viaje.destino} fue marcado como completado."
        else:
            texto = f"El viaje a {viaje.destino} está retrasado."

        await MensajeriaService(sesion).notificar_evento_viaje(viaje.chofer_id, texto)


def registrar_suscripciones() -> None:
    """Registra los manejadores en el bus. Se llama una vez desde main.py."""
    bus_eventos.suscribir("despachos.viaje.completado", _al_cambiar_estado_viaje)
    bus_eventos.suscribir("despachos.viaje.retrasado", _al_cambiar_estado_viaje)
