"""Capa BO del módulo mensajería."""

from app.core.excepciones import ReglaDeNegocioViolada

AUTORES_VALIDOS = {"admin", "chofer", "sistema"}


class MensajeriaBO:
    """Reglas de negocio del chat admin ↔ chofer."""

    def validar_autor(self, autor: str) -> None:
        if autor not in AUTORES_VALIDOS:
            raise ReglaDeNegocioViolada(f"Autor inválido: {autor}")

    def calcular_no_leidos(self, no_leidos_actual: int, autor: str) -> int:
        """El contador de no leídos solo crece con mensajes del chofer.

        Los mensajes del admin no suman (él ya los vio) y los del sistema
        sí, porque son avisos que el admin debe atender.
        """
        if autor in ("chofer", "sistema"):
            return no_leidos_actual + 1
        return no_leidos_actual
