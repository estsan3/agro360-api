"""Capa BO del módulo despachos: reglas del ciclo de vida de campañas y viajes.

Reglas principales del dominio:
- Una campaña nace en `borrador` y pasa a `activo` al "enviarse".
- Solo se puede activar una campaña que tenga al menos un viaje.
- Una campaña activa no puede eliminarse.
- Una campaña activa se `cierra` cuando todos sus viajes están `completado`.
- Las campañas cerradas no admiten nuevas operaciones sobre viajes.
- Transiciones de viaje válidas:
    borrador   → pendiente | en_viaje | en_busqueda_transportistas
    en_busqueda_transportistas → borrador | pendiente
    pendiente  → en_viaje
    en_viaje   → retrasado | completado
    retrasado  → en_viaje | completado
    completado → (final, sin salida)
"""

from datetime import date, timedelta

from app.core.excepciones import ReglaDeNegocioViolada
from app.modulos.despachos.models import Despacho, Viaje

# Grafo de transiciones válidas de estado de un viaje.
_TRANSICIONES_VIAJE: dict[str, set[str]] = {
    "borrador": {"pendiente", "en_viaje", "en_busqueda_transportistas"},
    "en_busqueda_transportistas": {"borrador", "pendiente"},
    "pendiente": {"en_viaje", "en_busqueda_transportistas"},
    "en_viaje": {"retrasado", "completado"},
    "retrasado": {"en_viaje", "completado"},
    "completado": set(),
}

# Estados en los que un viaje todavía no salió a la ruta.
_ESTADOS_SIN_INICIAR = {"borrador", "pendiente", "en_busqueda_transportistas"}
_ESTADOS_ASIGNABLES_LISTA = {"borrador", "pendiente", "en_busqueda_transportistas"}


class DespachoBO:
    """Reglas de negocio de campañas y viajes."""

    def validar_fechas(self, despacho: Despacho) -> None:
        """La llegada estimada no puede ser anterior al inicio."""
        if despacho.fecha_llegada_estimada < despacho.fecha_inicio:
            raise ReglaDeNegocioViolada(
                "La fecha de llegada estimada no puede ser anterior a la de inicio"
            )

    def validar_asignacion_por_lista(self, viaje: Viaje) -> None:
        """El viaje debe poder recibir asignación automática."""
        if viaje.estado not in _ESTADOS_ASIGNABLES_LISTA:
            raise ReglaDeNegocioViolada(
                f"No se puede asignar por lista un viaje en estado {viaje.estado}"
            )
        if viaje.chofer_id and viaje.estado == "pendiente":
            raise ReglaDeNegocioViolada("El viaje ya tiene chofer asignado")

    @staticmethod
    def unidad_compatible(
        *,
        capacidad_tn: float | None,
        tipo_unidad: str,
        toneladas: float,
        tipo_requerido: str | None = None,
    ) -> bool:
        if capacidad_tn is not None and capacidad_tn < toneladas:
            return False
        if tipo_requerido and tipo_unidad.lower() != tipo_requerido.lower():
            return False
        return True

    def elegir_flota_propia(
        self,
        unidades: list,
        choferes_ocupados: set[str],
        toneladas: float,
        tipo_unidad: str | None = None,
    ):
        """Primera unidad propia libre y compatible (orden de lista recibida)."""
        for u in unidades:
            if u.chofer_id in choferes_ocupados:
                continue
            if not self.unidad_compatible(
                capacidad_tn=u.capacidad_tn,
                tipo_unidad=u.tipo_unidad,
                toneladas=toneladas,
                tipo_requerido=tipo_unidad,
            ):
                continue
            return u
        return None

    def validar_activacion(self, despacho: Despacho) -> None:
        """Solo se activa una campaña en borrador y con viajes cargados."""
        if despacho.estado == "activo":
            raise ReglaDeNegocioViolada("La campaña ya está activa")
        if not despacho.viajes:
            raise ReglaDeNegocioViolada(
                "No se puede activar una campaña sin viajes cargados"
            )
        sin_chofer = [v for v in despacho.viajes if not v.chofer_id]
        if sin_chofer:
            raise ReglaDeNegocioViolada(
                "No se puede activar: hay viajes sin chofer asignado"
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
        """Activa la campaña y promueve viajes borrador/búsqueda a pendiente."""
        self.validar_activacion(despacho)
        despacho.estado = "activo"
        for viaje in despacho.viajes:
            if viaje.estado in {"borrador", "en_busqueda_transportistas"}:
                viaje.estado = "pendiente"

    def validar_busqueda_transportistas(self, despacho: Despacho) -> None:
        """Requisitos comerciales para publicar la oferta a transportistas.

        No exige viajes previos: si no hay, el service crea uno en búsqueda.
        """
        if despacho.estado not in {"borrador"}:
            raise ReglaDeNegocioViolada(
                "Solo se buscan transportistas en campañas en borrador"
            )
        if not (despacho.dador_viaje or "").strip():
            raise ReglaDeNegocioViolada("Indicar el dador de viaje")
        if despacho.tarifa_llena:
            if despacho.distancia_km is None or despacho.distancia_km <= 0:
                raise ReglaDeNegocioViolada("Tarifa llena requiere distancia en km")
            if despacho.tarifa_por_tn is None or despacho.tarifa_por_tn <= 0:
                raise ReglaDeNegocioViolada("No se pudo resolver la tarifa nacional")
        elif despacho.tarifa_por_tn is None or despacho.tarifa_por_tn <= 0:
            raise ReglaDeNegocioViolada("Indicar tarifa por tn o marcar tarifa llena")
        if despacho.cuando == "fecha" and despacho.cuando_fecha is None:
            raise ReglaDeNegocioViolada("Indicar la fecha de carga")

    def validar_datos_viaje_busqueda(
        self, destino: str | None, toneladas: float | None
    ) -> tuple[str, float]:
        """Destino y toneladas obligatorios para crear el viaje de búsqueda."""
        destino_limpio = (destino or "").strip()
        if len(destino_limpio) < 2:
            raise ReglaDeNegocioViolada(
                "Indicar destino de la carga para buscar transportistas"
            )
        if toneladas is None or toneladas <= 0:
            raise ReglaDeNegocioViolada(
                "Indicar toneladas de la carga para buscar transportistas"
            )
        return destino_limpio, float(toneladas)

    @staticmethod
    def resolver_tarifa_por_km(
        distancia_km: float, tramos: list[tuple[float, float, float]]
    ) -> float:
        """Devuelve precio $/tn del tramo que contiene la distancia."""
        for km_desde, km_hasta, precio in tramos:
            if km_desde <= distancia_km <= km_hasta:
                return precio
        raise ReglaDeNegocioViolada(
            f"No hay tarifa nacional configurada para {distancia_km} km"
        )

    @staticmethod
    def formatear_cuando(cuando: str, cuando_fecha: date | None, hoy: date) -> str:
        """Texto legible para el mensaje de oferta."""
        if cuando == "ahora":
            return "Ahora"
        if cuando == "manana":
            manana = hoy + timedelta(days=1)
            return f"Mañana ({manana.strftime('%d/%m/%Y')})"
        if cuando_fecha is None:
            return "Fecha a confirmar"
        # Nombre del día en español (simple).
        dias = (
            "Lunes",
            "Martes",
            "Miércoles",
            "Jueves",
            "Viernes",
            "Sábado",
            "Domingo",
        )
        nombre = dias[cuando_fecha.weekday()]
        return f"{nombre} ({cuando_fecha.strftime('%d/%m/%Y')})"

    @staticmethod
    def armar_mensaje_oferta(
        *,
        material: str,
        cuando_texto: str,
        origen: str,
        destino: str,
        tarifa_por_tn: float,
        tarifa_llena: bool,
        dador_viaje: str,
        toneladas: float,
    ) -> str:
        """Plantilla del 'agente' de búsqueda (sin LLM)."""
        monto = f"{tarifa_por_tn:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        tarifa_txt = (
            f"${monto}/tn (tarifa llena FADEEAC)" if tarifa_llena else f"${monto}/tn"
        )
        return (
            f"Oferta de carga\n"
            f"Tipo de carga: {material}\n"
            f"Cuando: {cuando_texto}\n"
            f"Origen: {origen}\n"
            f"Destino: {destino}\n"
            f"Tarifa: {tarifa_txt}\n"
            f"Dador: {dador_viaje}\n"
            f"Toneladas: {toneladas:g}"
        )
