"""Tests del armado/validación del payload AFIP (sin DB ni HTTP)."""

from datetime import UTC, datetime

import pytest

from app.core.excepciones import ReglaDeNegocioViolada
from app.modulos.cartas_porte.payload import DatosParaPayloadCPE, validar_y_armar_payload


def _datos(**overrides) -> DatosParaPayloadCPE:
    base = dict(
        tipo_cpe=74,
        sucursal=1,
        cosecha=2526,
        cuit_solicitante="30712345678",
        origen_cod_provincia=12,
        origen_cod_localidad=1234,
        origen_planta=None,
        origen_nro_renspa=None,
        origen_latitud=-32.95,
        origen_longitud=-60.65,
        cuit_productor="20111222333",
        corresponde_retiro_productor=True,
        es_solicitante_campo=True,
        cod_grano=23,
        peso_bruto_kg=45000,
        peso_tara_kg=15000,
        destino_cuit="30555666777",
        destino_es_campo=False,
        destino_cod_provincia=12,
        destino_cod_localidad=5678,
        destino_planta=100,
        cuit_transportista="30799888777",
        dominio="AB123CD",
        fecha_hora_partida=datetime(2026, 8, 5, 8, 0, tzinfo=UTC),
        km_recorrer=250,
        cuit_chofer="20333444555",
        tarifa=12010.0,
        cuit_pagador_flete=None,
        cuit_intermediario_flete=None,
        mercaderia_fumigada=False,
        codigo_turno=None,
        material_nombre="Soja",
        origen_descripcion="Campo Norte",
        destino_descripcion="Timbúes",
        despacho_nombre="Campaña demo",
    )
    base.update(overrides)
    return DatosParaPayloadCPE(**base)


def test_payload_automotor_completo():
    payload = validar_y_armar_payload(_datos())
    assert payload["tipo_cpe"] == 74
    assert payload["metodo_wscpe"] == "autorizarCPEAutomotor"
    assert payload["datos_carga"]["cod_grano"] == 23
    assert payload["datos_carga"]["peso_neto"] == 30000
    assert payload["transporte"]["dominio"] == ["AB123CD"]
    assert payload["destino"]["planta"] == 100
    assert "coordenadas_gps" in payload["origen"]


def test_payload_flete_corto():
    payload = validar_y_armar_payload(_datos(tipo_cpe=274))
    assert payload["tipo_cpe"] == 274
    assert payload["_meta"]["tipo_cpe_etiqueta"] == "Automotor flete corto"


def test_rechaza_tipo_no_soportado():
    with pytest.raises(ReglaDeNegocioViolada):
        validar_y_armar_payload(_datos(tipo_cpe=75))


def test_rechaza_destino_planta_sin_codigo():
    with pytest.raises(ReglaDeNegocioViolada, match="planta"):
        validar_y_armar_payload(_datos(destino_es_campo=False, destino_planta=None))


def test_cuit_invalido():
    with pytest.raises(ReglaDeNegocioViolada, match="CUIT"):
        validar_y_armar_payload(_datos(cuit_chofer="123"))


def test_mapeo_soap_autorizar_incluye_campos_wscpe():
    from app.modulos.cartas_porte.adaptadores.mapeo_soap import armar_solicitud_automotor

    payload = validar_y_armar_payload(_datos())
    xml = armar_solicitud_automotor(payload, nro_orden=7)
    assert "<tipoCP>74</tipoCP>" in xml
    assert "<nroOrden>7</nroOrden>" in xml
    assert "<codGrano>23</codGrano>" in xml
    assert "<dominio>AB123CD</dominio>" in xml
    assert "<cuitPagadorFlete>30712345678</cuitPagadorFlete>" in xml
    assert "<productor>" in xml
    assert "<coordenadasGPS>" in xml
    assert "<latitud><grados>-32</grados>" in xml
    assert "<longitud><grados>-60</grados>" in xml
    assert "<destinatario>" in xml
    assert "<esSolicitanteCampo>true</esSolicitanteCampo>" in xml
    assert "<nroRenspa>" not in xml
    assert "<codigoTurno>" not in xml


def test_payload_incluye_renspa_y_turno():
    payload = validar_y_armar_payload(
        _datos(origen_nro_renspa="12.345.6.78901/00", codigo_turno="COSM6752-14082025")
    )
    assert payload["origen"]["nro_renspa"] == "12.345.6.78901/00"
    assert payload["transporte"]["codigo_turno"] == "COSM6752-14082025"

    from app.modulos.cartas_porte.adaptadores.mapeo_soap import armar_solicitud_automotor

    xml = armar_solicitud_automotor(payload, nro_orden=1)
    assert "<nroRenspa>12.345.6.78901/00</nroRenspa>" in xml
    assert "<codigoTurno>COSM6752-14082025</codigoTurno>" in xml


def test_payload_incluye_acoplado_vs2_y_cuit_productor():
    payload = validar_y_armar_payload(
        _datos(
            dominio_acoplado="AF495WZ",
            cuit_remitente_comercial_venta_secundaria_2="30700000002",
            cuit_remitente_comercial_productor="20111222333",
        )
    )
    assert payload["transporte"]["dominio"] == ["AB123CD", "AF495WZ"]
    assert payload["intervinientes"]["cuit_remitente_comercial_venta_secundaria_2"] == "30700000002"
    assert payload["intervinientes"]["cuit_remitente_comercial_productor"] == "20111222333"

    from app.modulos.cartas_porte.adaptadores.mapeo_soap import armar_solicitud_automotor

    xml = armar_solicitud_automotor(payload, nro_orden=1)
    assert xml.count("<dominio>") == 2
    assert "<dominio>AF495WZ</dominio>" in xml
    assert (
        "<cuitRemitenteComercialVentaSecundaria2>30700000002"
        "</cuitRemitenteComercialVentaSecundaria2>"
    ) in xml
    assert (
        "<cuitRemitenteComercialProductor>20111222333</cuitRemitenteComercialProductor>"
    ) in xml


def test_mapeo_soap_origen_operador_si_no_es_campo():
    from app.modulos.cartas_porte.adaptadores.mapeo_soap import armar_solicitud_automotor

    payload = validar_y_armar_payload(
        _datos(es_solicitante_campo=False, origen_planta=10)
    )
    xml = armar_solicitud_automotor(payload, nro_orden=2)
    assert "<operador>" in xml
    assert "<planta>10</planta>" in xml
    assert "<productor>" not in xml


def test_mapeo_soap_anular():
    from app.modulos.cartas_porte.adaptadores.mapeo_soap import armar_solicitud_anular

    xml = armar_solicitud_anular(74, 1, 3)
    assert "<tipoCPE>74</tipoCPE>" in xml
    assert "<sucursal>1</sucursal>" in xml
    assert "<nroOrden>3</nroOrden>" in xml
