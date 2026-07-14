"""Puerto (interfaz) hacia el proveedor de Cartas de Porte Electrónicas.

Patrón puertos y adaptadores: el service del módulo depende de esta
interfaz, nunca del SDK concreto. Así se puede desarrollar y testear sin
certificado de ARCA, y cambiar de librería (PyAfipWs, cliente SOAP
propio, etc.) sin tocar el negocio.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SolicitudCPE:
    """Datos mínimos para pedir la autorización de una CPE automotor."""

    material: str
    origen: str
    destino: str
    dominio: str
    toneladas: float
    # Código de grano según tabla ARCA/AFIP (viene del catálogo de materiales).
    codigo_grano_afip: int | None = None


@dataclass(frozen=True)
class ResultadoCPE:
    """Respuesta normalizada del proveedor, sea real o simulado."""

    autorizada: bool
    nro_carta_porte: str | None = None
    nro_ctg: str | None = None
    error: str = ""


class ProveedorCPE(Protocol):
    """Contrato que debe cumplir cualquier adaptador de CPE."""

    async def autorizar_cpe_automotor(self, solicitud: SolicitudCPE) -> ResultadoCPE:
        """Solicita la autorización de una carta de porte automotor."""
        ...

    async def anular_cpe(self, nro_carta_porte: str) -> ResultadoCPE:
        """Anula una carta de porte previamente autorizada."""
        ...
