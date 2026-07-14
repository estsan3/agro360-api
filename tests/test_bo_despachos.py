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


def test_viaje_borrador_puede_iniciarse(bo):
    """borrador → en_viaje está permitido (iniciar desde la pantalla de borradores)."""
    viaje = Viaje(estado="borrador", destino="x", toneladas=1, chofer_id="ch-1")
    bo.aplicar_estado_viaje(viaje, "en_viaje")
    assert viaje.estado == "en_viaje"


def test_iniciar_sin_chofer_falla(bo):
    """Un viaje sin chofer asignado no puede salir a la ruta."""
    viaje = Viaje(estado="pendiente", destino="x", toneladas=1, chofer_id=None)
    with pytest.raises(ReglaDeNegocioViolada):
        bo.validar_inicio_viaje(viaje)


def test_eliminar_viaje_en_curso_falla(bo):
    """Solo se eliminan viajes que no salieron a la ruta."""
    viaje = Viaje(estado="en_viaje", destino="x", toneladas=1)
    with pytest.raises(ReglaDeNegocioViolada):
        bo.validar_eliminacion_viaje(viaje)


def test_activar_promueve_viajes_borrador(bo):
    """Al activar la campaña, los viajes borrador pasan a pendiente."""
    from app.modulos.despachos.models import Despacho

    despacho = Despacho(estado="borrador")
    despacho.viajes = [Viaje(estado="borrador", destino="x", toneladas=1)]
    bo.activar(despacho)
    assert despacho.estado == "activo"
    assert despacho.viajes[0].estado == "pendiente"
