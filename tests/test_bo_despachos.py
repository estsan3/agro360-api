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
    despacho.viajes = [
        Viaje(estado="borrador", destino="x", toneladas=1, chofer_id="ch-1")
    ]
    bo.activar(despacho)
    assert despacho.estado == "activo"
    assert despacho.viajes[0].estado == "pendiente"


def test_activar_sin_chofer_falla(bo):
    from app.modulos.despachos.models import Despacho

    despacho = Despacho(estado="borrador")
    despacho.viajes = [Viaje(estado="borrador", destino="x", toneladas=1)]
    with pytest.raises(ReglaDeNegocioViolada):
        bo.activar(despacho)


def test_resolver_tarifa_por_km(bo):
    tramos = [(0, 100, 25000.0), (101, 200, 40000.0)]
    assert bo.resolver_tarifa_por_km(80, tramos) == 25000.0
    assert bo.resolver_tarifa_por_km(150, tramos) == 40000.0
    with pytest.raises(ReglaDeNegocioViolada):
        bo.resolver_tarifa_por_km(500, tramos)


def test_busqueda_transportistas_valida(bo):
    from app.modulos.despachos.models import Despacho

    despacho = Despacho(
        estado="borrador",
        dador_viaje="COFCO",
        tarifa_llena=False,
        tarifa_por_tn=30000,
        cuando="ahora",
    )
    # Ya no exige viajes previos: el service los crea al buscar.
    despacho.viajes = []
    bo.validar_busqueda_transportistas(despacho)
    destino, toneladas = bo.validar_datos_viaje_busqueda("Rosario", 30)
    assert destino == "Rosario"
    assert toneladas == 30.0
    with pytest.raises(ReglaDeNegocioViolada):
        bo.validar_datos_viaje_busqueda("", 30)


def test_mensaje_oferta_plantilla(bo):
    from datetime import date

    texto = bo.armar_mensaje_oferta(
        material="Soja",
        cuando_texto=bo.formatear_cuando("ahora", None, date(2026, 7, 20)),
        origen="Pergamino",
        destino="Rosario",
        tarifa_por_tn=49240.0,
        tarifa_llena=True,
        dador_viaje="FEDEA",
        toneladas=32,
    )
    assert "Tipo de carga: Soja" in texto
    assert "Cuando: Ahora" in texto
    assert "tarifa llena FADEEAC" in texto
    assert "Dador: FEDEA" in texto


def test_cerrar_campaña_con_todos_completados(bo):
    from app.modulos.despachos.models import Despacho

    despacho = Despacho(estado="activo")
    despacho.viajes = [
        Viaje(estado="completado", destino="x", toneladas=1, progreso=100),
        Viaje(estado="completado", destino="y", toneladas=2, progreso=100),
    ]
    bo.cerrar(despacho)
    assert despacho.estado == "cerrado"


def test_cerrar_con_viajes_incompletos_falla(bo):
    from app.modulos.despachos.models import Despacho

    despacho = Despacho(estado="activo")
    despacho.viajes = [
        Viaje(estado="completado", destino="x", toneladas=1, progreso=100),
        Viaje(estado="en_viaje", destino="y", toneladas=2, progreso=50),
    ]
    with pytest.raises(ReglaDeNegocioViolada):
        bo.cerrar(despacho)


def test_campaña_cerrada_no_es_operable(bo):
    from app.modulos.despachos.models import Despacho

    despacho = Despacho(estado="cerrado")
    with pytest.raises(ReglaDeNegocioViolada):
        bo.validar_campaña_operable(despacho)


def test_edicion_metadatos_solo_activa(bo):
    from app.modulos.despachos.models import Despacho

    borrador = Despacho(estado="borrador")
    with pytest.raises(ReglaDeNegocioViolada):
        bo.validar_edicion_metadatos(borrador)

    activo = Despacho(estado="activo")
    bo.validar_edicion_metadatos(activo)


def test_cancelar_viaje(bo):
    viaje = Viaje(estado="pendiente", destino="x", toneladas=1)
    bo.cancelar_viaje(viaje)
    assert viaje.estado == "cancelado"


def test_cancelar_viaje_completado_falla(bo):
    viaje = Viaje(estado="completado", destino="x", toneladas=1, progreso=100)
    with pytest.raises(ReglaDeNegocioViolada):
        bo.cancelar_viaje(viaje)


def test_cerrar_campaña_con_cancelados(bo):
    from app.modulos.despachos.models import Despacho

    despacho = Despacho(estado="activo")
    despacho.viajes = [
        Viaje(estado="completado", destino="x", toneladas=1, progreso=100),
        Viaje(estado="cancelado", destino="y", toneladas=2),
    ]
    bo.cerrar(despacho)
    assert despacho.estado == "cerrado"


def test_reasignar_chofer_permitido(bo):
    viaje = Viaje(estado="en_viaje", destino="x", toneladas=1, chofer_id="ch-1")
    bo.validar_reasignacion_chofer(viaje)


def test_reasignar_chofer_completado_falla(bo):
    viaje = Viaje(estado="completado", destino="x", toneladas=1, progreso=100)
    with pytest.raises(ReglaDeNegocioViolada):
        bo.validar_reasignacion_chofer(viaje)
