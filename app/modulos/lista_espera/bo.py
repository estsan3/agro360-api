"""Capa BO del módulo lista de espera: FIFO, compatibilidad y rotación."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.excepciones import ReglaDeNegocioViolada
from app.modulos.lista_espera.models import EntradaLista

ESTADOS_ACTIVOS = {"en_espera", "ofertado"}
DEFAULT_TIMEOUT_MINUTOS = 15


@dataclass(frozen=True)
class RequisitosViaje:
    """Condiciones que debe cumplir una unidad para el viaje."""

    toneladas: float
    tipo_unidad: str | None = None


class ListaEsperaBO:
    """Reglas puras de la cola (sin DB ni HTTP)."""

    def validar_anotacion_no_propia(self, es_flota_propia: bool) -> None:
        if es_flota_propia:
            raise ReglaDeNegocioViolada(
                "La flota propia no se anota en la lista: se despacha con prioridad"
            )

    def ordenar_fifo(self, entradas: list[EntradaLista]) -> list[EntradaLista]:
        return sorted(entradas, key=lambda e: e.anotado_en)

    def es_compatible(self, entrada: EntradaLista, req: RequisitosViaje) -> bool:
        if entrada.capacidad_tn is not None and entrada.capacidad_tn < req.toneladas:
            return False
        if req.tipo_unidad and entrada.tipo_unidad:
            if entrada.tipo_unidad.lower() != req.tipo_unidad.lower():
                return False
        return True

    def filtrar_compatibles(
        self, entradas: list[EntradaLista], req: RequisitosViaje
    ) -> list[EntradaLista]:
        return [e for e in self.ordenar_fifo(entradas) if self.es_compatible(e, req)]

    def elegir_siguiente(
        self, entradas: list[EntradaLista], req: RequisitosViaje
    ) -> EntradaLista | None:
        aptos = [
            e
            for e in self.filtrar_compatibles(entradas, req)
            if e.estado == "en_espera"
        ]
        return aptos[0] if aptos else None

    def ofertar(
        self, entrada: EntradaLista, viaje_id: str, ahora: datetime
    ) -> None:
        if entrada.estado != "en_espera":
            raise ReglaDeNegocioViolada(
                f"Solo se ofrece a entradas en espera (actual: {entrada.estado})"
            )
        entrada.estado = "ofertado"
        entrada.viaje_ofertado_id = viaje_id
        entrada.ofertado_en = ahora

    def mandar_al_fondo(self, entrada: EntradaLista, ahora: datetime) -> None:
        """Rechazo o timeout: limpia oferta y pasa al final de la cola."""
        entrada.estado = "en_espera"
        entrada.viaje_ofertado_id = None
        entrada.ofertado_en = None
        entrada.anotado_en = ahora

    def marcar_asignada(self, entrada: EntradaLista, viaje_id: str) -> None:
        if entrada.estado != "ofertado":
            raise ReglaDeNegocioViolada(
                "Solo se asigna una entrada que esté en oferta"
            )
        if entrada.viaje_ofertado_id != viaje_id:
            raise ReglaDeNegocioViolada("La oferta no corresponde a ese viaje")
        entrada.estado = "fuera"
        entrada.viaje_asignado_id = viaje_id
        entrada.viaje_ofertado_id = None
        entrada.ofertado_en = None

    def reencolar(self, entrada: EntradaLista, ahora: datetime) -> None:
        """Al completar viaje: vuelve a la cola al final."""
        if entrada.estado not in {"fuera", "en_espera", "ofertado"}:
            raise ReglaDeNegocioViolada("Estado inválido para reencolar")
        entrada.estado = "en_espera"
        entrada.viaje_asignado_id = None
        entrada.viaje_ofertado_id = None
        entrada.ofertado_en = None
        entrada.anotado_en = ahora

    def oferta_vencida(
        self,
        entrada: EntradaLista,
        ahora: datetime,
        timeout_minutos: int = DEFAULT_TIMEOUT_MINUTOS,
    ) -> bool:
        if entrada.estado != "ofertado" or entrada.ofertado_en is None:
            return False
        ofertado = entrada.ofertado_en
        # SQLite puede devolver naive; normalizamos para comparar.
        if ofertado.tzinfo is None and ahora.tzinfo is not None:
            ofertado = ofertado.replace(tzinfo=ahora.tzinfo)
        elif ofertado.tzinfo is not None and ahora.tzinfo is None:
            ahora = ahora.replace(tzinfo=ofertado.tzinfo)
        return ahora >= ofertado + timedelta(minutes=timeout_minutos)

    def validar_quitar(self, entrada: EntradaLista) -> None:
        if entrada.estado == "ofertado":
            raise ReglaDeNegocioViolada(
                "No se puede quitar una unidad con oferta activa; rechace primero"
            )
