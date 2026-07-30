"""Puerto de notificación WhatsApp (stub v1).

Cuando se integre WhatsApp Business, implementar este Protocol
con un adaptador real sin tocar el service de mensajería.
"""

from typing import Protocol


class NotificadorWhatsApp(Protocol):
    async def enviar(self, destinatario: str, texto: str) -> None: ...


class NotificadorWhatsAppStub:
    """No-op: deja el mensaje solo en la mensajería in-app."""

    async def enviar(self, destinatario: str, texto: str) -> None:
        return None
