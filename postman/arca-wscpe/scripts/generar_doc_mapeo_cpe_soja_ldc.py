#!/usr/bin/env python3
"""Genera PDF de documentación del mapeo CPE Automotor ejemplo #2 (Soja → LDC)."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

DOCS = Path(__file__).resolve().parents[1] / "docs"
IMG_SRC = Path(
    "/Users/estebansantamarina/.cursor/projects/"
    "Users-estebansantamarina-agro360-api/assets/"
    "WhatsApp_Image_2025-12-20_at_17.22.52-f80ce58d-ed25-46f2-a2c9-ffadf00b320b.png"
)
OUT = DOCS / "WSCPE-mapeo-cpe-automotor-ejemplo-soja-ldc.pdf"
IMG_DST = DOCS / "carta-porte-ejemplo-soja-ldc.png"

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]


class Doc(FPDF):
    def __init__(self, font_path: str) -> None:
        super().__init__()
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
            "Agro360 · WSCPE · CPE Automotor ejemplo #2 (Soja → LDC)",
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
                self.multi_cell(widths[i], line_h, str(cell), border=1, fill=fill)
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
    pdf.h2("Mapeo CPE Automotor ejemplo #2 — Soja → LDC General Lagos")
    pdf.p(
        "Proyecto Agro360. Ambiente de homologacion ARCA/AFIP. "
        "Mismo formato de analisis que el ejemplo Maiz→COFCO, aplicado a esta CPE."
    )
    pdf.p(
        "CPE = Carta de Porte Electronica. CTG de ejemplo: 10128282729. "
        "Vencimiento PDF: 15/12/2025."
    )

    pdf.h2("1. Carta de porte de ejemplo")
    pdf.p(
        "Fecha/partida 13/12/2025 14:30. Grano: Soja. "
        "Origen: Intendente Alvear (La Pampa). "
        "Destino: planta LDC 21030, General Lagos (Santa Fe), RP 21 km 16. "
        "Pesos: bruto 50000 / neto 35000 (tara 15000)."
    )
    if IMG_DST.exists():
        pdf.image(str(IMG_DST), w=pdf.w - pdf.l_margin - pdf.r_margin)
        pdf.ln(3)

    pdf.add_page()
    pdf.h2("2. Flujo de negocio")
    pdf.p(
        "Cadena mas corta que el ejemplo Viterra/FYO/COFCO: "
        "campo → titular/siembras → transporte → planta LDC."
    )
    pdf.bullet(
        "Origen: campo en Intendente Alvear, La Pampa. "
        "Coords PDF: lat 35° 20' 26'' / long 63° 34' 42''."
    )
    pdf.bullet(
        "Titular CPE / flete pagador: SIEMBRAS TC-SMG S.R.L. (30716040530 como flete pagador; "
        "titular parcialmente tachado, misma razon social)."
    )
    pdf.bullet(
        "Rep. entregador: REALES DE AE Y GD SRL (CUIT parcialmente tachado, empieza 307…)."
    )
    pdf.bullet(
        "Sin Rte. Com. Venta Primaria/Secundaria, sin corredor ni mercado a termino "
        "(campos vacios en el PDF)."
    )
    pdf.bullet(
        "Transporte: Transportes Braidotti SRL / chofer Torres Dario Alberto. "
        "Dominios AB646GL + AF232IV. 450 km. Tarifa 30000."
    )
    pdf.bullet(
        "Destino: LDC Argentina S.A. (30526712729), planta 21030, "
        "General Lagos, Santa Fe. Turno LAG-SOJ-20251215-3876."
    )

    diagrama = DOCS / "flujo-cpe-soja-ldc.png"
    if diagrama.exists():
        pdf.add_page()
        pdf.h2("2.b Diagrama de flujo")
        pdf.p(
            "Campo → titular/SIEMBRAS + rep. entregador → transporte Braidotti → "
            "planta LDC General Lagos."
        )
        max_w = pdf.w - pdf.l_margin - pdf.r_margin
        max_h = pdf.h - pdf.get_y() - 20
        pdf.image(str(diagrama), w=max_w, h=max_h, keep_aspect_ratio=True)
        pdf.ln(2)

    pdf.add_page()
    pdf.h2("3. Intervinientes (significado de negocio)")
    pdf.table(
        ["Rol", "CUIT", "Razon social", "Significado"],
        [
            [
                "Titular CPE",
                "(tachado)",
                "SIEMBRAS TC…",
                "Quien emite/autoriza la carta; dueño operativo del documento",
            ],
            [
                "Rep. entregador",
                "307… (tachado)",
                "REALES DE AE Y GD SRL",
                "Representa quien entrega el grano en origen",
            ],
            [
                "Destinatario / Destino",
                "30526712729",
                "LDC ARGENTINA S.A.",
                "Comprador/receptor y planta de descarga",
            ],
            [
                "Transportista",
                "30649956746",
                "TRANSPORTES BRAIDOTTI SRL",
                "Empresa responsable del flete",
            ],
            [
                "Flete pagador",
                "30716040530",
                "SIEMBRAS TC-SMG S.R.L.",
                "Quien paga el flete del viaje",
            ],
            [
                "Chofer",
                "23247746099",
                "TORRES DARIO ALBERTO",
                "Conductor del camion",
            ],
        ],
        [42, 28, 52, 68],
    )

    pdf.h3("Roles vacios en este PDF")
    pdf.bullet("Rte. Com. Productor / Venta Primaria / Venta Secundaria: sin cadena de reventas.")
    pdf.bullet("Mercado a Termino / Corredores / Rep. recibidor / Intermediario flete: vacios.")
    pdf.p(
        "En negocio: suele ser un traslado mas directo (productor/comercial propio → exportador), "
        "sin traders intermedios documentados en la CPE."
    )

    pdf.add_page()
    pdf.h2("4. Codigos de catalogo (homologacion WSCPE)")
    pdf.table(
        ["Concepto", "Codigo", "Descripcion"],
        [
            ["Tipo CPE", "74", "Automotor"],
            ["CTG (generado)", "10128282729", "Lo emite ARCA al autorizar"],
            ["Provincia origen", "21", "LA PAMPA"],
            ["Localidad origen", "6975", "INTENDENTE ALVEAR"],
            ["Provincia destino", "12", "SANTA FE"],
            ["Localidad destino", "6381", "GENERAL LAGOS"],
            ["Grano", "23", "Soja"],
            ["Planta destino", "21030", "LDC · RP 21 Km 16 (validada en consultarPlantas homo)"],
            ["Peso bruto / tara / neto", "50000 / 15000 / 35000", "Tara = bruto - neto"],
            ["Turno", "LAG-SOJ-20251215-3876", "codigoTurno"],
        ],
        [50, 45, 95],
    )
    pdf.p(
        "Planta 21030 en homo: codProvincia=12, codLocalidad=6381, "
        "ubicacionGeoreferencial='Ruta Provincial 21 Km 16' (coincide con el PDF)."
    )

    pdf.h2("5. Servicios WSCPE")
    pdf.table(
        ["Paso", "Servicio", "Para que"],
        [
            ["1", "WSAA loginCms", "token + sign (service=wscpe)"],
            ["2", "consultarProvincias", "21 La Pampa / 12 Santa Fe"],
            ["3", "consultarLocalidadesPorProvincia", "6975 Alvear / 6381 Gral. Lagos"],
            ["4", "consultarTiposGrano", "Soja = 23"],
            ["5", "consultarPlantas", "CUIT 30526712729 → planta 21030"],
            ["6", "consultarUltNroOrden", "Proximo nroOrden"],
            ["7", "autorizarCPEAutomotor", "Generar CPE / CTG / PDF"],
        ],
        [15, 70, 105],
    )
    pdf.p(
        "SOAPAction obligatorio con URL de operacion "
        '(ej. "https://serviciosjava.afip.gob.ar/wscpe/autorizarCPEAutomotor").'
    )

    pdf.h2("6. Endpoints homologacion")
    pdf.bullet("WSAA: https://wsaahomo.afip.gov.ar/ws/services/LoginCms")
    pdf.bullet("WSCPE: https://cpea-ws-qaext.afip.gob.ar/wscpe/services/soap")
    pdf.bullet("WSDL: https://cpea-ws-qaext.afip.gob.ar/wscpe/services/soap?wsdl")

    pdf.add_page()
    pdf.h2("7. Payload autorizarCPEAutomotor (estructura)")
    pdf.p('SOAPAction: "https://serviciosjava.afip.gob.ar/wscpe/autorizarCPEAutomotor"')
    pdf.set_font("Doc", "", 8)
    pdf._reset_x()
    pdf.multi_cell(
        0,
        4.2,
        """cabecera: tipoCP=74, cuitSolicitante=(titular SIEMBRAS / tachado), sucursal, nroOrden
origen.productor:
  codProvincia=21, codLocalidad=6975
  coordenadasGPS: lat 35°20'26'' / long 63°34'42'' (hemisferio S/O)
correspondeRetiroProductor: true (origen campo) | esSolicitanteCampo: segun titular
retiroProductor / intervinientes comerciales: vacios en PDF (omitir o solo rep entregador)
intervinientes:
  cuitRepresentanteEntregador = 307… REALES DE AE Y GD SRL (completar CUIT)
datosCarga: codGrano=23, cosecha=(no legible en PDF), pesoBruto=50000, pesoTara=15000
destino:
  cuit=30526712729, esDestinoCampo=false
  codProvincia=12, codLocalidad=6381, planta=21030
destinatario.cuit=30526712729
transporte:
  cuitTransportista=30649956746
  dominio AB646GL + AF232IV
  fechaHoraPartida=2025-12-13T14:30:00
  kmRecorrer=450 | codigoTurno=LAG-SOJ-20251215-3876
  cuitChofer=23247746099 | tarifa=30000
  cuitPagadorFlete=30716040530
  mercaderiaFumigada=false""",
    )
    pdf.ln(2)

    pdf.h2("8. Lo que genera ARCA (no va en el request)")
    pdf.bullet("CTG (en el PDF: 10128282729), N° CPE, vencimiento, QR / PDF")
    pdf.bullet("Peso neto")
    pdf.bullet("Historial post-confirmacion")
    pdf.p("Seccion G descarga: vacia al momento de la captura (pre-confirmacion en destino).")

    pdf.h2("9. Comparacion rapida vs ejemplo Maiz→COFCO")
    pdf.table(
        ["Tema", "Ejemplo #1 Maiz/COFCO", "Ejemplo #2 Soja/LDC"],
        [
            ["Grano", "Maiz (19)", "Soja (23)"],
            ["Destino", "COFCO 33506737449", "LDC 30526712729"],
            ["Planta", "512428 Puerto Gral San Martin (11797)", "21030 General Lagos (6381)"],
            ["Cadena comercial", "Viterra + FYO + A3 + corredor", "Sin rte/corredor/mercado"],
            ["Flete pagador", "Tachado", "SIEMBRAS 30716040530"],
            ["Km / tarifa", "454 / 41000", "450 / 30000"],
        ],
        [40, 75, 75],
    )

    pdf.h2("10. Notas de homologacion")
    pdf.bullet("Completar CUITs tachados (titular, rep. entregador) antes de autorizar.")
    pdf.bullet("Pedir set de prueba a sri@arca.gob.ar si CUITs reales fallan en testing.")
    pdf.bullet("Planta 21030 SI aparece en consultarPlantas homo para LDC.")
    pdf.bullet("Coleccion Postman: postman/arca-wscpe/")

    pdf.h2("11. Archivos en el repo")
    pdf.bullet("postman/arca-wscpe/docs/WSCPE-mapeo-cpe-automotor-ejemplo-soja-ldc.pdf")
    pdf.bullet("postman/arca-wscpe/docs/carta-porte-ejemplo-soja-ldc.png")
    pdf.bullet("postman/arca-wscpe/docs/WSCPE-mapeo-cpe-automotor-ejemplo.pdf (ejemplo #1)")
    pdf.bullet("postman/arca-wscpe/scripts/generar_doc_mapeo_cpe_soja_ldc.py")

    pdf.output(str(OUT))
    print(f"PDF escrito: {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
