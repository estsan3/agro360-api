"""Mapeo puro: payload JSON de Agro360 → XML de solicitud WSCPE.

No habla con la red. Lo usa el adaptador AFIP para armar el SOAP.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from xml.sax.saxutils import escape

from app.modulos.cartas_porte.payload import decimal_a_gms

NS = "https://serviciosjava.afip.gob.ar/wscpe/"


def _txt(valor: Any) -> str:
    return escape(str(valor), {"'": "&apos;", '"': "&quot;"})


def _bool(valor: Any) -> str:
    return "true" if bool(valor) else "false"


def _fecha_partida(iso: str) -> str:
    """WSCPE espera dateTime sin zona (ej. 2025-08-13T20:00:00)."""
    bruto = (iso or "").strip()
    if not bruto:
        return bruto
    try:
        dt = datetime.fromisoformat(bruto.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None, microsecond=0).isoformat()
    except ValueError:
        return bruto[:19]


def _tag(nombre: str, valor: Any | None, *, omitir_vacio: bool = True) -> str:
    if valor is None or valor == "":
        return "" if omitir_vacio else f"<{nombre}></{nombre}>"
    return f"<{nombre}>{_txt(valor)}</{nombre}>"


def _gms(bloque: dict[str, Any] | None, decimal: float | None) -> str:
    grados: Any
    minutos: Any
    segundos: Any
    if bloque and bloque.get("grados") is not None:
        grados, minutos, segundos = bloque["grados"], bloque["minutos"], bloque["segundos"]
        # El payload guarda grados en valor absoluto; WSCPE espera signo en grados.
        if decimal is not None and decimal < 0:
            try:
                if int(grados) > 0:
                    grados = -int(grados)
            except (TypeError, ValueError):
                pass
    elif decimal is not None:
        convertido = decimal_a_gms(decimal)
        signo = -1 if decimal < 0 else 1
        grados = signo * int(convertido["grados"])
        minutos = convertido["minutos"]
        segundos = convertido["segundos"]
    else:
        return ""
    return (
        f"<grados>{_txt(grados)}</grados>"
        f"<minutos>{_txt(minutos)}</minutos>"
        f"<segundos>{_txt(segundos)}</segundos>"
    )


def _origen(payload: dict[str, Any]) -> str:
    origen = payload.get("origen") or {}
    flags = payload.get("flags") or {}
    planta = origen.get("planta")
    # WSCPE 949: no informar <productor> si el solicitante no opera desde campo.
    if flags.get("es_solicitante_campo"):
        gps = origen.get("coordenadas_gps") or {}
        lat_bloque = gps.get("latitud") if isinstance(gps.get("latitud"), dict) else None
        lng_bloque = gps.get("longitud") if isinstance(gps.get("longitud"), dict) else None
        lat_xml = _gms(lat_bloque, gps.get("latitud_decimal"))
        lng_xml = _gms(lng_bloque, gps.get("longitud_decimal"))
        coords = ""
        if lat_xml and lng_xml:
            coords = (
                "<coordenadasGPS>"
                f"<latitud>{lat_xml}</latitud>"
                f"<longitud>{lng_xml}</longitud>"
                "</coordenadasGPS>"
            )
        renspa = _tag("nroRenspa", origen.get("nro_renspa"))
        return (
            "<origen><productor>"
            f"{_tag('codProvincia', origen.get('cod_provincia'), omitir_vacio=False)}"
            f"{_tag('codLocalidad', origen.get('cod_localidad'), omitir_vacio=False)}"
            f"{renspa}{coords}"
            "</productor></origen>"
        )
    return (
        "<origen><operador>"
        f"{_tag('codProvincia', origen.get('cod_provincia'), omitir_vacio=False)}"
        f"{_tag('codLocalidad', origen.get('cod_localidad'), omitir_vacio=False)}"
        f"{_tag('planta', planta, omitir_vacio=False)}"
        "</operador></origen>"
    )


def _intervinientes(payload: dict[str, Any]) -> str:
    datos = payload.get("intervinientes") or {}
    pares = (
        ("cuitRemitenteComercialVentaPrimaria", "cuit_remitente_comercial_venta_primaria"),
        ("cuitRemitenteComercialVentaSecundaria", "cuit_remitente_comercial_venta_secundaria"),
        ("cuitRemitenteComercialVentaSecundaria2", "cuit_remitente_comercial_venta_secundaria_2"),
        ("cuitMercadoATermino", "cuit_mercado_a_termino"),
        ("cuitCorredorVentaPrimaria", "cuit_corredor_venta_primaria"),
        ("cuitCorredorVentaSecundaria", "cuit_corredor_venta_secundaria"),
        ("cuitRepresentanteEntregador", "cuit_representante_entregador"),
        ("cuitRepresentanteRecibidor", "cuit_representante_recibidor"),
    )
    cuerpo = "".join(_tag(xml, datos.get(json_key)) for xml, json_key in pares)
    if not cuerpo:
        return ""
    return f"<intervinientes>{cuerpo}</intervinientes>"


def _retiro_productor(payload: dict[str, Any]) -> str:
    flags = payload.get("flags") or {}
    if not flags.get("corresponde_retiro_productor"):
        return ""
    inter = payload.get("intervinientes") or {}
    origen = payload.get("origen") or {}
    cuit = (
        inter.get("cuit_remitente_comercial_productor")
        or origen.get("cuit_productor")
    )
    if not cuit:
        return ""
    return (
        "<retiroProductor>"
        f"{_tag('cuitRemitenteComercialProductor', cuit)}"
        "</retiroProductor>"
    )


def _transporte(payload: dict[str, Any]) -> str:
    tr = payload.get("transporte") or {}
    dominios = tr.get("dominio") or []
    if isinstance(dominios, str):
        dominios = [dominios]
    xml_dominios = "".join(_tag("dominio", d) for d in dominios if d)
    pagador = tr.get("cuit_pagador_flete") or payload.get("cuit_solicitante")
    return (
        "<transporte>"
        f"{_tag('cuitTransportista', tr.get('cuit_transportista'))}"
        f"{xml_dominios}"
        f"{_tag('fechaHoraPartida', _fecha_partida(str(tr.get('fecha_hora_partida') or '')))}"
        f"{_tag('kmRecorrer', tr.get('km_recorrer'))}"
        f"{_tag('codigoTurno', tr.get('codigo_turno'))}"
        f"{_tag('cuitChofer', tr.get('cuit_chofer'))}"
        f"{_tag('tarifa', tr.get('tarifa'))}"
        f"{_tag('cuitPagadorFlete', pagador)}"
        f"{_tag('cuitIntermediarioFlete', tr.get('cuit_intermediario_flete'))}"
        f"<mercaderiaFumigada>{_bool(tr.get('mercaderia_fumigada'))}</mercaderiaFumigada>"
        "</transporte>"
    )


def armar_solicitud_automotor(payload: dict[str, Any], nro_orden: int) -> str:
    """Devuelve el XML interno de `<solicitud>` para autorizarCPEAutomotor."""
    carga = payload.get("datos_carga") or {}
    destino = payload.get("destino") or {}
    flags = payload.get("flags") or {}
    observaciones = (payload.get("observaciones") or "").strip()
    destino_cuit = destino.get("cuit")
    planta = destino.get("planta")
    if destino.get("es_destino_campo"):
        planta = None

    return (
        "<solicitud>"
        "<cabecera>"
        f"{_tag('tipoCP', payload.get('tipo_cpe'))}"
        f"{_tag('cuitSolicitante', payload.get('cuit_solicitante'))}"
        f"{_tag('sucursal', payload.get('sucursal'))}"
        f"{_tag('nroOrden', nro_orden)}"
        "</cabecera>"
        f"{_origen(payload)}"
        f"<correspondeRetiroProductor>{_bool(flags.get('corresponde_retiro_productor'))}</correspondeRetiroProductor>"
        f"<esSolicitanteCampo>{_bool(flags.get('es_solicitante_campo'))}</esSolicitanteCampo>"
        f"{_retiro_productor(payload)}"
        f"{_intervinientes(payload)}"
        "<datosCarga>"
        f"{_tag('codGrano', carga.get('cod_grano'))}"
        f"{_tag('cosecha', carga.get('cosecha'))}"
        f"{_tag('pesoBruto', carga.get('peso_bruto'))}"
        f"{_tag('pesoTara', carga.get('peso_tara'))}"
        "</datosCarga>"
        "<destino>"
        f"{_tag('cuit', destino_cuit)}"
        f"<esDestinoCampo>{_bool(destino.get('es_destino_campo'))}</esDestinoCampo>"
        f"{_tag('codProvincia', destino.get('cod_provincia'))}"
        f"{_tag('codLocalidad', destino.get('cod_localidad'))}"
        f"{_tag('planta', planta)}"
        "</destino>"
        "<destinatario>"
        f"{_tag('cuit', destino_cuit)}"
        "</destinatario>"
        f"{_transporte(payload)}"
        f"{_tag('observaciones', observaciones)}"
        "</solicitud>"
    )


def armar_solicitud_anular(tipo_cpe: int, sucursal: int, nro_orden: int) -> str:
    return (
        "<solicitud><cartaPorte>"
        f"{_tag('tipoCPE', tipo_cpe)}"
        f"{_tag('sucursal', sucursal)}"
        f"{_tag('nroOrden', nro_orden)}"
        "</cartaPorte></solicitud>"
    )


def envolver_soap(operacion_req: str, auth_xml: str, solicitud_xml: str) -> str:
    """Arma el envelope SOAP 1.1 de WSCPE."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
        f'xmlns:wsc="{NS}">'
        "<soapenv:Header/>"
        "<soapenv:Body>"
        f"<wsc:{operacion_req}>"
        f"{auth_xml}"
        f"{solicitud_xml}"
        f"</wsc:{operacion_req}>"
        "</soapenv:Body>"
        "</soapenv:Envelope>"
    )


def auth_xml(token: str, sign: str, cuit: str) -> str:
    return (
        "<auth>"
        f"<token>{_txt(token)}</token>"
        f"<sign>{_txt(sign)}</sign>"
        f"<cuitRepresentada>{_txt(cuit)}</cuitRepresentada>"
        "</auth>"
    )
