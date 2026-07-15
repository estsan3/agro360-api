"""Capa BO del módulo despachos: reglas del ciclo de vida de campañas y viajes.

Reglas principales del dominio:
- Una campaña nace en `borrador` y pasa a `activo` al "enviarse".
- Solo se puede activar una campaña que tenga al menos un viaje.
- Una campaña activa no puede eliminarse.
- Una campaña activa se `cierra` cuando todos sus viajes están `completado`.
- Las campañas cerradas no admiten nuevas operaciones sobre viajes.
- Transiciones de viaje válidas:
    borrador   → pendiente | en_viaje   (al activar la campaña / iniciar)
    pendiente  → en_viaje
    en_viaje   → retrasado | completado
    retrasado  → en_viaje | completado
    completado → (final, sin salida)
"""

from app.core.excepciones import ReglaDeNegocioViolada
from app.modulos.despachos.models import Despacho, Viaje

# Grafo de transiciones válidas de estado de un viaje.
_TRANSICIONES_VIAJE: dict[str, set[str]] = {
    "borrador": {"pendiente", "en_viaje"},
    "pendiente": {"en_viaje"},
    "en_viaje": {"retrasado", "completado"},
    "retrasado": {"en_viaje", "completado"},
    "completado": set(),
}

# Estados en los que un viaje todavía no salió a la ruta.
_ESTADOS_SIN_INICIAR = {"borrador", "pendiente"}


class DespachoBO:
    """Reglas de negocio de campañas y viajes."""

    def validar_fechas(self, despacho: Despacho) -> None:
        """La llegada estimada no puede ser anterior al inicio."""
        if despacho.fecha_llegada_estimada < despacho.fecha_inicio:
            raise ReglaDeNegocioViolada(
                "La fecha de llegada estimada no puede ser anterior a la de inicio"
            )

    def validar_activacion(self, despacho: Despacho) -> None:
        """Solo se activa una campaña en borrador y con viajes cargados."""
        if despacho.estado == "activo":
            raise ReglaDeNegocioViolada("La campaña ya está activa")
        if not despacho.viajes:
            raise ReglaDeNegocioViolada(
                "No se puede activar una campaña sin viajes cargados"
            )

    def validar_eliminacion(self, despacho: Despacho) -> None:
        """Las campañas activas o cerradas no se eliminan."""
        if despacho.estado in {"activo", "cerrado"}:
            raise ReglaDeNegocioViolada("No se puede eliminar una campaña activa o cerrada")

    def validar_campaña_operable(self, despacho: Despacho) -> None:
        """Bloquea mutaciones sobre campañas ya cerradas."""
        if despacho.estado == "cerrado":
            raise ReglaDeNegocioViolada("La campaña está cerrada")

    def validar_cierre(self, despacho: Despacho) -> None:
        """Solo se cierra una campaña activa con todos los viajes completados."""
        if despacho.estado != "activo":
            raise ReglaDeNegocioViolada("Solo se pueden cerrar campañas activas")
        if not despacho.viajes:
            raise ReglaDeNegocioViolada("No se puede cerrar una campaña sin viajes")
        incompletos = [viaje for viaje in despacho.viajes if viaje.estado != "completado"]
        if incompletos:
            raise ReglaDeNegocioViolada(
                f"Quedan {len(incompletos)} viaje(s) sin completar"
            )

    def cerrar(self, despacho: Despacho) -> None:
        """Marca la campaña como cerrada (archivada operativamente)."""
        self.validar_cierre(despacho)
        despacho.estado = "cerrado"

    def validar_edicion_metadatos(self, despacho: Despacho) -> None:
        """Metadatos editables solo en campañas activas."""
        if despacho.estado != "activo":
            raise ReglaDeNegocioViolada(
                "Solo se pueden ajustar metadatos de campañas activas"
            )

    def validar_transicion_viaje(self, viaje: Viaje, nuevo_estado: str) -> None:
        """Verifica que el cambio de estado del viaje sea una transición válida."""
        if nuevo_estado == viaje.estado:
            return  # Sin cambio: operación idempotente.
        permitidos = _TRANSICIONES_VIAJE.get(viaje.estado, set())
        if nuevo_estado not in permitidos:
            raise ReglaDeNegocioViolada(
                f"Transición inválida: {viaje.estado} → {nuevo_estado}"
            )

    def aplicar_estado_viaje(self, viaje: Viaje, nuevo_estado: str) -> None:
        """Aplica el cambio de estado con sus efectos derivados."""
        self.validar_transicion_viaje(viaje, nuevo_estado)
        viaje.estado = nuevo_estado
        # Un viaje completado siempre queda con progreso 100.
        if nuevo_estado == "completado":
            viaje.progreso = 100

    def validar_inicio_viaje(self, viaje: Viaje) -> None:
        """Para salir a la ruta el viaje necesita chofer asignado."""
        if viaje.chofer_id is None:
            raise ReglaDeNegocioViolada(
                "No se puede iniciar un viaje sin chofer asignado"
            )

    def validar_eliminacion_viaje(self, viaje: Viaje) -> None:
        """Solo se eliminan viajes que todavía no salieron a la ruta."""
        if viaje.estado not in _ESTADOS_SIN_INICIAR:
            raise ReglaDeNegocioViolada(
                f"No se puede eliminar un viaje en estado {viaje.estado}"
            )

    def validar_edicion(self, despacho: Despacho) -> None:
        """Solo se editan campañas en borrador (las activas están en operación)."""
        if despacho.estado == "activo":
            raise ReglaDeNegocioViolada("No se puede editar una campaña activa")

    def activar(self, despacho: Despacho) -> None:
        """Activa la campaña y promueve sus viajes borrador a pendiente."""
        self.validar_activacion(despacho)
        despacho.estado = "activo"
        for viaje in despacho.viajes:
            if viaje.estado == "borrador":
                viaje.estado = "pendiente"
