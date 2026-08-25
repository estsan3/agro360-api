"""Casuística Agro360 a partir de cartas de porte reales (WSCPE).

Datos ilegibles/tachados en el PDF llevan prefijo ``sim-`` en el *nombre*
(razón social). Los CUIT siguen siendo 11 dígitos (requisito AFIP/Agro360);
si el CUIT también estaba ilegible se inventa uno sintético documentado
en ``simulado=True``.

Ejemplos:
  #1 Maíz → COFCO (Puerto Gral. San Martín)
  #2 Soja → LDC (General Lagos)
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.modulos.cartas_porte.models import CartaPorte
from app.modulos.catalogos.models import (
    Camion,
    Campo,
    Chofer,
    Productor,
    PuntoEntrada,
    Transportista,
)
from app.modulos.despachos.models import Despacho, Viaje

# ---------------------------------------------------------------------------
# Constantes de códigos ARCA (homologación)
# ---------------------------------------------------------------------------

PROV_LA_PAMPA = 21
LOC_INTENDENTE_ALVEAR = 6975
PROV_SANTA_FE = 12
LOC_PUERTO_GRAL_SAN_MARTIN = 11797
LOC_GENERAL_LAGOS = 6381
GRANO_MAIZ = 19
GRANO_SOJA = 23


def _cuit_sim(indice: int) -> str:
    """CUIT sintético 11 dígitos para datos ilegibles (no lleva 'sim-' en el número)."""
    return f"30999{indice:06d}"


# ---------------------------------------------------------------------------
# Catálogos de la casuística
# ---------------------------------------------------------------------------

def construir_catalogos_casuistica() -> tuple[
    list[Productor], list[Transportista], list[Chofer]
]:
    """Productores, transportistas, choferes y camiones de las 2 CPE."""
    # --- Ejemplo #1 Maíz/COFCO ---
    # Titular / productor / flete pagador tachados → sim-
    p_maiz = Productor(
        id="p-cpe-maiz",
        nombre="sim-Productor Intendente Alvear (CPE Maíz)",
        cuit=_cuit_sim(1),
        activo=True,
        datos_ui={
            "nombre_fantasia": "sim-Productor Intendente Alvear",
            "razon_social": "sim-Productor Intendente Alvear SA",
            "notas": "CUIT y razón social ilegibles en PDF CPE Maíz→COFCO; datos simulados.",
            "casuistica_cpe": "maiz-cofco",
            "simulado": True,
        },
        campos=[
            Campo(
                id="c-cpe-maiz",
                nombre="Campo Intendente Alvear (LP)",
                productor_id="p-cpe-maiz",
                activo=True,
                datos_ui={
                    "codigo": "CPA-6975",
                    "localidad": "INTENDENTE ALVEAR",
                    "provincia": "LA PAMPA",
                    "partido": "Chapaleufú",
                    "latitud": -35.340556,  # approx 35°20'26''
                    "longitud": -63.578333,  # approx 63°34'42''
                    "cod_provincia_arca": PROV_LA_PAMPA,
                    "cod_localidad_arca": LOC_INTENDENTE_ALVEAR,
                },
                puntos_entrada=[
                    PuntoEntrada(
                        id="pe-cpe-maiz-1",
                        campo_id="c-cpe-maiz",
                        nombre="Entrada principal",
                        latitud=-35.340556,
                        longitud=-63.578333,
                        orden=1,
                    )
                ],
            )
        ],
    )

    t_barbesini = Transportista(
        id="t-cpe-barbesini",
        nombre="Barbesini Claudio Oscar",
        cuit="20237684436",
        activo=True,
        es_flota_propia=False,
        datos_ui={
            "razon_social": "BARBESINI CLAUDIO OSCAR",
            "casuistica_cpe": "maiz-cofco",
        },
        camiones=[
            Camion(
                id="cm-cpe-jii026",
                transportista_id="t-cpe-barbesini",
                dominio="JII026",
                modelo="Tractor + acoplado",
                activo=True,
                datos_ui={
                    "marca": "sim-Marca",
                    "tipo": "Tractor",
                    "acoplado_dominio": "AF495WZ",
                    "notas": "PDF trae 2 dominios; Agro360 solo persiste 1 (tractor).",
                },
            )
        ],
    )
    ch_parra = Chofer(
        id="ch-cpe-parra",
        nombre="Parra Paolo Maximiliano",
        transportista_id="t-cpe-barbesini",
        camion_id="cm-cpe-jii026",
        cuit="20388082802",
        activo=True,
        datos_ui={"nombre": "Paolo Maximiliano", "apellido": "Parra"},
    )

    # --- Ejemplo #2 Soja/LDC ---
    p_soja = Productor(
        id="p-cpe-soja",
        nombre="sim-SIEMBRAS TC-SMG (titular CPE Soja)",
        cuit="30716040530",  # flete pagador visible; titular ilegible → usamos este + sim- en nombre
        activo=True,
        datos_ui={
            "nombre_fantasia": "sim-SIEMBRAS TC-SMG",
            "razon_social": "sim-SIEMBRAS TC-SMG S.R.L.",
            "notas": (
                "Titular parcialmente ilegible en PDF (SIEMBRAS TC…). "
                "CUIT de flete pagador 30716040530 usado como solicitante simulado."
            ),
            "casuistica_cpe": "soja-ldc",
            "simulado": True,
            "cuit_flete_pagador_pdf": "30716040530",
        },
        campos=[
            Campo(
                id="c-cpe-soja",
                nombre="Campo Intendente Alvear (LP) — Soja",
                productor_id="p-cpe-soja",
                activo=True,
                datos_ui={
                    "codigo": "CPA-6975-SOJA",
                    "localidad": "INTENDENTE ALVEAR",
                    "provincia": "LA PAMPA",
                    "latitud": -35.340556,
                    "longitud": -63.578333,
                    "cod_provincia_arca": PROV_LA_PAMPA,
                    "cod_localidad_arca": LOC_INTENDENTE_ALVEAR,
                },
                puntos_entrada=[
                    PuntoEntrada(
                        id="pe-cpe-soja-1",
                        campo_id="c-cpe-soja",
                        nombre="Entrada campo",
                        latitud=-35.340556,
                        longitud=-63.578333,
                        orden=1,
                    )
                ],
            )
        ],
    )

    t_braidotti = Transportista(
        id="t-cpe-braidotti",
        nombre="Transportes Braidotti SRL",
        cuit="30649956746",
        activo=True,
        es_flota_propia=False,
        datos_ui={"razon_social": "TRANSPORTES BRAIDOTTI SRL", "casuistica_cpe": "soja-ldc"},
        camiones=[
            Camion(
                id="cm-cpe-ab646gl",
                transportista_id="t-cpe-braidotti",
                dominio="AB646GL",
                modelo="Tractor + acoplado",
                activo=True,
                datos_ui={
                    "tipo": "Tractor",
                    "acoplado_dominio": "AF232IV",
                    "notas": "Segundo dominio (acoplado) no tiene campo propio en Agro360.",
                },
            )
        ],
    )
    ch_torres = Chofer(
        id="ch-cpe-torres",
        nombre="Torres Dario Alberto",
        transportista_id="t-cpe-braidotti",
        camion_id="cm-cpe-ab646gl",
        cuit="23247746099",
        activo=True,
        datos_ui={"nombre": "Dario Alberto", "apellido": "Torres"},
    )

    return (
        [p_maiz, p_soja],
        [t_barbesini, t_braidotti],
        [ch_parra, ch_torres],
    )


# ---------------------------------------------------------------------------
# Despachos + viajes
# ---------------------------------------------------------------------------

def construir_despachos_casuistica() -> list[Despacho]:
    """Dos campañas CPE listas para emitir intención / evaluar gaps."""
    d_maiz = Despacho(
        id="d-cpe-maiz-cofco",
        nombre="CPE casuística Maíz → COFCO (PDF real)",
        productor_id="p-cpe-maiz",
        campo_id="c-cpe-maiz",
        origen="Intendente Alvear, La Pampa",
        entrada_campo="Entrada principal",
        material="Maíz",
        administrador_id="a-1",
        vendedor_id="v-1",
        fecha_inicio=date(2025, 8, 13),
        fecha_llegada_estimada=date(2025, 8, 18),
        estado="activo",
        dador_viaje="sim-Dador viaje (ilegible PDF)",
        tarifa_por_tn=41000.0,
        distancia_km=454.0,
        cuando="fecha",
        cuando_fecha=date(2025, 8, 13),
        observaciones=(
            "Casuística desde PDF CPE Automotor Maíz→COFCO. "
            "Campos sim-* = ilegibles/tachados en el documento."
        ),
        cpe_habilitada=True,
        cpe_tipo=74,
        cpe_sucursal=1,
        cpe_cosecha=2425,
        cpe_cuit_solicitante=_cuit_sim(1),  # titular ilegible
        cpe_origen_cod_provincia=PROV_LA_PAMPA,
        cpe_origen_cod_localidad=LOC_INTENDENTE_ALVEAR,
        cpe_corresponde_retiro_productor=True,
        cpe_es_solicitante_campo=False,
        cpe_destino_cuit="33506737449",
        cpe_destino_es_campo=False,
        cpe_destino_cod_provincia=PROV_SANTA_FE,
        cpe_destino_cod_localidad=LOC_PUERTO_GRAL_SAN_MARTIN,
        cpe_destino_planta=512428,
        cpe_peso_tara_kg_default=15000,
        cpe_mercaderia_fumigada=False,
        cpe_cuit_pagador_flete=_cuit_sim(2),  # flete pagador tachado
        cpe_cuit_remitente_comercial_vp="33502232229",
        cpe_cuit_remitente_comercial_vs="30711855641",
        cpe_cuit_mercado_a_termino="30525698412",
        cpe_cuit_corredor_vs="30703605105",
        cpe_cuit_representante_entregador="30711962766",
        viajes=[
            Viaje(
                id="viaje-cpe-maiz-1",
                chofer_id="ch-cpe-parra",
                chofer_nombre="Parra Paolo Maximiliano",
                dominio="JII026",
                destino="COFCO — Puerto Gral. San Martín (planta 512428)",
                toneladas=30.0,  # neto
                estado="pendiente",
                progreso=0,
                observaciones=(
                    "Acoplado AF495WZ no modelado. "
                    "Turno COSM6752-14082025 no tiene campo en campaña/viaje."
                ),
                cpe_destino_cuit="33506737449",
                cpe_destino_es_campo=False,
                cpe_destino_cod_provincia=PROV_SANTA_FE,
                cpe_destino_cod_localidad=LOC_PUERTO_GRAL_SAN_MARTIN,
                cpe_destino_planta=512428,
                cpe_peso_bruto_kg=45000,
                cpe_peso_tara_kg=15000,
            )
        ],
    )

    d_soja = Despacho(
        id="d-cpe-soja-ldc",
        nombre="CPE casuística Soja → LDC General Lagos (PDF real)",
        productor_id="p-cpe-soja",
        campo_id="c-cpe-soja",
        origen="Intendente Alvear, La Pampa",
        entrada_campo="Entrada campo",
        material="Soja",
        administrador_id="a-1",
        vendedor_id="v-1",
        fecha_inicio=date(2025, 12, 13),
        fecha_llegada_estimada=date(2025, 12, 15),
        estado="activo",
        dador_viaje="sim-SIEMBRAS TC-SMG",
        tarifa_por_tn=30000.0,
        distancia_km=450.0,
        cuando="fecha",
        cuando_fecha=date(2025, 12, 13),
        observaciones=(
            "Casuística desde PDF CPE Automotor Soja→LDC. "
            "Cadena comercial vacía (sin VP/VS/MAT/corredor)."
        ),
        cpe_habilitada=True,
        cpe_tipo=74,
        cpe_sucursal=1,
        cpe_cosecha=2526,  # no legible en PDF; simulado temporada
        cpe_cuit_solicitante="30716040530",
        cpe_origen_cod_provincia=PROV_LA_PAMPA,
        cpe_origen_cod_localidad=LOC_INTENDENTE_ALVEAR,
        cpe_corresponde_retiro_productor=True,
        cpe_es_solicitante_campo=True,
        cpe_destino_cuit="30526712729",
        cpe_destino_es_campo=False,
        cpe_destino_cod_provincia=PROV_SANTA_FE,
        cpe_destino_cod_localidad=LOC_GENERAL_LAGOS,
        cpe_destino_planta=21030,
        cpe_peso_tara_kg_default=15000,
        cpe_mercaderia_fumigada=False,
        cpe_cuit_pagador_flete="30716040530",
        cpe_cuit_representante_entregador=_cuit_sim(3),  # CUIT ilegible REALES…
        viajes=[
            Viaje(
                id="viaje-cpe-soja-1",
                chofer_id="ch-cpe-torres",
                chofer_nombre="Torres Dario Alberto",
                dominio="AB646GL",
                destino="LDC — General Lagos (planta 21030)",
                toneladas=35.0,
                estado="pendiente",
                progreso=0,
                observaciones=(
                    "Rep. entregador: sim-REALES DE AE Y GD SRL (CUIT ilegible → "
                    f"{_cuit_sim(3)}). Acoplado AF232IV no modelado. "
                    "Turno LAG-SOJ-20251215-3876 sin campo en Agro360."
                ),
                cpe_destino_cuit="30526712729",
                cpe_destino_es_campo=False,
                cpe_destino_cod_provincia=PROV_SANTA_FE,
                cpe_destino_cod_localidad=LOC_GENERAL_LAGOS,
                cpe_destino_planta=21030,
                cpe_peso_bruto_kg=50000,
                cpe_peso_tara_kg=15000,
            )
        ],
    )
    return [d_maiz, d_soja]


def _payload_maiz() -> dict[str, Any]:
    return {
        "metodo_wscpe": "autorizarCPEAutomotor",
        "tipo_cpe": 74,
        "sucursal": 1,
        "cuit_solicitante": _cuit_sim(1),
        "origen": {
            "cod_provincia": PROV_LA_PAMPA,
            "cod_localidad": LOC_INTENDENTE_ALVEAR,
            "planta": None,
            "cuit_productor": _cuit_sim(1),
            "coordenadas_gps": {
                "latitud_decimal": -35.340556,
                "longitud_decimal": -63.578333,
            },
        },
        "flags": {
            "corresponde_retiro_productor": True,
            "es_solicitante_campo": False,
        },
        "intervinientes": {
            "cuit_remitente_comercial_venta_primaria": "33502232229",
            "cuit_remitente_comercial_venta_secundaria": "30711855641",
            "cuit_mercado_a_termino": "30525698412",
            "cuit_corredor_venta_secundaria": "30703605105",
            "cuit_representante_entregador": "30711962766",
            "cuit_remitente_comercial_productor": _cuit_sim(4),  # tachado; gap Agro360
        },
        "datos_carga": {
            "cod_grano": GRANO_MAIZ,
            "cosecha": 2425,
            "peso_bruto": 45000,
            "peso_tara": 15000,
            "peso_neto": 30000,
        },
        "destino": {
            "cuit": "33506737449",
            "es_destino_campo": False,
            "cod_provincia": PROV_SANTA_FE,
            "cod_localidad": LOC_PUERTO_GRAL_SAN_MARTIN,
            "planta": 512428,
        },
        "transporte": {
            "cuit_transportista": "20237684436",
            "dominio": ["JII026", "AF495WZ"],
            "fecha_hora_partida": "2025-08-13T20:00:00",
            "km_recorrer": 454,
            "codigo_turno": "COSM6752-14082025",
            "cuit_chofer": "20388082802",
            "tarifa": 41000,
            "cuit_pagador_flete": _cuit_sim(2),
            "mercaderia_fumigada": False,
        },
        "observaciones": "Casuística PDF Maíz→COFCO",
        "_meta": {
            "material_nombre": "Maíz",
            "origen_descripcion": "Intendente Alvear, La Pampa",
            "destino_descripcion": "COFCO Puerto Gral. San Martín",
            "casuistica": "maiz-cofco",
            "simulado": {
                "cuit_solicitante": True,
                "cuit_productor": True,
                "cuit_pagador_flete": True,
                "cuit_remitente_comercial_productor": True,
            },
            "gaps_agro360": [
                "codigo_turno no se captura en despacho/viaje (BO lo manda None)",
                "segundo dominio (acoplado) no tiene campo",
                "cuit_remitente_comercial_productor (retiro) no está en despacho",
                "nro_renspa origen no modelado",
                "fecha_hora_partida exacta (solo fecha campaña + 08:00 UTC)",
            ],
        },
    }


def _payload_soja() -> dict[str, Any]:
    return {
        "metodo_wscpe": "autorizarCPEAutomotor",
        "tipo_cpe": 74,
        "sucursal": 1,
        "cuit_solicitante": "30716040530",
        "origen": {
            "cod_provincia": PROV_LA_PAMPA,
            "cod_localidad": LOC_INTENDENTE_ALVEAR,
            "planta": None,
            "cuit_productor": "30716040530",
            "coordenadas_gps": {
                "latitud_decimal": -35.340556,
                "longitud_decimal": -63.578333,
            },
        },
        "flags": {
            "corresponde_retiro_productor": True,
            "es_solicitante_campo": True,
        },
        "intervinientes": {
            "cuit_representante_entregador": _cuit_sim(3),
        },
        "datos_carga": {
            "cod_grano": GRANO_SOJA,
            "cosecha": 2526,
            "peso_bruto": 50000,
            "peso_tara": 15000,
            "peso_neto": 35000,
        },
        "destino": {
            "cuit": "30526712729",
            "es_destino_campo": False,
            "cod_provincia": PROV_SANTA_FE,
            "cod_localidad": LOC_GENERAL_LAGOS,
            "planta": 21030,
        },
        "transporte": {
            "cuit_transportista": "30649956746",
            "dominio": ["AB646GL", "AF232IV"],
            "fecha_hora_partida": "2025-12-13T14:30:00",
            "km_recorrer": 450,
            "codigo_turno": "LAG-SOJ-20251215-3876",
            "cuit_chofer": "23247746099",
            "tarifa": 30000,
            "cuit_pagador_flete": "30716040530",
            "mercaderia_fumigada": False,
        },
        "observaciones": "Casuística PDF Soja→LDC",
        "_meta": {
            "material_nombre": "Soja",
            "origen_descripcion": "Intendente Alvear, La Pampa",
            "destino_descripcion": "LDC General Lagos",
            "ctg_pdf": "10128282729",
            "casuistica": "soja-ldc",
            "simulado": {
                "nombre_titular": True,
                "cuit_representante_entregador": True,
                "cosecha": True,
            },
            "gaps_agro360": [
                "codigo_turno no se captura en despacho/viaje",
                "segundo dominio (acoplado) no tiene campo",
                "hora exacta de partida (14:30) no se guarda",
            ],
        },
    }


def construir_cartas_casuistica() -> list[CartaPorte]:
    """Intenciones pendientes con payload completo de las 2 CPE."""
    return [
        CartaPorte(
            id="cpe-casuistica-maiz-cofco",
            despacho_id="d-cpe-maiz-cofco",
            viaje_id="viaje-cpe-maiz-1",
            tipo_cpe=74,
            nro_carta_porte=None,
            nro_ctg=None,
            estado="pendiente",
            material="Maíz",
            origen="Intendente Alvear, La Pampa",
            destino="COFCO — Puerto Gral. San Martín",
            dominio="JII026",
            toneladas=30.0,
            payload_afip=_payload_maiz(),
            intentos=0,
            error_detalle="",
        ),
        CartaPorte(
            id="cpe-casuistica-soja-ldc",
            despacho_id="d-cpe-soja-ldc",
            viaje_id="viaje-cpe-soja-1",
            tipo_cpe=74,
            nro_carta_porte=None,
            nro_ctg="10128282729",  # del PDF (ya emitida en prod; acá como referencia)
            estado="pendiente",
            material="Soja",
            origen="Intendente Alvear, La Pampa",
            destino="LDC — General Lagos",
            dominio="AB646GL",
            toneladas=35.0,
            payload_afip=_payload_soja(),
            intentos=0,
            error_detalle="",
        ),
    ]


# ---------------------------------------------------------------------------
# Gap analysis (CPE PDF → Agro360)
# ---------------------------------------------------------------------------

GAPS_CAMPOS: list[dict[str, str]] = [
    {
        "campo_cpe": "codigoTurno",
        "ejemplo": "COSM6752… / LAG-SOJ-…",
        "agro360": "No hay campo en Despacho/Viaje; BO manda codigo_turno=None",
        "estado": "FALTA",
    },
    {
        "campo_cpe": "dominio acoplado (2°)",
        "ejemplo": "AF495WZ / AF232IV",
        "agro360": "Viaje.dominio / Camion.dominio solo 1 patente",
        "estado": "FALTA",
    },
    {
        "campo_cpe": "fechaHoraPartida (hora)",
        "ejemplo": "20:00 / 14:30",
        "agro360": "Solo fecha (cuando/fecha_inicio) + hora fija 08:00 UTC en BO",
        "estado": "PARCIAL",
    },
    {
        "campo_cpe": "cuitRemitenteComercialProductor",
        "ejemplo": "retiroProductor (tachado en Maíz)",
        "agro360": "No existe en Despacho; solo flag corresponde_retiro_productor",
        "estado": "FALTA",
    },
    {
        "campo_cpe": "nroRenspa",
        "ejemplo": "origen productor",
        "agro360": "No modelado en Campo/Despacho",
        "estado": "FALTA",
    },
    {
        "campo_cpe": "cuitRemitenteComercialVentaSecundaria2",
        "ejemplo": "opcional WSCPE",
        "agro360": "No hay campo (solo VP y VS)",
        "estado": "FALTA",
    },
    {
        "campo_cpe": "intervinientes VP/VS/MAT/corredor/entregador",
        "ejemplo": "CUITs en pestaña CPE",
        "agro360": "Campos cpe_cuit_* en Despacho",
        "estado": "OK",
    },
    {
        "campo_cpe": "destino planta/prov/loc/cuit",
        "ejemplo": "512428 / 21030",
        "agro360": "cpe_destino_* + override en Viaje",
        "estado": "OK",
    },
    {
        "campo_cpe": "pesos bruto/tara",
        "ejemplo": "45000/15000",
        "agro360": "Viaje.cpe_peso_* + default tara campaña",
        "estado": "OK",
    },
    {
        "campo_cpe": "codGrano / cosecha",
        "ejemplo": "19 Maíz / 23 Soja",
        "agro360": "Material.codigo_grano_afip + cpe_cosecha",
        "estado": "OK",
    },
    {
        "campo_cpe": "GPS origen",
        "ejemplo": "lat/long campo",
        "agro360": "PuntoEntrada lat/lng → contexto CPE",
        "estado": "OK",
    },
    {
        "campo_cpe": "CTG / N° CPE / vencimiento / QR",
        "ejemplo": "respuesta ARCA",
        "agro360": "CartaPorte.nro_ctg / nro_carta_porte / pdf (post-autorizar)",
        "estado": "OK (respuesta)",
    },
]


def texto_gap_analisis_md() -> str:
    lineas = [
        "# Gap analysis: CPE PDF → Agro360",
        "",
        "Casuísticas sembradas: `d-cpe-maiz-cofco`, `d-cpe-soja-ldc`.",
        "Prefijo `sim-` en nombres = dato ilegible/tachado en el PDF (CUIT sintético aparte).",
        "",
        "| Campo CPE | Ejemplo | En Agro360 | Estado |",
        "|---|---|---|---|",
    ]
    for g in GAPS_CAMPOS:
        lineas.append(
            f"| {g['campo_cpe']} | {g['ejemplo']} | {g['agro360']} | **{g['estado']}** |"
        )
    lineas += [
        "",
        "## IDs útiles en la app",
        "",
        "| Entidad | ID |",
        "|---|---|",
        "| Despacho Maíz→COFCO | `d-cpe-maiz-cofco` |",
        "| Viaje Maíz | `viaje-cpe-maiz-1` |",
        "| Intención Maíz | `cpe-casuistica-maiz-cofco` |",
        "| Despacho Soja→LDC | `d-cpe-soja-ldc` |",
        "| Viaje Soja | `viaje-cpe-soja-1` |",
        "| Intención Soja | `cpe-casuistica-soja-ldc` |",
        "| Productor Maíz (sim) | `p-cpe-maiz` |",
        "| Productor Soja (sim) | `p-cpe-soja` |",
        "| Transportista Barbesini | `t-cpe-barbesini` |",
        "| Transportista Braidotti | `t-cpe-braidotti` |",
        "",
        "## Nota CUITs simulados",
        "",
        "AFIP/Agro360 exigen 11 dígitos. Por eso `sim-` va en el **nombre**, no en el CUIT.",
        f"- Titular/productor Maíz: `{_cuit_sim(1)}`",
        f"- Flete pagador Maíz: `{_cuit_sim(2)}`",
        f"- Rep. entregador Soja: `{_cuit_sim(3)}`",
        f"- Rte. Com. Productor Maíz (gap): `{_cuit_sim(4)}`",
        "",
    ]
    return "\n".join(lineas)
