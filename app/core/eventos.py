"""Bus de eventos de dominio (en memoria).

Los módulos se comunican de dos formas:

1. Sincrónica: llamando al *contrato* público de otro módulo (interfaz).
2. Asincrónica: publicando eventos de dominio en este bus, sin conocer
   quién los escucha.

Hoy el bus es en memoria (mismo proceso). Cuando los módulos se separen
en microservicios, esta clase se reemplaza por un adaptador a un broker
real (RabbitMQ, Redis Streams, etc.) manteniendo la misma interfaz
`publicar` / `suscribir`, por lo que los módulos no cambian.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EventoDominio:
    """Evento inmutable que describe algo que YA ocurrió en el dominio.

    El nombre sigue la convención `modulo.entidad.accion`,
    ej: `despachos.viaje.completado`.
    """

    nombre: str
    datos: dict[str, Any]
    ocurrido_en: datetime = field(default_factory=lambda: datetime.now(UTC))


# Un manejador es una corutina que recibe el evento y no devuelve nada.
ManejadorEvento = Callable[[EventoDominio], Awaitable[None]]


class BusEventos:
    """Bus publish/subscribe en memoria, con tolerancia a fallos por manejador."""

    def __init__(self) -> None:
        # Mapa nombre de evento -> lista de manejadores suscriptos.
        self._suscriptores: dict[str, list[ManejadorEvento]] = {}

    def suscribir(self, nombre_evento: str, manejador: ManejadorEvento) -> None:
        """Registra un manejador para un nombre de evento."""
        self._suscriptores.setdefault(nombre_evento, []).append(manejador)

    async def publicar(self, evento: EventoDominio) -> None:
        """Entrega el evento a todos los suscriptores.

        Un fallo en un manejador se registra pero no interrumpe al resto ni
        al flujo principal: los eventos son efectos secundarios, no parte
        de la transacción del caso de uso.
        """
        for manejador in self._suscriptores.get(evento.nombre, []):
            try:
                await manejador(evento)
            except Exception:
                logger.exception(
                    "Error en manejador del evento %s", evento.nombre
                )


# Instancia única del bus para todo el proceso.
bus_eventos = BusEventos()
