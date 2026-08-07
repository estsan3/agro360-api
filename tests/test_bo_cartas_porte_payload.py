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
