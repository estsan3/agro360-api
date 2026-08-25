"""Adaptador real hacia ARCA/AFIP: WSAA + WSCPE (SOAP).

Requisitos:
1. Certificado digital + clave privada (WSASS en homologación).
2. Alta del servicio `wscpe` asociada al certificado.
3. Variables `AGRO360_CPE_*` apuntando a esos archivos y al CUIT.

No usa PyAfipWs: el cliente SOAP es propio (httpx), el mismo contrato
que ya validamos con Postman.
"""

from __future__ import annotations

import html
from pathlib import Path
from xml.etree import ElementTree as ET

import httpx

from app.core.config import Configuracion
from app.modulos.cartas_porte.adaptadores.mapeo_soap import (
    NS,
    armar_solicitud_anular,
    armar_solicitud_automotor,
    auth_xml,
    envolver_soap,
)
from app.modulos.cartas_porte.adaptadores.wsaa import TicketAcceso, obtener_ticket
from app.modulos.cartas_porte.puerto import ProveedorCPE, ResultadoCPE, SolicitudCPE

WSCPE_HOMO = "https://cpea-ws-qaext.afip.gob.ar/wscpe/services/soap"
WSCPE_PROD = "https://cpea-ws.afip.gob.ar/wscpe/services/soap"
SOAP_ACTION = "https://serviciosjava.afip.gob.ar/wscpe/{operacion}"


class AdaptadorAfip(ProveedorCPE):
    """Implementación real vía WSAA + WSCPE SOAP."""

    def __init__(
        self,
        ruta_certificado: str,
        ruta_clave_privada: str,
        cuit_representada: str,
        homologacion: bool = True,
        cliente: httpx.AsyncClient | None = None,
    ) -> None:
        self._certificado = Path(ruta_certificado)
        self._clave = Path(ruta_clave_privada)
        self._cuit = "".join(ch for ch in cuit_representada if ch.isdigit())
        self._homologacion = homologacion
        self._cliente = cliente
        self._ticket: TicketAcceso | None = None
        self._url = WSCPE_HOMO if homologacion else WSCPE_PROD

    @classmethod
    def desde_config(cls, cfg: Configuracion) -> AdaptadorAfip:
        return cls(
            ruta_certificado=cfg.cpe_certificado,
            ruta_clave_privada=cfg.cpe_clave_privada,
            cuit_representada=cfg.cpe_cuit_representada,
            homologacion=cfg.cpe_homologacion,
        )

    def _validar_archivos(self) -> str | None:
        if not self._cuit or len(self._cuit) != 11:
            return "Falta AGRO360_CPE_CUIT_REPRESENTADA (CUIT de 11 dígitos)"
        if not self._certificado.is_file():
            return f"No existe el certificado ARCA: {self._certificado}"
        if not self._clave.is_file():
            return f"No existe la clave privada ARCA: {self._clave}"
        return None

    async def autorizar_cpe_automotor(self, solicitud: SolicitudCPE) -> ResultadoCPE:
        error_cfg = self._validar_archivos()
        if error_cfg:
            return ResultadoCPE(autorizada=False, error=error_cfg)
        try:
            ticket = await self._obtener_ticket()
            solicitud_xml = armar_solicitud_automotor(solicitud.payload, solicitud.nro_orden)
            xml = await self._post(
                "autorizarCPEAutomotor",
                "AutorizarCPEAutomotorReq",
                ticket,
                solicitud_xml,
            )
            return _parsear_autorizacion(xml, solicitud)
        except Exception as exc:
            return ResultadoCPE(autorizada=False, error=str(exc))

    async def anular_cpe(
        self, *, tipo_cpe: int, sucursal: int, nro_orden: int
    ) -> ResultadoCPE:
        error_cfg = self._validar_archivos()
        if error_cfg:
            return ResultadoCPE(autorizada=False, error=error_cfg)
        try:
            ticket = await self._obtener_ticket()
            xml = await self._post(
                "anularCPE",
                "AnularCPEReq",
                ticket,
                armar_solicitud_anular(tipo_cpe, sucursal, nro_orden),
            )
            errores = _errores_wscpe(xml)
            if errores:
                return ResultadoCPE(autorizada=False, error=errores)
            if _es_fault(xml):
                return ResultadoCPE(autorizada=False, error=_faultstring(xml))
            return ResultadoCPE(
                autorizada=True,
                nro_carta_porte=f"{tipo_cpe}{sucursal:05d}{nro_orden:08d}",
            )
        except Exception as exc:
            return ResultadoCPE(autorizada=False, error=str(exc))

    async def _obtener_ticket(self) -> TicketAcceso:
        if self._ticket and self._ticket.vigente():
            return self._ticket
        self._ticket = await obtener_ticket(
            certificado=self._certificado,
            clave=self._clave,
            homologacion=self._homologacion,
            cliente=self._cliente,
        )
        return self._ticket

    async def _post(
        self,
        operacion: str,
        req_name: str,
        ticket: TicketAcceso,
        solicitud_xml: str,
    ) -> str:
        body = envolver_soap(
            req_name,
            auth_xml(ticket.token, ticket.sign, self._cuit),
            solicitud_xml,
        )
        propio = self._cliente is None
        http = self._cliente or httpx.AsyncClient(
            timeout=60.0, verify=not self._homologacion
        )
        try:
            resp = await http.post(
                self._url,
                content=body.encode("utf-8"),
                headers={
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": f'"{SOAP_ACTION.format(operacion=operacion)}"',
                },
            )
            return resp.text
        finally:
            if propio:
                await http.aclose()


def _texto(elem: ET.Element | None, tag: str) -> str:
    if elem is None:
        return ""
    hallado = elem.find(f".//{{{NS}}}{tag}")
    if hallado is None:
        hallado = elem.find(f".//{{*}}{tag}")
    if hallado is None or hallado.text is None:
        return ""
    return hallado.text.strip()


def _errores_wscpe(xml: str) -> str:
    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError:
        return ""
    partes: list[str] = []
    for error in raiz.iter():
        local = error.tag.rsplit("}", 1)[-1]
        if local not in {"error", "codigoDescripcion"}:
            continue
        codigo = _texto(error, "codigo")
        desc = _texto(error, "descripcion")
        if codigo or desc:
            partes.append(f"{codigo}: {desc}".strip(": "))
    return " | ".join(partes)


def _es_fault(xml: str) -> bool:
    compacto = xml.lower()
    return "<faultstring>" in compacto or ":fault>" in compacto


def _faultstring(xml: str) -> str:
    texto = html.unescape(xml)
    inicio = texto.lower().find("<faultstring>")
    fin = texto.lower().find("</faultstring>")
    if inicio >= 0 and fin > inicio:
        return texto[inicio + len("<faultstring>") : fin].strip()
    return "Error SOAP de WSCPE"


def _parsear_autorizacion(xml: str, solicitud: SolicitudCPE) -> ResultadoCPE:
    if _es_fault(xml) and "nroCTG" not in xml:
        return ResultadoCPE(autorizada=False, error=_faultstring(xml))
    errores = _errores_wscpe(xml)
    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError:
        return ResultadoCPE(autorizada=False, error=errores or "Respuesta WSCPE ilegible")

    nro_ctg = _texto(raiz, "nroCTG")
    sucursal = _texto(raiz, "sucursal") or str(solicitud.payload.get("sucursal") or "")
    nro_orden = _texto(raiz, "nroOrden") or str(solicitud.nro_orden)
    tipo = str(solicitud.payload.get("tipo_cpe") or 74)
    pdf = _texto(raiz, "pdf")
    nro_carta = ""
    if sucursal and nro_orden:
        try:
            nro_carta = f"{int(tipo)}{int(sucursal):05d}{int(nro_orden):08d}"
        except ValueError:
            nro_carta = f"{tipo}-{sucursal}-{nro_orden}"

    if errores and not nro_ctg:
        return ResultadoCPE(autorizada=False, error=errores)
    if not nro_ctg:
        return ResultadoCPE(
            autorizada=False,
            error=errores or _faultstring(xml) or "WSCPE no devolvió CTG",
        )
    return ResultadoCPE(
        autorizada=True,
        nro_carta_porte=nro_carta or None,
        nro_ctg=nro_ctg,
        pdf_base64=pdf or None,
        error=errores,
    )
