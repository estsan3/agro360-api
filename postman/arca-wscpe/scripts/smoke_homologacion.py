#!/usr/bin/env python3
"""Smoke de homologación ARCA/AFIP sin certificado.

1) WSCPE dummy → debe devolver appserver/authserver/dbserver = Ok
2) WSAA LoginCms con CMS inválido → debe responder Fault CMS (servicio vivo)
3) ConsultarProvincias con Auth inválida → error de autenticación (Auth parseado)
"""

from __future__ import annotations

import ssl
import sys
import urllib.error
import urllib.request

WSCPE = "https://cpea-ws-qaext.afip.gob.ar/wscpe/services/soap"
WSAA = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms"
NS = "https://serviciosjava.afip.gob.ar/wscpe/"

# Homologación AFIP suele presentar cadena no confiable en algunos Python/macOS.
SSL_CTX = ssl._create_unverified_context()


def post_xml(url: str, body: str) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        data=body.encode("utf-8"),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": '""',
            "User-Agent": "Agro360-WSCPE-Smoke/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def main() -> int:
    ok = True

    dummy = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:wsc="{NS}">
  <soapenv:Header/>
  <soapenv:Body>
    <wsc:dummy/>
  </soapenv:Body>
</soapenv:Envelope>"""
    code, body = post_xml(WSCPE, dummy)
    compact = body.replace(" ", "").replace("\n", "").lower()
    dummy_ok = (
        code == 200
        and "appserver>ok" in compact
        and "authserver>ok" in compact
        and "dbserver>ok" in compact
    )
    print(f"[1] dummy HTTP {code} → {'PASS' if dummy_ok else 'FAIL'}")
    if not dummy_ok:
        print(body[:400])
        ok = False

    login = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:wsaa="http://wsaa.view.sua.dvadac.desein.afip.gov">
  <soapenv:Header/>
  <soapenv:Body>
    <wsaa:loginCms>
      <wsaa:in0>INVALID</wsaa:in0>
    </wsaa:loginCms>
  </soapenv:Body>
</soapenv:Envelope>"""
    code, body = post_xml(WSAA, login)
    wsaa_ok = "CMS" in body or "loginCmsResponse" in body or "faultstring" in body
    print(f"[2] WSAA LoginCms HTTP {code} → {'PASS (servicio responde)' if wsaa_ok else 'FAIL'}")
    if not wsaa_ok:
        print(body[:400])
        ok = False
    else:
        print(f"    fault/respuesta: {body[body.find('faultstring'):body.find('faultstring')+80] if 'faultstring' in body else 'ok'}")

    provincias = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:wsc="{NS}">
  <soapenv:Header/>
  <soapenv:Body>
    <wsc:ConsultarProvinciasReq>
      <auth>
        <token>INVALID</token>
        <sign>INVALID</sign>
        <cuitRepresentada>20111111111</cuitRepresentada>
      </auth>
    </wsc:ConsultarProvinciasReq>
  </soapenv:Body>
</soapenv:Envelope>"""
    code, body = post_xml(WSCPE, provincias)
    low = body.lower()
    # SOAP Fault de auth suele llegar como HTTP 500.
    auth_ok = (
        "autentic" in low
        or "token" in low
        or "sign" in low
        or "faultstring" in low
    )
    print(f"[3] ConsultarProvincias Auth inválida HTTP {code} → {'PASS' if auth_ok else 'FAIL'}")
    if not auth_ok:
        print(body[:400])
        ok = False
    else:
        print("    (esperado: rechazo de token/sign; confirma que Auth se valida)")
        if "<faultstring>" in body:
            ini = body.find("<faultstring>")
            fin = body.find("</faultstring>") + len("</faultstring>")
            print(f"    detalle: {body[ini:fin]}")

    print("RESULTADO:", "OK" if ok else "CON FALLOS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
