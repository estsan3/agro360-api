"""Ticket de acceso WSAA (CMS firmado + LoginCms)."""

from __future__ import annotations

import base64
import html
import json
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

import httpx

TZ_AR = ZoneInfo("America/Argentina/Buenos_Aires")
_RAIZ_REPO = Path(__file__).resolve().parents[4]

WSAA_HOMO = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms"
WSAA_PROD = "https://wsaa.afip.gov.ar/ws/services/LoginCms"


@dataclass(frozen=True)
class TicketAcceso:
    token: str
    sign: str
    expiracion: datetime

    def vigente(self, margen_segundos: int = 300) -> bool:
        return datetime.now(TZ_AR) < (self.expiracion - timedelta(seconds=margen_segundos))


def crear_tra(service: str = "wscpe") -> str:
    ahora = datetime.now(TZ_AR)
    gen = (ahora - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S-03:00")
    exp = (ahora + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S-03:00")
    unique = int(time.time())
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<loginTicketRequest version="1.0">'
        "<header>"
        f"<uniqueId>{unique}</uniqueId>"
        f"<generationTime>{gen}</generationTime>"
        f"<expirationTime>{exp}</expirationTime>"
        "</header>"
        f"<service>{service}</service>"
        "</loginTicketRequest>"
    )


def firmar_cms(tra: str, certificado: Path, clave: Path) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tra_path = tmp_path / "TRA.xml"
        cms_path = tmp_path / "TRA.tmp"
        tra_path.write_text(tra, encoding="utf-8")
        cmd = [
            "openssl",
            "smime",
            "-sign",
            "-signer",
            str(certificado),
            "-inkey",
            str(clave),
            "-outform",
            "DER",
            "-nodetach",
            "-binary",
            "-in",
            str(tra_path),
            "-out",
            str(cms_path),
        ]
        resultado = subprocess.run(cmd, capture_output=True, text=True)
        if resultado.returncode != 0:
            detalle = (resultado.stderr or resultado.stdout or "").strip()
            raise RuntimeError(f"OpenSSL no pudo firmar el TRA WSAA: {detalle}")
        return base64.b64encode(cms_path.read_bytes()).decode("ascii")


def parsear_ticket(xml_o_escapado: str) -> TicketAcceso:
    """Extrae token/sign/expiración del loginCmsReturn (a veces HTML-escaped)."""
    texto = html.unescape(xml_o_escapado)
    inicio = texto.find("<loginTicketResponse")
    if inicio >= 0:
        fin = texto.find("</loginTicketResponse>")
        texto = texto[inicio : fin + len("</loginTicketResponse>")] if fin > 0 else texto[inicio:]
    raiz = ET.fromstring(texto)
    token = raiz.findtext(".//token") or ""
    sign = raiz.findtext(".//sign") or ""
    exp_txt = raiz.findtext(".//expirationTime") or ""
    if not token or not sign:
        raise RuntimeError("WSAA no devolvió token/sign en el ticket de acceso")
    try:
        expiracion = datetime.fromisoformat(exp_txt.replace("Z", "+00:00"))
        if expiracion.tzinfo is None:
            expiracion = expiracion.replace(tzinfo=TZ_AR)
    except ValueError:
        expiracion = datetime.now(TZ_AR) + timedelta(hours=12)
    return TicketAcceso(token=token, sign=sign, expiracion=expiracion)


def _ruta_cache(homologacion: bool, service: str) -> Path:
    ambiente = "homo" if homologacion else "prod"
    return _RAIZ_REPO / "data" / f"wsaa_{service}_{ambiente}.json"


def _leer_cache(homologacion: bool, service: str) -> TicketAcceso | None:
    ruta = _ruta_cache(homologacion, service)
    if not ruta.is_file():
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        ticket = TicketAcceso(
            token=str(datos["token"]),
            sign=str(datos["sign"]),
            expiracion=datetime.fromisoformat(str(datos["expiracion"])),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if not ticket.vigente():
        return None
    return ticket


def _guardar_cache(ticket: TicketAcceso, homologacion: bool, service: str) -> None:
    ruta = _ruta_cache(homologacion, service)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(
            {
                "token": ticket.token,
                "sign": ticket.sign,
                "expiracion": ticket.expiracion.isoformat(),
            }
        ),
        encoding="utf-8",
    )


async def obtener_ticket(
    *,
    certificado: Path,
    clave: Path,
    homologacion: bool,
    service: str = "wscpe",
    cliente: httpx.AsyncClient | None = None,
) -> TicketAcceso:
    cacheado = _leer_cache(homologacion, service)
    if cacheado is not None:
        return cacheado

    cms = firmar_cms(crear_tra(service), certificado, clave)
    url = WSAA_HOMO if homologacion else WSAA_PROD
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
        'xmlns:wsaa="http://wsaa.view.sua.dvadac.desein.afip.gov">'
        "<soapenv:Header/><soapenv:Body>"
        f"<wsaa:loginCms><wsaa:in0>{cms}</wsaa:in0></wsaa:loginCms>"
        "</soapenv:Body></soapenv:Envelope>"
    )
    propio = cliente is None
    http = cliente or httpx.AsyncClient(timeout=30.0, verify=not homologacion)
    try:
        resp = await http.post(
            url,
            content=body.encode("utf-8"),
            headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": '""'},
        )
        xml = resp.text
        if "loginCmsReturn" in xml or "loginTicketResponse" in xml:
            ticket = parsear_ticket(xml)
            _guardar_cache(ticket, homologacion, service)
            return ticket
        try:
            ticket = parsear_ticket(xml)
            _guardar_cache(ticket, homologacion, service)
            return ticket
        except (RuntimeError, ET.ParseError):
            pass
        detalle = _mensaje_fault(xml) or f"WSAA rechazó LoginCms (HTTP {resp.status_code})"
        if "ya posee un TA" in detalle:
            raise RuntimeError(
                f"{detalle}. WSAA no reentrega el ticket vigente: hay que esperar "
                "a que expire (~12 h) o reutilizar el TA cacheado en data/wsaa_*.json."
            )
        raise RuntimeError(detalle)
    finally:
        if propio:
            await http.aclose()


def _mensaje_fault(xml: str) -> str:
    texto = html.unescape(xml)
    inicio = texto.find("<faultstring>")
    fin = texto.find("</faultstring>")
    if inicio >= 0 and fin > inicio:
        return texto[inicio + len("<faultstring>") : fin].strip()
    return ""
