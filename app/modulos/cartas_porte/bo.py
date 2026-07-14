"""Capa BO del módulo cartas de porte."""

from app.core.excepciones import ReglaDeNegocioViolada
from app.modulos.cartas_porte.models import CartaPorte
from app.modulos.despachos.contrato import ViajeResumen


class CartaPorteBO:
    """Reglas de negocio para la emisión y anulación de CPE."""

    def validar_emision(
        self, viaje: ViajeResumen, cpe_vigente: CartaPorte | None
    ) -> None:
        """Un viaje solo puede tener una CPE autorizada a la vez y debe
        estar en condiciones de salir (chofer y dominio asignados)."""
        if cpe_vigente is not None:
            raise ReglaDeNegocioViolada(
                f"El viaje ya tiene una carta de porte autorizada "
                f"(nro {cpe_vigente.nro_carta_porte})"
            )
        if viaje.dominio in ("", "-"):
            raise ReglaDeNegocioViolada(
                "El viaje no tiene chofer/dominio asignado; asignalo antes de emitir"
            )
        if viaje.estado == "completado":
            raise ReglaDeNegocioViolada(
                "El viaje ya está completado; no corresponde emitir carta de porte"
            )

    def validar_anulacion(self, carta: CartaPorte) -> None:
        if carta.estado != "autorizada":
            raise ReglaDeNegocioViolada(
                f"Solo se puede anular una CPE autorizada (estado actual: {carta.estado})"
            )
