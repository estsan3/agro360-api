"""Estructura del payload AFIP/ARCA para CPE automotor (tipo 74) y flete corto (274).

Este módulo es puro: arma y valida el JSON que luego se enviará a
`autorizarCPEAutomotor` (WSCPE). No habla con la red ni con la DB.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from app.core.excepciones import ReglaDeNegocioViolada

TipoCPEAutomotor = Literal[74, 274]

TIPOS_CPE_SOPORTADOS: frozenset[int] = frozenset({74, 274})


@dataclass(frozen=True)
class DatosParaPayloadCPE:
    """Inputs de negocio necesarios para armar el payload WSCPE automotor."""

    tipo_cpe: int
    sucursal: int
    cosecha: int
    cuit_solicitante: str

    # Origen
    origen_cod_provincia: int
    origen_cod_localidad: int
    origen_planta: int | None
    origen_latitud: float | None
    origen_longitud: float | None
    cuit_productor: str
    corresponde_retiro_productor: bool
    es_solicitante_campo: bool

    # Carga
    cod_grano: int
    peso_bruto_kg: int
    peso_tara_kg: int

    # Destino
    destino_cuit: str
    destino_es_campo: bool
    destino_cod_provincia: int
    destino_cod_localidad: int
    destino_planta: int | None

    # Transporte
    cuit_transportista: str
    dominio: str
    fecha_hora_partida: datetime
    km_recorrer: int
    cuit_chofer: str
    tarifa: float | None
    cuit_pagador_flete: str | None
    cuit_intermediario_flete: str | None
    mercaderia_fumigada: bool
    codigo_turno: str | None

    # Intervinientes opcionales
    cuit_remitente_comercial_venta_primaria: str | None = None
    cuit_remitente_comercial_venta_secundaria: str | None = None
    cuit_mercado_a_termino: str | None = None
    cuit_corredor_venta_primaria: str | None = None
    cuit_corredor_venta_secundaria: str | None = None
    cuit_representante_entregador: str | None = None
    cuit_representante_recibidor: str | None = None

    observaciones: str = ""

    # Metadatos locales (no van al SOAP, sí al JSON guardado)
    material_nombre: str = ""
    origen_descripcion: str = ""
    destino_descripcion: str = ""
    despacho_nombre: str = ""


def decimal_a_gms(valor: float) -> dict[str, float | int]:
    """Convierte lat/lng decimal a grados/minutos/segundos (formato AFIP)."""
    absoluto = abs(valor)
    grados = int(absoluto)
    minutos_f = (absoluto - grados) * 60
    minutos = int(minutos_f)
    segundos = round((minutos_f - minutos) * 60, 3)
    return {"grados": grados, "minutos": minutos, "segundos": segundos}


def _cuit_limpio(cuit: str | None, campo: str, *, obligatorio: bool = True) -> str | None:
    if cuit is None or not str(cuit).strip():
        if obligatorio:
            raise ReglaDeNegocioViolada(f"Falta {campo} para armar la carta de porte")
        return None
    digitos = "".join(ch for ch in str(cuit) if ch.isdigit())
    if len(digitos) != 11:
        raise ReglaDeNegocioViolada(f"{campo} inválido (debe tener 11 dígitos): {cuit}")
    return digitos


def validar_y_armar_payload(datos: DatosParaPayloadCPE) -> dict[str, Any]:
    """Valida datos obligatorios y devuelve el payload listo para persistir/enviar."""
    if datos.tipo_cpe not in TIPOS_CPE_SOPORTADOS:
        raise ReglaDeNegocioViolada(
            f"Tipo de CPE no soportado: {datos.tipo_cpe}. Usar 74 (automotor) o 274 (flete corto)"
        )
    if datos.sucursal < 1 or datos.sucursal > 99_999:
        raise ReglaDeNegocioViolada("Sucursal CPE inválida (1..99999)")
    if datos.cosecha < 1000 or datos.cosecha > 9999:
        raise ReglaDeNegocioViolada("Cosecha inválida (formato AAAA, ej. 2526)")
    if datos.cod_grano < 1:
        raise ReglaDeNegocioViolada("Código de grano AFIP inválido o ausente en el material")
    if datos.peso_bruto_kg <= 0 or datos.peso_bruto_kg > 88_000:
        raise ReglaDeNegocioViolada("Peso bruto (kg) inválido (1..88000)")
    if datos.peso_tara_kg < 0 or datos.peso_tara_kg >= datos.peso_bruto_kg:
        raise ReglaDeNegocioViolada("Peso tara (kg) inválido (debe ser >= 0 y menor al bruto)")
    if datos.km_recorrer < 1 or datos.km_recorrer > 99_999:
        raise ReglaDeNegocioViolada("Kilómetros a recorrer inválidos (1..99999)")
    dominio = (datos.dominio or "").strip().upper()
    if not dominio or dominio == "-":
        raise ReglaDeNegocioViolada("El viaje no tiene dominio (patente) asignado")

    cuit_solicitante = _cuit_limpio(datos.cuit_solicitante, "CUIT solicitante")
    cuit_productor = _cuit_limpio(datos.cuit_productor, "CUIT productor")
    destino_cuit = _cuit_limpio(datos.destino_cuit, "CUIT destinatario")
    cuit_transportista = _cuit_limpio(datos.cuit_transportista, "CUIT transportista")
    cuit_chofer = _cuit_limpio(datos.cuit_chofer, "CUIT chofer")

    if not datos.destino_es_campo and datos.destino_planta is None:
        raise ReglaDeNegocioViolada(
            "Destino a planta requiere código de planta RUCA (o marcar destino a campo)"
        )
    if datos.es_solicitante_campo and (
        datos.origen_latitud is None or datos.origen_longitud is None
    ):
        raise ReglaDeNegocioViolada(
            "Origen en campo requiere coordenadas GPS (punto de entrada del campo)"
        )

    origen: dict[str, Any] = {
        "cod_provincia": datos.origen_cod_provincia,
        "cod_localidad": datos.origen_cod_localidad,
        "planta": datos.origen_planta,
        "cuit_productor": cuit_productor,
    }
    if datos.origen_latitud is not None and datos.origen_longitud is not None:
        origen["coordenadas_gps"] = {
            "latitud": decimal_a_gms(datos.origen_latitud),
            "longitud": decimal_a_gms(datos.origen_longitud),
            "latitud_decimal": datos.origen_latitud,
            "longitud_decimal": datos.origen_longitud,
        }

    payload: dict[str, Any] = {
        "metodo_wscpe": "autorizarCPEAutomotor",
        "tipo_cpe": datos.tipo_cpe,
        "sucursal": datos.sucursal,
        "cuit_solicitante": cuit_solicitante,
        "origen": origen,
        "flags": {
            "corresponde_retiro_productor": datos.corresponde_retiro_productor,
            "es_solicitante_campo": datos.es_solicitante_campo,
        },
        "intervinientes": {
            "cuit_remitente_comercial_venta_primaria": _cuit_limpio(
                datos.cuit_remitente_comercial_venta_primaria,
                "CUIT remitente comercial VP",
                obligatorio=False,
            ),
            "cuit_remitente_comercial_venta_secundaria": _cuit_limpio(
                datos.cuit_remitente_comercial_venta_secundaria,
                "CUIT remitente comercial VS",
                obligatorio=False,
            ),
            "cuit_mercado_a_termino": _cuit_limpio(
                datos.cuit_mercado_a_termino, "CUIT mercado a término", obligatorio=False
            ),
            "cuit_corredor_venta_primaria": _cuit_limpio(
                datos.cuit_corredor_venta_primaria,
                "CUIT corredor VP",
                obligatorio=False,
            ),
            "cuit_corredor_venta_secundaria": _cuit_limpio(
                datos.cuit_corredor_venta_secundaria,
                "CUIT corredor VS",
                obligatorio=False,
            ),
            "cuit_representante_entregador": _cuit_limpio(
                datos.cuit_representante_entregador,
                "CUIT representante entregador",
                obligatorio=False,
            ),
            "cuit_representante_recibidor": _cuit_limpio(
                datos.cuit_representante_recibidor,
                "CUIT representante recibidor",
                obligatorio=False,
            ),
        },
        "datos_carga": {
            "cod_grano": datos.cod_grano,
            "cosecha": datos.cosecha,
            "peso_bruto": datos.peso_bruto_kg,
            "peso_tara": datos.peso_tara_kg,
            "peso_neto": datos.peso_bruto_kg - datos.peso_tara_kg,
        },
        "destino": {
            "cuit": destino_cuit,
            "es_destino_campo": datos.destino_es_campo,
            "cod_provincia": datos.destino_cod_provincia,
            "cod_localidad": datos.destino_cod_localidad,
            "planta": None if datos.destino_es_campo else datos.destino_planta,
        },
        "transporte": {
            "cuit_transportista": cuit_transportista,
            "dominio": [dominio],
            "fecha_hora_partida": datos.fecha_hora_partida.replace(microsecond=0).isoformat(),
            "km_recorrer": datos.km_recorrer,
            "cuit_chofer": cuit_chofer,
            "tarifa": datos.tarifa,
            "cuit_pagador_flete": _cuit_limpio(
                datos.cuit_pagador_flete, "CUIT pagador flete", obligatorio=False
            ),
            "cuit_intermediario_flete": _cuit_limpio(
                datos.cuit_intermediario_flete,
                "CUIT intermediario flete",
                obligatorio=False,
            ),
            "mercaderia_fumigada": datos.mercaderia_fumigada,
            "codigo_turno": datos.codigo_turno,
        },
        "observaciones": datos.observaciones or "",
        "_meta": {
            "material_nombre": datos.material_nombre,
            "origen_descripcion": datos.origen_descripcion,
            "destino_descripcion": datos.destino_descripcion,
            "despacho_nombre": datos.despacho_nombre,
            "tipo_cpe_etiqueta": (
                "Automotor" if datos.tipo_cpe == 74 else "Automotor flete corto"
            ),
        },
    }
    return payload
