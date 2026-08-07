"""Generación de PDF demo de Carta de Porte (sin dependencias externas)."""

from __future__ import annotations

import base64


def generar_pdf_cpe_demo(
    *,
    nro_carta_porte: str,
    nro_ctg: str,
    tipo_cpe: int,
    material: str,
    origen: str,
    destino: str,
    dominio: str,
    toneladas: float,
    estado: str = "procesada",
) -> str:
    """Devuelve un PDF mínimo válido en base64 (visualizable/descargable)."""
    tipo_etiqueta = "Automotor" if tipo_cpe == 74 else "Automotor flete corto"
    lineas = [
        "AGRO360 — Carta de Porte Electrónica (demo)",
        f"Estado: {estado.upper()}",
        f"Tipo CPE: {tipo_cpe} ({tipo_etiqueta})",
        f"Nro. Carta de Porte: {nro_carta_porte}",
        f"CTG: {nro_ctg}",
        f"Material: {material}",
        f"Origen: {origen}",
        f"Destino: {destino}",
        f"Dominio: {dominio}",
        f"Toneladas: {toneladas}",
        "",
        "Documento generado para demo local.",
        "En producción se reemplaza por el PDF oficial de ARCA/WSCPE.",
    ]
    return base64.b64encode(_pdf_texto(lineas)).decode("ascii")


def _pdf_texto(lineas: list[str]) -> bytes:
    """Arma un PDF 1.4 de una página con texto en Helvetica."""
    # Coordenadas: de arriba hacia abajo.
    y = 780
    comandos = ["BT", "/F1 11 Tf", "14 TL", f"50 {y} Td"]
    for i, linea in enumerate(lineas):
        segura = (
            linea.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
            .replace("—", "-")
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
            .replace("ñ", "n")
            .replace("Á", "A")
            .replace("É", "E")
            .replace("Í", "I")
            .replace("Ó", "O")
            .replace("Ú", "U")
            .replace("Ñ", "N")
        )
        if i == 0:
            comandos.append(f"({segura}) Tj")
        else:
            comandos.append(f"T* ({segura}) Tj")
    comandos.append("ET")
    stream = "\n".join(comandos).encode("latin-1", errors="replace")

    objetos: list[bytes] = []
    objetos.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objetos.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objetos.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
    )
    objetos.append(
        f"4 0 obj<< /Length {len(stream)} >>stream\n".encode("ascii")
        + stream
        + b"\nendstream\nendobj\n"
    )
    objetos.append(
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
    )

    salida = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objetos:
        offsets.append(len(salida))
        salida.extend(obj)

    xref_pos = len(salida)
    salida.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    salida.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        salida.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    salida.extend(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(salida)
