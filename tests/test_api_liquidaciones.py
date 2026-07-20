"""Tests de integración API liquidaciones."""

import uuid

import pytest
from httpx import AsyncClient

from app.core.database import fabrica_sesiones
from app.modulos.catalogos.models import Transportista


@pytest.fixture
async def transportista_id() -> str:
    async with fabrica_sesiones() as sesion:
        sufijo = uuid.uuid4().hex[:8]
        t = Transportista(
            nombre=f"Transporte Test Ctacte {sufijo}",
            cuit=f"20-{sufijo[:8]}-1",
            activo=True,
        )
        sesion.add(t)
        await sesion.commit()
        return t.id


@pytest.mark.asyncio
async def test_parametros_y_movimiento_manual(
    cliente: AsyncClient, auth_headers: dict[str, str], transportista_id: str
) -> None:
    params = await cliente.get("/api/v1/liquidaciones/parametros", headers=auth_headers)
    assert params.status_code == 200
    body = params.json()
    assert body["tarifa_flete_por_tn"] == 15000.0
    assert body["comision_porcentaje"] == 8.0

    crear = await cliente.post(
        "/api/v1/liquidaciones/movimientos",
        headers=auth_headers,
        json={
            "transportista_id": transportista_id,
            "concepto": "gasoil",
            "detalle": "Factura de gasoil test",
            "debe": 50000,
            "haber": 0,
        },
    )
    assert crear.status_code == 200
    assert crear.json()["debe"] == 50000

    resumen = await cliente.get(
        f"/api/v1/liquidaciones/cuentas/{transportista_id}",
        headers=auth_headers,
    )
    assert resumen.status_code == 200
    data = resumen.json()
    assert data["totales_debe"] == 50000
    assert data["saldo_final"] == -50000
    assert len(data["movimientos"]) == 1

    cuentas = await cliente.get("/api/v1/liquidaciones/cuentas", headers=auth_headers)
    assert cuentas.status_code == 200
    assert any(c["transportista_id"] == transportista_id for c in cuentas.json())

    mov_id = crear.json()["id"]
    editar = await cliente.put(
        f"/api/v1/liquidaciones/movimientos/{mov_id}",
        headers=auth_headers,
        json={
            "fecha": "2026-07-15",
            "detalle": "Gasoil editado",
            "dador_viaje": "",
            "comprobante": "AN-EDIT",
            "debe": 40000,
            "haber": 0,
        },
    )
    assert editar.status_code == 200
    assert editar.json()["detalle"] == "Gasoil editado"
    assert editar.json()["debe"] == 40000

    borrar = await cliente.delete(
        f"/api/v1/liquidaciones/movimientos/{mov_id}",
        headers=auth_headers,
    )
    assert borrar.status_code == 204

    resumen_vacio = await cliente.get(
        f"/api/v1/liquidaciones/cuentas/{transportista_id}",
        headers=auth_headers,
    )
    assert resumen_vacio.json()["movimientos"] == []


@pytest.mark.asyncio
async def test_crear_flete_genera_conceptos_automaticos(
    cliente: AsyncClient, auth_headers: dict[str, str], transportista_id: str
) -> None:
    """30 tn × 10000: Haber flete+IVA; Debe comisión 8% + IVA + Ley 0,6%."""
    crear = await cliente.post(
        "/api/v1/liquidaciones/fletes",
        headers=auth_headers,
        json={
            "transportista_id": transportista_id,
            "detalle": "Flete a Rosario",
            "toneladas": 30,
            "tarifa": 10000,
            "dador_viaje": "Campo Demo",
        },
    )
    assert crear.status_code == 200
    lineas = crear.json()
    assert len(lineas) == 5
    por_concepto = {m["concepto"]: m for m in lineas}
    assert por_concepto["flete"]["haber"] == 300000.0
    assert por_concepto["flete"]["debe"] == 0.0
    assert por_concepto["iva_flete"]["haber"] == 63000.0
    assert por_concepto["comision"]["debe"] == 24000.0  # 8% de 300000
    assert por_concepto["iva_comision"]["debe"] == 5040.0
    assert por_concepto["ley_25413"]["debe"] == 2178.0  # 0,6% de (300000+63000)

    resumen = await cliente.get(
        f"/api/v1/liquidaciones/cuentas/{transportista_id}",
        headers=auth_headers,
    )
    assert resumen.status_code == 200
    data = resumen.json()
    assert data["totales_haber"] == 363000.0
    assert data["totales_debe"] == 31218.0
    assert data["saldo_final"] == 331782.0
