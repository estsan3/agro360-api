#!/usr/bin/env python3
"""Genera PNGs de diagrama de flujo para las CPE de ejemplo."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DOCS = Path(__file__).resolve().parents[1] / "docs"

# Colores planos (sin gradientes)
BG = (250, 250, 248)
INK = (30, 30, 30)
MUTED = (90, 90, 90)
LINE = (60, 60, 60)
BOX_FILL = (255, 255, 255)
BOX_BORDER = (40, 40, 40)
GROUP_FILL = (245, 245, 242)
GROUP_BORDER = (180, 180, 175)
ACCENT = (34, 94, 60)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
        tw, _ = _text_size(draw, test, font)
        if tw <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _draw_box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    title: str,
    lines: list[str],
    font_title: ImageFont.ImageFont,
    font_body: ImageFont.ImageFont,
) -> None:
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=8, fill=BOX_FILL, outline=BOX_BORDER, width=2)
    pad = 10
    draw.text((x1 + pad, y1 + pad), title, font=font_title, fill=ACCENT)
    ty = y1 + pad + 18
    for line in lines:
        for wrapped in _wrap(draw, line, font_body, x2 - x1 - 2 * pad):
            draw.text((x1 + pad, ty), wrapped, font=font_body, fill=INK)
            ty += 14


def _arrow(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, label: str = "") -> None:
    draw.line((x1, y1, x2, y2), fill=LINE, width=2)
    # arrow head
    if abs(x2 - x1) >= abs(y2 - y1):
        # horizontal
        direction = 1 if x2 > x1 else -1
        draw.polygon(
            [(x2, y2), (x2 - 8 * direction, y2 - 5), (x2 - 8 * direction, y2 + 5)],
            fill=LINE,
        )
    else:
        direction = 1 if y2 > y1 else -1
        draw.polygon(
            [(x2, y2), (x2 - 5, y2 - 8 * direction), (x2 + 5, y2 - 8 * direction)],
            fill=LINE,
        )
    if label:
        font = _font(11)
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2
        tw, th = _text_size(draw, label, font)
        draw.rectangle((mx - tw // 2 - 4, my - th - 10, mx + tw // 2 + 4, my - 2), fill=BG)
        draw.text((mx - tw // 2, my - th - 8), label, font=font, fill=MUTED)


def _group(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    title: str,
    font: ImageFont.ImageFont,
) -> None:
    draw.rounded_rectangle(xy, radius=12, fill=GROUP_FILL, outline=GROUP_BORDER, width=1)
    draw.text((xy[0] + 12, xy[1] + 8), title, font=font, fill=MUTED)


def generar_maiz_cofco(path: Path) -> None:
    w, h = 1400, 820
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    ft = _font(13, bold=True)
    fb = _font(12)
    fg = _font(14, bold=True)
    ftitle = _font(20, bold=True)

    draw.text((40, 24), "Flujo CPE Automotor — Ejemplo #1 Maíz → COFCO", font=ftitle, fill=INK)
    draw.text(
        (40, 54),
        "Intendente Alvear (LP) → Puerto Gral. San Martín (SF) · Planta 512428",
        font=fb,
        fill=MUTED,
    )

    # Groups
    _group(draw, (40, 100, 340, 400), "ORIGEN — Campo", fg)
    _group(draw, (380, 100, 900, 400), "CADENA COMERCIAL", fg)
    _group(draw, (940, 100, 1360, 400), "TRANSPORTE", fg)
    _group(draw, (480, 460, 1100, 760), "DESTINO", fg)

    # Origen boxes
    _draw_box(
        draw,
        (60, 140, 320, 230),
        "Productor / Rte. Com. Productor",
        ["(tachado en el PDF)"],
        ft,
        fb,
    )
    _draw_box(
        draw,
        (60, 250, 320, 340),
        "Localidad origen",
        ["Intendente Alvear · LA PAMPA", "loc 6975 · prov 21"],
        ft,
        fb,
    )
    _draw_box(
        draw,
        (60, 360, 320, 450),
        "Rep. entregador",
        ["Gualtieri e Hijos", "30711962766"],
        ft,
        fb,
    )

    # Comercial
    _draw_box(
        draw,
        (400, 140, 630, 250),
        "Rte. Com. Venta Primaria",
        ["Viterra", "33502232229"],
        ft,
        fb,
    )
    _draw_box(
        draw,
        (650, 140, 880, 250),
        "Rte. Com. Venta Secundaria",
        ["FYO Acopio", "30711855641"],
        ft,
        fb,
    )
    _draw_box(
        draw,
        (400, 280, 630, 380),
        "Corredor Venta Secundaria",
        ["Futuros y Opciones.com", "30703605105"],
        ft,
        fb,
    )
    _draw_box(
        draw,
        (650, 280, 880, 380),
        "Mercado a Término",
        ["A3 Mercados", "30525698412"],
        ft,
        fb,
    )

    # Transporte
    _draw_box(
        draw,
        (960, 140, 1340, 240),
        "Transportista",
        ["Barbesini · 20237684436"],
        ft,
        fb,
    )
    _draw_box(
        draw,
        (960, 260, 1340, 340),
        "Chofer",
        ["Parra · 20388082802"],
        ft,
        fb,
    )
    _draw_box(
        draw,
        (960, 360, 1340, 440),
        "Dominios",
        ["JII026 · AF495WZ · 454 km"],
        ft,
        fb,
    )

    # Destino
    _draw_box(
        draw,
        (520, 510, 860, 620),
        "Destinatario / Destino",
        ["COFCO International", "33506737449"],
        ft,
        fb,
    )
    _draw_box(
        draw,
        (880, 510, 1060, 720),
        "Planta 512428",
        ["Puerto Gral. San Martín", "SF · loc 11797 · prov 12"],
        ft,
        fb,
    )

    # Arrows
    _arrow(draw, 320, 185, 400, 195, "1ª venta")
    _arrow(draw, 630, 195, 650, 195, "2ª venta")
    _arrow(draw, 765, 250, 765, 280, "intermedia")
    _arrow(draw, 880, 195, 960, 190, "despacha")
    _arrow(draw, 1150, 440, 1150, 510, "")
    _arrow(draw, 690, 400, 690, 510, "flete")
    _arrow(draw, 860, 565, 880, 565, "")

    img.save(path, "PNG")
    print(f"OK {path}")


def generar_soja_ldc(path: Path) -> None:
    w, h = 1400, 780
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    ft = _font(13, bold=True)
    fb = _font(12)
    fg = _font(14, bold=True)
    ftitle = _font(20, bold=True)

    draw.text((40, 24), "Flujo CPE Automotor — Ejemplo #2 Soja → LDC", font=ftitle, fill=INK)
    draw.text(
        (40, 54),
        "Intendente Alvear (LP) → General Lagos (SF) · Planta 21030 · Cadena comercial corta",
        font=fb,
        fill=MUTED,
    )

    _group(draw, (40, 100, 420, 420), "ORIGEN — Campo", fg)
    _group(draw, (460, 100, 900, 420), "EMISOR / ENTREGA", fg)
    _group(draw, (940, 100, 1360, 420), "TRANSPORTE", fg)
    _group(draw, (400, 480, 1100, 740), "DESTINO", fg)

    _draw_box(
        draw,
        (60, 140, 400, 250),
        "Campo / Productor",
        ["Intendente Alvear · LA PAMPA", "loc 6975 · prov 21", "GPS 35°20'26'' / 63°34'42''"],
        ft,
        fb,
    )
    _draw_box(
        draw,
        (60, 280, 400, 390),
        "Sin rte. comerciales",
        ["Sin venta primaria/secundaria", "Sin corredor ni mercado a término"],
        ft,
        fb,
    )

    _draw_box(
        draw,
        (480, 140, 880, 250),
        "Titular CPE / Flete pagador",
        ["SIEMBRAS TC-SMG S.R.L.", "Flete pagador 30716040530", "Titular parcialmente tachado"],
        ft,
        fb,
    )
    _draw_box(
        draw,
        (480, 280, 880, 390),
        "Rep. entregador",
        ["REALES DE AE Y GD SRL", "CUIT 307… (tachado parcial)"],
        ft,
        fb,
    )

    _draw_box(
        draw,
        (960, 140, 1340, 230),
        "Transportista",
        ["Transportes Braidotti SRL", "30649956746"],
        ft,
        fb,
    )
    _draw_box(
        draw,
        (960, 250, 1340, 330),
        "Chofer",
        ["Torres Darío Alberto", "23247746099"],
        ft,
        fb,
    )
    _draw_box(
        draw,
        (960, 350, 1340, 430),
        "Dominios / flete",
        ["AB646GL · AF232IV", "450 km · tarifa 30000"],
        ft,
        fb,
    )

    _draw_box(
        draw,
        (440, 530, 780, 650),
        "Destinatario / Destino",
        ["LDC ARGENTINA S.A.", "30526712729"],
        ft,
        fb,
    )
    _draw_box(
        draw,
        (800, 530, 1060, 700),
        "Planta 21030",
        ["General Lagos · SF", "loc 6381 · prov 12", "RP 21 km 16", "Turno LAG-SOJ-20251215-3876"],
        ft,
        fb,
    )

    _arrow(draw, 400, 195, 480, 195, "emite / paga flete")
    _arrow(draw, 680, 250, 680, 280, "entrega")
    _arrow(draw, 880, 195, 960, 185, "despacha")
    _arrow(draw, 1150, 430, 1150, 530, "flete")
    _arrow(draw, 610, 420, 610, 530, "")
    _arrow(draw, 780, 590, 800, 590, "")

    img.save(path, "PNG")
    print(f"OK {path}")


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    generar_maiz_cofco(DOCS / "flujo-cpe-maiz-cofco.png")
    generar_soja_ldc(DOCS / "flujo-cpe-soja-ldc.png")


if __name__ == "__main__":
    main()
