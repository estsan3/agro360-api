"""Tests unitarios de la capa BO de despachos (sin base de datos).

Muestran la ventaja de separar las reglas en BO: se testean con objetos
en memoria, sin infraestructura.
"""

import pytest

from app.core.excepciones import ReglaDeNegocioViolada
from app.modulos.despachos.bo import DespachoBO
from app.modulos.despachos.models import Viaje


@pytest.fixture
def bo() -> DespachoBO:
    return DespachoBO()


def test_transicion_valida(bo):
    """pendiente → en_viaje es una transición permitida."""
    viaje = Viaje(estado="pendiente", destino="x", toneladas=1)
    bo.aplicar_estado_viaje(viaje, "en_viaje")
    assert viaje.estado == "en_viaje"


def test_transicion_invalida(bo):
    """pendiente → completado no está permitido (debe pasar por en_viaje)."""
    viaje = Viaje(estado="pendiente", destino="x", toneladas=1)
    with pytest.raises(ReglaDeNegocioViolada):
        bo.aplicar_estado_viaje(viaje, "completado")


def test_completado_es_final(bo):
    """Un viaje completado no puede volver a ningún otro estado."""
    viaje = Viaje(estado="completado", destino="x", toneladas=1, progreso=100)
    with pytest.raises(ReglaDeNegocioViolada):
        bo.aplicar_estado_viaje(viaje, "en_viaje")


def test_completar_fuerza_progreso_100(bo):
    """Al completar, el progreso queda en 100 aunque viniera menor."""
    viaje = Viaje(estado="en_viaje", destino="x", toneladas=1, progreso=80)
    bo.aplicar_estado_viaje(viaje, "completado")
    assert viaje.progreso == 100


def test_mismo_estado_es_idempotente(bo):
    """Repetir el mismo estado no lanza error (operación idempotente)."""
    viaje = Viaje(estado="en_viaje", destino="x", toneladas=1, progreso=50)
    bo.aplicar_estado_viaje(viaje, "en_viaje")
    assert viaje.estado == "en_viaje"
