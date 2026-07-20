"""Tests unitarios del BO de liquidaciones."""

from app.modulos.liquidaciones.bo import LiquidacionesBO


def test_calcular_movimientos_flete_basico() -> None:
    lineas = LiquidacionesBO.calcular_movimientos_flete(
        toneladas=30.0,
        tarifa=10000.0,
        comision_pct=10.0,
        iva_pct=21.0,
        ley_pct=0.6,
    )
    conceptos = {c: (d, h) for c, d, h in lineas}
    assert conceptos["flete"] == (0.0, 300000.0)
    assert conceptos["iva_flete"] == (0.0, 63000.0)
    assert conceptos["comision"] == (30000.0, 0.0)
    assert conceptos["iva_comision"] == (6300.0, 0.0)
    assert conceptos["ley_25413"] == (2178.0, 0.0)


def test_saldo_corrido() -> None:
    saldos = LiquidacionesBO.calcular_saldo_corrido(
        0.0,
        [(0.0, 100.0), (40.0, 0.0), (0.0, 20.0)],
    )
    assert saldos == [100.0, 60.0, 80.0]
