"""Tests BO de prioridad flota propia vs lista en despachos."""

from app.modulos.catalogos.contrato import UnidadFlotaResumen
from app.modulos.despachos.bo import DespachoBO


def _unidad(chofer_id: str, capacidad: float = 35) -> UnidadFlotaResumen:
    return UnidadFlotaResumen(
        transportista_id="t-propia",
        transportista_nombre="Propia",
        es_flota_propia=True,
        chofer_id=chofer_id,
        chofer_nombre="Chofer",
        camion_id=f"cm-{chofer_id}",
        dominio="AA111AA",
        capacidad_tn=capacidad,
        tipo_unidad="tolva",
    )


def test_flota_propia_gana_si_hay_libre():
    bo = DespachoBO()
    unidades = [_unidad("ch-1"), _unidad("ch-2")]
    elegida = bo.elegir_flota_propia(unidades, set(), toneladas=30)
    assert elegida is not None
    assert elegida.chofer_id == "ch-1"


def test_flota_propia_omite_ocupados_e_incompatibles():
    bo = DespachoBO()
    unidades = [_unidad("ch-1", capacidad=10), _unidad("ch-2", capacidad=40)]
    elegida = bo.elegir_flota_propia(
        unidades, choferes_ocupados={"ch-2"}, toneladas=30
    )
    assert elegida is None


def test_flota_propia_salta_ocupado_al_siguiente():
    bo = DespachoBO()
    unidades = [_unidad("ch-1"), _unidad("ch-2")]
    elegida = bo.elegir_flota_propia(
        unidades, choferes_ocupados={"ch-1"}, toneladas=30
    )
    assert elegida is not None
    assert elegida.chofer_id == "ch-2"
