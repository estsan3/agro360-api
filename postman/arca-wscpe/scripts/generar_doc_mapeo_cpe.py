#!/usr/bin/env python3
"""Genera PDF de documentación del mapeo CPE Automotor (ejemplo)."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

DOCS = Path(__file__).resolve().parents[1] / "docs"
IMG_SRC = Path(
    "/Users/estebansantamarina/.cursor/projects/"
    "Users-estebansantamarina-agro360-api/assets/"
    "WhatsApp_Image_2025-12-07_at_12.20.44-aebebef7-248a-4ce1-8ebb-115d445ceeeb.png"
)
OUT = DOCS / "WSCPE-mapeo-cpe-automotor-ejemplo.pdf"
IMG_DST = DOCS / "carta-porte-ejemplo.png"

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]


class Doc(FPDF):
    def __init__(self, font_path: str) -> None:
        super().__init__()
        self._font = font_path
        self.set_auto_page_break(auto=True, margin=18)
        self.add_font("Doc", "", font_path)
        self.add_font("Doc", "B", font_path)
        self.alias_nb_pages()

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Doc", "B", 9)
        self.set_text_color(90, 90, 90)
        self.cell(
            0,
            8,
            "Agro360 · WSCPE · Mapeo CPE Automotor (ejemplo)",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.set_draw_color(210, 210, 210)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Doc", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            8,
            f"Pagina {self.page_no()}/{{nb}} · Homologacion ARCA/AFIP · Uso interno",
            align="C",
        )

    def _reset_x(self) -> None:
        self.set_x(self.l_margin)

    def h1(self, text: str) -> None:
        self.set_font("Doc", "B", 16)
        self.set_text_color(20, 20, 20)
        self._reset_x()
        self.multi_cell(0, 9, text)
        self.ln(2)

    def h2(self, text: str) -> None:
        self.ln(3)
        self.set_font("Doc", "B", 12)
        self.set_text_color(25, 25, 25)
        self._reset_x()
        self.multi_cell(0, 7, text)
        self.ln(1)

    def h3(self, text: str) -> None:
        self.ln(2)
        self.set_font("Doc", "B", 10)
        self._reset_x()
        self.multi_cell(0, 6, text)

    def p(self, text: str) -> None:
        self.set_font("Doc", "", 10)
        self.set_text_color(35, 35, 35)
        self._reset_x()
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def bullet(self, text: str) -> None:
        self.set_font("Doc", "", 10)
        self.set_text_color(35, 35, 35)
        self._reset_x()
        self.multi_cell(0, 5.5, f"- {text}")

    def table(self, headers: list[str], rows: list[list[str]], widths: list[float]) -> None:
        usable = self.w - self.l_margin - self.r_margin
        assert abs(sum(widths) - usable) < 1, (sum(widths), usable)
        line_h = 5

        def row_height(cells: list[str], bold: bool = False) -> float:
            self.set_font("Doc", "B" if bold else "", 7.5)
            h = line_h
            for i, cell in enumerate(cells):
                # approx lines
                w = widths[i] - 2
                words = str(cell).split()
                lines, cur = 1, 0.0
                for word in words:
                    ww = self.get_string_width(word + " ")
                    if cur + ww > w:
                        lines += 1
                        cur = ww
                    else:
                        cur += ww
                h = max(h, lines * line_h + 2)
            return min(h, 28)

        def draw_row(cells: list[str], bold: bool = False, fill: bool = False) -> None:
            h = row_height(cells, bold)
            if self.get_y() + h > self.h - 20:
                self.add_page()
            self._reset_x()
            x0, y0 = self.get_x(), self.get_y()
            self.set_font("Doc", "B" if bold else "", 7.5)
            if fill:
                self.set_fill_color(242, 242, 242)
            for i, cell in enumerate(cells):
                self.set_xy(x0 + sum(widths[:i]), y0)
                self.multi_cell(
                    widths[i],
                    line_h,
                    str(cell),
                    border=1,
                    fill=fill,
                )
                # multi_cell moves Y; restore for next col
            self.set_xy(x0, y0 + h)

        draw_row(headers, bold=True, fill=True)
        for r in rows:
            draw_row(r)
        self.ln(2)
        self._reset_x()


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    if IMG_SRC.exists():
        IMG_DST.write_bytes(IMG_SRC.read_bytes())

    font = next((p for p in FONT_CANDIDATES if Path(p).exists()), None)
    if not font:
        raise SystemExit("No se encontro fuente TTF Unicode")

    pdf = Doc(font)
    pdf.add_page()
    pdf.h1("Documentacion WSCPE")
    pdf.h2("Mapeo Carta de Porte Electronica Automotor (ejemplo)")
    pdf.p(
        "Proyecto Agro360. Ambiente de homologacion ARCA/AFIP. "
        "Documentacion armada a partir de una CPE real (datos parcialmente tachados) "
        "y consultas a los servicios WSCPE."
    )
    pdf.p(
        "CPE = Carta de Porte Electronica: documento digital que autoriza y traza "
        "el traslado de granos en Argentina."
    )

    pdf.h2("1. Carta de porte de ejemplo")
    pdf.p(
        "Fecha 13/08/2025. Grano: Maiz. Origen: Intendente Alvear (La Pampa). "
        "Destino: Puerto Gral. San Martin (Santa Fe). Planta 512428. Campania 2425."
    )
    if IMG_DST.exists():
        pdf.image(str(IMG_DST), w=pdf.w - pdf.l_margin - pdf.r_margin)
        pdf.ln(3)

    pdf.add_page()
    pdf.h2("2. Flujo de negocio")
    pdf.p("Campo (productor) -> cadena comercial -> transporte -> planta destino (COFCO).")
    pdf.bullet("Origen: campo en Intendente Alvear, La Pampa. Entrega: Rep. entregador Gualtieri.")
    pdf.bullet("1a venta comercial: Viterra (Rte. Com. Venta Primaria).")
    pdf.bullet(
        "2a venta: FYO Acopio (Rte. Com. Venta Secundaria), con corredor "
        "Futuros y Opciones.com y Mercado a Termino A3."
    )
    pdf.bullet("Transporte: Barbesini / chofer Parra. Dominios JII026 y AF495WZ. 454 km.")
    pdf.bullet("Destino: COFCO International, planta 512428, Puerto Gral. San Martin, Santa Fe.")

    diagrama = DOCS / "flujo-cpe-maiz-cofco.png"
    if diagrama.exists():
        pdf.add_page()
        pdf.h2("2.b Diagrama de flujo")
        pdf.p(
            "Campo → cadena comercial (Viterra / FYO / A3 / corredor) → "
            "transporte → planta COFCO."
        )
        max_w = pdf.w - pdf.l_margin - pdf.r_margin
        # dejar margen inferior para que no lo corte el page-break
        max_h = pdf.h - pdf.get_y() - 20
        pdf.image(str(diagrama), w=max_w, h=max_h, keep_aspect_ratio=True)
        pdf.ln(2)

    pdf.add_page()
    pdf.h2("3. Intervinientes (significado de negocio)")
    pdf.table(
        ["Rol", "CUIT", "Razon social", "Significado"],
        [
            [
                "Rte. Com. Venta Primaria",
                "33502232229",
                "VITERRA ARGENTINA S.A.",
                "Comercializa la 1a venta del grano",
            ],
            [
                "Rte. Com. Venta Secundaria",
                "30711855641",
                "FYO ACOPIO S.A.",
                "Reventa entre comerciales (2a venta)",
            ],
            [
                "Mercado a Termino",
                "30525698412",
                "A3 MERCADOS S.A.",
                "Mercado de futuros del contrato",
            ],
            [
                "Corredor Venta Secundaria",
                "30703605105",
                "FUTUROS Y OPCIONES.COM S.A.",
                "Broker de la venta secundaria",
            ],
            [
                "Rep. entregador",
                "30711962766",
                "GUALTIERI E HIJOS S.R.L.",
                "Representa quien entrega en origen",
            ],
            [
                "Destinatario / Destino",
                "33506737449",
                "COFCO INTERNATIONAL ARGENTINA S.A.",
                "Titular de la mercaderia y planta de descarga",
            ],
            [
                "Transportista",
                "20237684436",
                "BARBESINI CLAUDIO OSCAR",
                "Empresa responsable del flete",
            ],
            [
                "Chofer",
                "20388082802",
                "PARRA PAOLO MAXIMILIANO",
                "Conductor del camion",
            ],
        ],
        [42, 28, 55, 65],
    )

    pdf.h3("Roles tachados / vacios en el PDF")
    pdf.bullet("Titular CPE: quien emite/autoriza la carta.")
    pdf.bullet("Remitente Comercial Productor: productor o comercial en origen.")
    pdf.bullet("Flete pagador: quien paga el flete.")
    pdf.bullet("Corredor venta primaria / Rep. recibidor: vacios en este ejemplo.")

    pdf.add_page()
    pdf.h2("4. Codigos de catalogo (homologacion)")
    pdf.table(
        ["Concepto", "Codigo", "Descripcion"],
        [
            ["Tipo CPE", "74", "Automotor"],
            ["Provincia origen", "21", "LA PAMPA"],
            ["Localidad origen", "6975", "INTENDENTE ALVEAR"],
            ["Provincia destino", "12", "SANTA FE"],
            ["Localidad destino", "11797", "PUERTO GRAL SAN MARTIN"],
            ["Grano", "19", "Maiz"],
            ["Planta destino", "512428", "Del PDF COFCO (en homo puede no existir)"],
            ["Cosecha", "2425", "Campania 24/25"],
            ["Peso bruto / tara", "45000 / 15000", "Neto 30000 (no se envia)"],
        ],
        [50, 40, 100],
    )

    pdf.h2("5. Servicios WSCPE")
    pdf.table(
        ["Paso", "Servicio", "Para que"],
        [
            ["1", "WSAA loginCms", "token + sign (service=wscpe)"],
            ["2", "consultarProvincias", "Codigos de provincia"],
            ["3", "consultarLocalidadesPorProvincia", "Localidades origen/destino"],
            ["4", "consultarTiposGrano", "Codigo Maiz = 19"],
            ["5", "consultarUltNroOrden", "Proximo nroOrden"],
            ["6", "consultarPlantas", "Validar nroPlanta (opcional)"],
            ["7", "autorizarCPEAutomotor", "Generar CPE / CTG / PDF"],
        ],
        [15, 70, 105],
    )
    pdf.p(
        "Importante: SOAPAction debe ser la URL de la operacion "
        '(ej. "https://serviciosjava.afip.gob.ar/wscpe/consultarProvincias"). '
        "Si va vacio, WSCPE responde error de autenticacion aunque el TA sea valido."
    )

    pdf.h2("6. Endpoints homologacion")
    pdf.bullet("WSAA: https://wsaahomo.afip.gov.ar/ws/services/LoginCms")
    pdf.bullet("WSCPE: https://cpea-ws-qaext.afip.gob.ar/wscpe/services/soap")
    pdf.bullet("WSDL: https://cpea-ws-qaext.afip.gob.ar/wscpe/services/soap?wsdl")
    pdf.bullet("Manual: https://www.arca.gob.ar/ws/documentos/manual_wscpe_v2-0-5.pdf")

    pdf.add_page()
    pdf.h2("7. Payload autorizarCPEAutomotor (estructura)")
    pdf.p('SOAPAction: "https://serviciosjava.afip.gob.ar/wscpe/autorizarCPEAutomotor"')
    pdf.set_font("Doc", "", 8)
    pdf._reset_x()
    pdf.multi_cell(
        0,
        4.2,
        """cabecera: tipoCP=74, cuitSolicitante, sucursal, nroOrden
origen.productor: codProvincia=21, codLocalidad=6975 (+ renspa/GPS si aplica)
correspondeRetiroProductor=true | esSolicitanteCampo=false
retiroProductor.cuitRemitenteComercialProductor = (tachado en PDF)
intervinientes:
  ventaPrimaria=33502232229 | ventaSecundaria=30711855641
  mercadoATermino=30525698412 | corredorSecundaria=30703605105
  repEntregador=30711962766
datosCarga: codGrano=19, cosecha=2425, pesoBruto=45000, pesoTara=15000
destino: cuit=33506737449, esDestinoCampo=false, prov=12, loc=11797, planta=512428
destinatario.cuit=33506737449
transporte:
  transportista=20237684436 | dominios JII026 + AF495WZ
  partida=2025-08-13T20:00:00 | km=454 | turno=COSM6752-14082025
  chofer=20388082802 | tarifa=41000 | pagadorFlete=(tachado)
  mercaderiaFumigada=false""",
    )
    pdf.ln(2)

    pdf.h2("8. Lo que genera ARCA (no va en el request)")
    pdf.bullet("CTG, N° CPE, vencimiento, QR / PDF")
    pdf.bullet("Peso neto (bruto - tara)")
    pdf.bullet("Historial post-confirmacion")
    pdf.p(
        "La descarga en destino (seccion G del PDF) es otro flujo: "
        "confirmacionDefinitiva / descargadoDestino, etc."
    )

    pdf.h2("9. Notas de homologacion")
    pdf.bullet("Pedir set de prueba a sri@arca.gob.ar; CUITs reales pueden rechazarse en testing.")
    pdf.bullet("Planta 512428 es de produccion; en homo usar nroPlanta de consultarPlantas.")
    pdf.bullet("Si WSAA dice coe.alreadyAuthenticated, reutilizar el TA vigente (~12 h).")
    pdf.bullet("Coleccion Postman: postman/arca-wscpe/")

    pdf.h2("10. Archivos en el repo")
    pdf.bullet("postman/arca-wscpe/ARCA-WSCPE.postman_collection.json")
    pdf.bullet("postman/arca-wscpe/Homologacion.postman_environment.json")
    pdf.bullet("postman/arca-wscpe/README.md")
    pdf.bullet("postman/arca-wscpe/scripts/generar_cms_wsaa.py")
    pdf.bullet("postman/arca-wscpe/docs/carta-porte-ejemplo.png")
    pdf.bullet("postman/arca-wscpe/docs/WSCPE-mapeo-cpe-automotor-ejemplo.pdf")

    pdf.output(str(OUT))
    print(f"PDF escrito: {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
