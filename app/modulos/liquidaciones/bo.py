"""Reglas de negocio puras de liquidaciones / cuenta corriente."""

from app.core.excepciones import ReglaDeNegocioViolada

CONCEPTOS_MANUALES = frozenset({"gasoil", "transferencia", "cheque", "anticipo", "ajuste"})


class LiquidacionesBO:
    """Cálculos y validaciones sin DB ni HTTP."""

    @staticmethod
    def calcular_movimientos_flete(
        toneladas: float,
        tarifa: float,
        comision_pct: float,
        iva_pct: float,
        ley_pct: float,
    ) -> list[tuple[str, float, float]]:
        """
        Devuelve (concepto, debe, haber) para un flete liquidado.

        Haber (a favor del transportista): flete + IVA flete.
        Debe (cargo de la transportadora): comisión + IVA comisión + Imp. Ley 25.413.
        Por defecto Ley 25.413 = 0,6 % (6‰ alícuota general); parametrizable.
        """
        neto = round(toneladas * tarifa, 2)
        iva_flete = round(neto * iva_pct / 100, 2)
        comision = round(neto * comision_pct / 100, 2)
        iva_comision = round(comision * iva_pct / 100, 2)
        ley = round((neto + iva_flete) * ley_pct / 100, 2)
        return [
            ("flete", 0.0, neto),
            ("iva_flete", 0.0, iva_flete),
            ("comision", comision, 0.0),
            ("iva_comision", iva_comision, 0.0),
            ("ley_25413", ley, 0.0),
        ]

    @staticmethod
    def calcular_saldo_corrido(
        saldo_inicial: float, movimientos: list[tuple[float, float]]
    ) -> list[float]:
        """Saldo tras cada movimiento: saldo = saldo - debe + haber."""
        saldos: list[float] = []
        saldo = saldo_inicial
        for debe, haber in movimientos:
            saldo = round(saldo - debe + haber, 2)
            saldos.append(saldo)
        return saldos

    @staticmethod
    def validar_movimiento_manual(concepto: str, debe: float, haber: float) -> None:
        if concepto not in CONCEPTOS_MANUALES:
            raise ReglaDeNegocioViolada(
                f"Concepto manual no permitido: {concepto}"
            )
        if (debe > 0) == (haber > 0):
            raise ReglaDeNegocioViolada(
                "El movimiento manual debe tener importe en debe o en haber, no en ambos"
            )
