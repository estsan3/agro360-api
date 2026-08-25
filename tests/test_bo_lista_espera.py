"""Tests unitarios de la capa BO de lista de espera (sin base de datos)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.excepciones import ReglaDeNegocioViolada
from app.modulos.lista_espera.bo import ListaEsperaBO, RequisitosViaje
from app.modulos.lista_espera.models import EntradaLista


@pytest.fixture
def bo() -> ListaEsperaBO:
    return ListaEsperaBO()


def _entrada(
    *,
    anotado_en: datetime,
    capacidad_tn: float = 30,
    tipo_unidad: str = "tolva",
    estado: str = "en_espera",
) -> EntradaLista:
    return EntradaLista(
        empresa_id="default",
        transportista_id="t-x",
        camion_id="cm-x",
        chofer_id="ch-x",
        capacidad_tn=capacidad_tn,
        tipo_unidad=tipo_unidad,
        estado=estado,
        anotado_en=anotado_en,
    )


def test_fifo_elige_el_mas_antiguo(bo):
    ahora = datetime.now(UTC)
    tarde = _entrada(anotado_en=ahora)
    temprano = _entrada(anotado_en=ahora - timedelta(hours=1))
    elegido = bo.elegir_siguiente([tarde, temprano], RequisitosViaje(toneladas=20))
    assert elegido is temprano


def test_incompatible_por_capacidad(bo):
    entrada = _entrada(anotado_en=datetime.now(UTC), capacidad_tn=10)
    assert bo.elegir_siguiente([entrada], RequisitosViaje(toneladas=30)) is None


def test_incompatible_por_tipo(bo):
    entrada = _entrada(anotado_en=datetime.now(UTC), tipo_unidad="cisterna")
    assert (
        bo.elegir_siguiente(
            [entrada], RequisitosViaje(toneladas=10, tipo_unidad="tolva")
        )
        is None
    )


def test_flota_propia_no_se_anota(bo):
    with pytest.raises(ReglaDeNegocioViolada):
        bo.validar_anotacion_no_propia(True)


def test_mandar_al_fondo_limpia_oferta(bo):
    ahora = datetime.now(UTC)
    entrada = _entrada(anotado_en=ahora - timedelta(hours=2), estado="ofertado")
    entrada.viaje_ofertado_id = "v-1"
    entrada.ofertado_en = ahora - timedelta(minutes=20)
    bo.mandar_al_fondo(entrada, ahora)
    assert entrada.estado == "en_espera"
    assert entrada.viaje_ofertado_id is None
    assert entrada.anotado_en == ahora


def test_timeout_detecta_oferta_vencida(bo):
    ahora = datetime.now(UTC)
    entrada = _entrada(anotado_en=ahora, estado="ofertado")
    entrada.ofertado_en = ahora - timedelta(minutes=20)
    assert bo.oferta_vencida(entrada, ahora, timeout_minutos=15)


def test_asignar_requiere_oferta(bo):
    entrada = _entrada(anotado_en=datetime.now(UTC), estado="en_espera")
    with pytest.raises(ReglaDeNegocioViolada):
        bo.marcar_asignada(entrada, "v-1")
