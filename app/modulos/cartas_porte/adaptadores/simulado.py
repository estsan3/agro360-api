"""Adaptador SIMULADO del proveedor de CPE.

Genera números ficticios con el formato real y un PDF demo, para poder
desarrollar el front y probar el flujo completo sin certificado digital.
"""

import random

from app.modulos.cartas_porte.documento import generar_pdf_cpe_demo
from app.modulos.cartas_porte.puerto import ProveedorCPE, ResultadoCPE, SolicitudCPE


class AdaptadorSimulado(ProveedorCPE):
    """Autoriza siempre, salvo datos evidentemente inválidos."""

    async def autorizar_cpe_automotor(self, solicitud: SolicitudCPE) -> ResultadoCPE:
        payload = solicitud.payload
        transporte = payload.get("transporte") or {}
        dominios = transporte.get("dominio") or []
        dominio = dominios[0] if dominios else ""
        if dominio in ("", "-"):
            return ResultadoCPE(
                autorizada=False,
                error="El viaje no tiene dominio (patente) asignado",
            )
        carga = payload.get("datos_carga") or {}
        neto = carga.get("peso_neto") or 0
        if float(neto) <= 0:
            return ResultadoCPE(autorizada=False, error="Toneladas inválidas")

        nro_carta = (
            f"{int(payload.get('tipo_cpe') or 74)}"
            f"{int(payload.get('sucursal') or 1):05d}"
            f"{solicitud.nro_orden:08d}"
        )
        nro_ctg = f"{random.randint(10_000_000, 99_999_999)}"
        meta = payload.get("_meta") or {}
        pdf = generar_pdf_cpe_demo(
            nro_carta_porte=nro_carta,
            nro_ctg=nro_ctg,
            tipo_cpe=int(payload.get("tipo_cpe") or 74),
            material=str(meta.get("material_nombre") or ""),
            origen=str(meta.get("origen_descripcion") or ""),
            destino=str(meta.get("destino_descripcion") or ""),
            dominio=str(dominio),
            toneladas=float(neto) / 1000.0,
            estado="procesada",
        )
        return ResultadoCPE(
            autorizada=True,
            nro_carta_porte=nro_carta,
            nro_ctg=nro_ctg,
            pdf_base64=pdf,
        )

    async def anular_cpe(
        self, *, tipo_cpe: int, sucursal: int, nro_orden: int
    ) -> ResultadoCPE:
        nro = f"{tipo_cpe}{sucursal:05d}{nro_orden:08d}"
        return ResultadoCPE(autorizada=True, nro_carta_porte=nro)
