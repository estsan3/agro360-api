"""Prueba viva contra homologación ARCA: WSAA + WSCPE.

Usa el adaptador real (`AGRO360_CPE_PROVEEDOR=afip`) y el payload de ejemplo
Maíz → COFCO de la colección Postman.

  poetry run python scripts/probar_homologacion_cpe.py
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from app.core.config import obtener_configuracion
from app.modulos.cartas_porte.adaptadores.afip import AdaptadorAfip
from app.modulos.cartas_porte.puerto import SolicitudCPE

TZ_AR = ZoneInfo("America/Argentina/Buenos_Aires")
CUIT = "20297938739"


def _texto_local(xml: str, tag: str) -> str:
    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError:
        return ""
    for elem in raiz.iter():
        if elem.tag.rsplit("}", 1)[-1] == tag and elem.text:
            return elem.text.strip()
    return ""


def _fault(xml: str) -> str:
    texto = xml.replace("&lt;", "<").replace("&gt;", ">")
    match = re.search(r"<faultstring>(.*?)</faultstring>", texto, re.I | re.S)
    if match:
        return match.group(1).strip()
    errores = []
    for m in re.finditer(
        r"<descripcion>(.*?)</descripcion>", texto, re.I | re.S
    ):
        errores.append(m.group(1).strip())
    return " | ".join(errores)[:500]


def _resumen_xml(xml: str, tags: tuple[str, ...] = ()) -> str:
    fault = _fault(xml)
    if fault:
        return fault
    if not tags:
        return re.sub(r">\s+<", "><", xml)[:400]
    partes: list[str] = []
    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError:
        return xml[:300]
    for elem in raiz.iter():
        local = elem.tag.rsplit("}", 1)[-1]
        if local in tags and elem.text and elem.text.strip():
            partes.append(f"{local}={elem.text.strip()}")
    return " | ".join(partes[:20]) or xml[:300]


def _payload_cofco(partida: datetime, *, origen: dict, es_campo: bool) -> dict:
    return {
        "metodo_wscpe": "autorizarCPEAutomotor",
        "tipo_cpe": 74,
        "sucursal": 1,
        "cuit_solicitante": CUIT,
        "origen": origen,
        "flags": {
            "corresponde_retiro_productor": False,
            "es_solicitante_campo": es_campo,
        },
        "intervinientes": {
            "cuit_remitente_comercial_venta_primaria": "33502232229",
            "cuit_remitente_comercial_venta_secundaria": "30711855641",
            "cuit_mercado_a_termino": "30525698412",
            "cuit_corredor_venta_secundaria": "30703605105",
            "cuit_representante_entregador": "30711962766",
        },
        "datos_carga": {
            "cod_grano": 19,
            "cosecha": 2526,
            "peso_bruto": 45000,
            "peso_tara": 15000,
            "peso_neto": 30000,
        },
        "destino": {
            "cuit": "33506737449",
            "es_destino_campo": False,
            "cod_provincia": 12,
            "cod_localidad": 11797,
            "planta": 512428,
        },
        "transporte": {
            "cuit_transportista": "20237684436",
            "dominio": ["JII026", "AF495WZ"],
            "fecha_hora_partida": partida.replace(microsecond=0).isoformat(),
            "km_recorrer": 454,
            "cuit_chofer": "20388082802",
            "tarifa": 41000,
            "cuit_pagador_flete": CUIT,
            "mercaderia_fumigada": False,
        },
        "observaciones": "Prueba homologación Agro360",
    }


async def main() -> int:
    cfg = obtener_configuracion()
    print(
        f"proveedor={cfg.cpe_proveedor} homo={cfg.cpe_homologacion} "
        f"cuit={cfg.cpe_cuit_representada}"
    )
    print(f"cert={cfg.cpe_certificado}")
    adapter = AdaptadorAfip.desde_config(cfg)
    error_cfg = adapter._validar_archivos()
    if error_cfg:
        print("CONFIG:", error_cfg)
        return 1

    print("\n[1] WSAA LoginCms…")
    ticket = await adapter._obtener_ticket()
    print(f"    OK token={ticket.token[:12]}… expira={ticket.expiracion.isoformat()}")

    print("\n[2] consultarProvincias…")
    xml_prov = await adapter._post(
        "consultarProvincias", "ConsultarProvinciasReq", ticket, ""
    )
    compacto = xml_prov.lower()
    if "cod" in compacto and "descripcion" in compacto and "faultstring" not in compacto:
        print("    OK (listado de provincias)")
    else:
        print("    FAIL", _fault(xml_prov) or xml_prov[:400])
        return 1

    print("\n[3] consultarDomiciliosPorCUIT / consultarPlantas…")
    xml_dom = await adapter._post(
        "consultarDomiciliosPorCUIT",
        "ConsultarDomiciliosPorCUITReq",
        ticket,
        f"<cuit>{CUIT}</cuit>",
    )
    print(
        "    domicilios:",
        _resumen_xml(
            xml_dom,
            ("codProvincia", "codLocalidad", "planta", "nroPlanta", "descripcion", "tipo"),
        ),
    )
    xml_plantas = await adapter._post(
        "consultarPlantas",
        "ConsultarPlantasReq",
        ticket,
        f"<solicitud><cuit>{CUIT}</cuit></solicitud>",
    )
    print(
        "    plantas:",
        _resumen_xml(
            xml_plantas,
            ("codProvincia", "codLocalidad", "planta", "nroPlanta", "descripcion", "codigo"),
        ),
    )
    planta = _texto_local(xml_plantas, "planta") or _texto_local(xml_dom, "planta")
    orig_prov = _texto_local(xml_plantas, "codProvincia") or _texto_local(xml_dom, "codProvincia")
    orig_loc = _texto_local(xml_plantas, "codLocalidad") or _texto_local(xml_dom, "codLocalidad")
    if planta and orig_prov and orig_loc:
        origen = {
            "cod_provincia": int(orig_prov),
            "cod_localidad": int(orig_loc),
            "planta": int(planta),
        }
        es_campo = False
        print(f"    origen operador planta={planta} prov={orig_prov} loc={orig_loc}")
    else:
        origen = {
            "cod_provincia": 21,
            "cod_localidad": 6975,
            "cuit_productor": CUIT,
            "coordenadas_gps": {
                "latitud_decimal": -33.0569,
                "longitud_decimal": -60.6778,
            },
        }
        es_campo = True
        print("    sin planta en padron; se intenta origen campo (puede fallar 1015)")

    print("\n[4] consultarUltNroOrden sucursal=1 tipoCPE=74…")
    xml_nro = await adapter._post(
        "consultarUltNroOrden",
        "ConsultarUltNroOrdenReq",
        ticket,
        "<solicitud><sucursal>1</sucursal><tipoCPE>74</tipoCPE></solicitud>",
    )
    ultimo = _texto_local(xml_nro, "nroOrden") or _texto_local(xml_nro, "nroOrden")
    if not ultimo:
        ultimo = _texto_local(xml_nro, "ultimoNroOrden")
    fault_nro = _fault(xml_nro)
    if ultimo:
        nro_orden = int(ultimo) + 1
        print(f"    último={ultimo} → próximo={nro_orden}")
    else:
        nro_orden = int(datetime.now(TZ_AR).strftime("%d%H%M"))
        print(
            f"    no se pudo leer último ({(fault_nro or xml_nro[:200])!r}) "
            f"→ nro_orden={nro_orden}"
        )

    partida = datetime.now(TZ_AR) + timedelta(hours=6)
    payload = _payload_cofco(partida, origen=origen, es_campo=es_campo)
    print(
        f"\n[5] autorizarCPEAutomotor nroOrden={nro_orden} "
        f"partida={partida.isoformat(timespec='minutes')}…"
    )
    solicitud = SolicitudCPE(payload=payload, nro_orden=nro_orden)
    resultado = await adapter.autorizar_cpe_automotor(solicitud)
    if resultado.autorizada:
        print("    AUTORIZADA")
        print(f"    nro_carta_porte={resultado.nro_carta_porte}")
        print(f"    nro_ctg={resultado.nro_ctg}")
        print(f"    pdf={'sí' if resultado.pdf_base64 else 'no'}")
        if resultado.error:
            print(f"    avisos={resultado.error}")
        return 0

    print("    RECHAZADA:", resultado.error)
    return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
