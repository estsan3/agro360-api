"""Adaptador SIMULADO del proveedor de CPE.

Genera números ficticios con el formato real, para poder desarrollar el
front y probar el flujo completo sin certificado digital ni conexión a
los servidores de ARCA/AFIP.
"""

import random

from app.modulos.cartas_porte.puerto import ProveedorCPE, ResultadoCPE, SolicitudCPE


class AdaptadorSimulado(ProveedorCPE):
    """Autoriza siempre, salvo datos evidentemente inválidos."""

    async def autorizar_cpe_automotor(self, solicitud: SolicitudCPE) -> ResultadoCPE:
        # Simulamos el rechazo típico de AFIP por datos incompletos.
        if solicitud.dominio in ("", "-"):
            return ResultadoCPE(
                autorizada=False,
                error="El viaje no tiene dominio (patente) asignado",
            )
        if solicitud.toneladas <= 0:
            return ResultadoCPE(autorizada=False, error="Toneladas inválidas")

        # Formato similar al real: nro de carta de porte y CTG numéricos.
        return ResultadoCPE(
            autorizada=True,
            nro_carta_porte=f"{random.randint(10_000_000_000, 99_999_999_999)}",
            nro_ctg=f"{random.randint(10_000_000, 99_999_999)}",
        )

    async def anular_cpe(self, nro_carta_porte: str) -> ResultadoCPE:
        return ResultadoCPE(autorizada=True, nro_carta_porte=nro_carta_porte)
