"""Puerto (interfaz) hacia el proveedor de Cartas de Porte Electrónicas.

Patrón puertos y adaptadores: el service del módulo depende de esta
interfaz, nunca del SDK concreto. Así se puede desarrollar y testear sin
certificado de ARCA, y cambiar de librería (cliente SOAP propio, etc.)
sin tocar el negocio.
"""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SolicitudCPE:
    """Pedido de autorización: payload WSCPE ya validado + nro de orden."""

    payload: dict[str, Any]
    nro_orden: int


@dataclass(frozen=True)
class ResultadoCPE:
    """Respuesta normalizada del proveedor, sea real o simulado."""

    autorizada: bool
    nro_carta_porte: str | None = None
    nro_ctg: str | None = None
    error: str = ""
    pdf_base64: str | None = None


class ProveedorCPE(Protocol):
    """Contrato que debe cumplir cualquier adaptador de CPE."""

    async def autorizar_cpe_automotor(self, solicitud: SolicitudCPE) -> ResultadoCPE:
        """Solicita la autorización de una carta de porte automotor (74/274)."""
        ...

    async def anular_cpe(
        self, *, tipo_cpe: int, sucursal: int, nro_orden: int
    ) -> ResultadoCPE:
        """Anula una carta de porte previamente autorizada."""
        ...
