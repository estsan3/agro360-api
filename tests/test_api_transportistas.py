"""Integración: CRUD de transportistas y camiones."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_transportistas_crud_y_catalogos_agregados(
    cliente: AsyncClient, auth_headers: dict[str, str]
) -> None:
    # Alta transportista
    respuesta = await cliente.post(
        "/api/v1/catalogos/transportistas",
        headers=auth_headers,
        json={"nombre": "Logística Test SA", "cuit": "30111222333"},
    )
    assert respuesta.status_code == 201
    transportista = respuesta.json()
    tid = transportista["id"]
    assert transportista["nombre"] == "Logística Test SA"
    assert transportista["camiones"] == []

    # Alta camión
    respuesta = await cliente.post(
        f"/api/v1/catalogos/transportistas/{tid}/camiones",
        headers=auth_headers,
        json={"dominio": "ZZ999ZZ", "modelo": "Scania R500"},
    )
    assert respuesta.status_code == 201
    flota = respuesta.json()["camiones"]
    assert len(flota) == 1
    assert flota[0]["dominio"] == "ZZ999ZZ"
    camion_id = flota[0]["id"]

    # GET agregado incluye transportistas
    catalogos = (await cliente.get("/api/v1/catalogos", headers=auth_headers)).json()
    assert "transportistas" in catalogos
    assert any(t["id"] == tid for t in catalogos["transportistas"])
    agg = next(t for t in catalogos["transportistas"] if t["id"] == tid)
    assert agg["camiones"][0]["dominio"] == "ZZ999ZZ"

    # Edición camión
    respuesta = await cliente.put(
        f"/api/v1/catalogos/transportistas/{tid}/camiones/{camion_id}",
        headers=auth_headers,
        json={"modelo": "Scania R500 XT"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["camiones"][0]["modelo"] == "Scania R500 XT"

    # Baja camión
    respuesta = await cliente.delete(
        f"/api/v1/catalogos/transportistas/{tid}/camiones/{camion_id}",
        headers=auth_headers,
    )
    assert respuesta.status_code == 204

    listado = (
        await cliente.get("/api/v1/catalogos/transportistas", headers=auth_headers)
    ).json()
    t = next(x for x in listado if x["id"] == tid)
    assert t["camiones"][0]["activo"] is False


@pytest.mark.asyncio
async def test_chofer_vinculado_a_transportista(
    cliente: AsyncClient, auth_headers: dict[str, str]
) -> None:
    transportista = (
        await cliente.post(
            "/api/v1/catalogos/transportistas",
            headers=auth_headers,
            json={"nombre": "Flota Chofer Test"},
        )
    ).json()
    tid = transportista["id"]

    chofer = (
        await cliente.post(
            f"/api/v1/catalogos/transportistas/{tid}/choferes",
            headers=auth_headers,
            json={"nombre": "Juan Chofer"},
        )
    ).json()
    assert chofer["transportista_id"] == tid

    catalogos = (await cliente.get("/api/v1/catalogos", headers=auth_headers)).json()
    agg = next(c for c in catalogos["choferes"] if c["id"] == chofer["id"])
    assert agg["transportista_id"] == tid
    assert agg["camiones"] == []
