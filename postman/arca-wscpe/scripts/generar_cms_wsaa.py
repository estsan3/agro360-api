#!/usr/bin/env python3
"""Genera el CMS Base64 para WSAA LoginCms (homologación / producción).

Requisitos:
  - Certificado X.509 + clave privada emitidos por ARCA (WSASS en homo).
  - Alta del servicio `wscpe` asociada al certificado.
  - OpenSSL en PATH.

Uso:
  python generar_cms_wsaa.py \\
    --cert ./homo.crt \\
    --key ./homo.key \\
    --service wscpe \\
    --out cms.b64

Luego pegá el contenido de cms.b64 en la variable Postman `cmsBase64`
y ejecutá "LoginCms (WSAA homologación)".
"""

from __future__ import annotations

import argparse
import base64
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# WSAA valida generationTime/expirationTime en horario Argentina (-03:00).
# No usar UTC con sufijo -03:00: queda ~3h en el futuro y falla.
TZ_AR = ZoneInfo("America/Argentina/Buenos_Aires")


def crear_tra(service: str) -> str:
    ahora = datetime.now(TZ_AR)
    # Margen hacia atrás por desfase de reloj con los servers de AFIP.
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


def firmar_cms(tra: str, cert: Path, key: Path) -> str:
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
            str(cert),
            "-inkey",
            str(key),
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
            raise SystemExit(
                f"OpenSSL falló (exit {resultado.returncode}).\n"
                f"Comando: {' '.join(cmd)}\n"
                f"Detalle: {detalle or '(sin mensaje)'}\n\n"
                "Verificá que --cert y --key apunten a archivos reales del certificado "
                "WSASS (no uses /ruta/homo.crt como en el ejemplo del README)."
            )
        return base64.b64encode(cms_path.read_bytes()).decode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cert", type=Path, required=True, help="Certificado .crt/.pem")
    parser.add_argument("--key", type=Path, required=True, help="Clave privada .key/.pem")
    parser.add_argument(
        "--service",
        default="wscpe",
        help="ID del WSN en el TRA (default: wscpe)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("cms.b64"),
        help="Archivo de salida con el CMS en Base64",
    )
    args = parser.parse_args()

    if not args.cert.is_file():
        raise SystemExit(
            f"No existe el certificado: {args.cert}\n"
            "Reemplazá /ruta/homo.crt por la ruta real de tu .crt/.pem de homologación WSASS."
        )
    if not args.key.is_file():
        raise SystemExit(
            f"No existe la clave privada: {args.key}\n"
            "Reemplazá /ruta/homo.key por la ruta real de tu .key/.pem."
        )

    tra = crear_tra(args.service)
    cms_b64 = firmar_cms(tra, args.cert, args.key)
    args.out.write_text(cms_b64, encoding="ascii")
    print(f"CMS escrito en {args.out} ({len(cms_b64)} chars)")
    print("Pegalo en Postman → environment → cmsBase64")


if __name__ == "__main__":
    main()
