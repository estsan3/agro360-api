"""Integración: endpoints ABM /transportistas y /productores."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_productores_abm_flujo(cliente: AsyncClient, auth_headers: dict[str, str]) -> None:
    respuesta = await cliente.post(
        "/api/v1/productores",
        headers=auth_headers,
        json={
            "nombre_fantasia": "Productor ABM Test",
            "razon_social": "Productor ABM Test SA",
            "cuit": "30-11111111-1",
        },
    )
    assert respuesta.status_code == 201
    productor = respuesta.json()
    pid = productor["id"]
    assert productor["nombre_fantasia"] == "Productor ABM Test"

    respuesta = await cliente.post(
        f"/api/v1/productores/{pid}/campos",
        headers=auth_headers,
        json={
            "nombre": "Campo Demo",
            "codigo": "CD-01",
            "latitud": -33.0,
            "longitud": -60.5,
            "puntos_entrada": [
                {
                    "nombre": "Entrada principal",
                    "orden": 1,
                    "latitud": -33.001,
                    "longitud": -60.501,
                    "observacion": "Portón azul",
                }
            ],
        },
    )
    assert respuesta.status_code == 201
    detalle = respuesta.json()
    assert len(detalle["campos"]) == 1
    assert len(detalle["campos"][0]["puntos_entrada"]) == 1

    catalogos = (await cliente.get("/api/v1/catalogos", headers=auth_headers)).json()
    campo = next(c for p in catalogos["productores"] if p["id"] == pid for c in p["campos"])
    assert campo["puntos_entrada"][0]["nombre"] == "Entrada principal"


@pytest.mark.asyncio
async def test_transportistas_abm_flujo(cliente: AsyncClient, auth_headers: dict[str, str]) -> None:
    respuesta = await cliente.post(
        "/api/v1/transportistas",
        headers=auth_headers,
        json={
            "nombre_fantasia": "Transporte ABM",
            "razon_social": "Transporte ABM SRL",
            "cuit": "30-22222222-2",
        },
    )
    assert respuesta.status_code == 201
    tid = respuesta.json()["id"]

    respuesta = await cliente.post(
        f"/api/v1/transportistas/{tid}/camiones",
        headers=auth_headers,
        json={"dominio": "AB123CD", "modelo": "Scania", "marca": "Scania", "tipo": "Camión"},
    )
    assert respuesta.status_code == 201
    assert any(c["dominio"] == "AB123CD" for c in respuesta.json()["camiones"])

    respuesta = await cliente.post(
        f"/api/v1/transportistas/{tid}/choferes",
        headers=auth_headers,
        json={"nombre": "Juan", "apellido": "Test", "documento": "12345678"},
    )
    assert respuesta.status_code == 201
    assert any(ch["nombre"] == "Juan" for ch in respuesta.json()["choferes"])

    listado = (
        await cliente.get("/api/v1/transportistas?filtro=activos", headers=auth_headers)
    ).json()
    assert any(t["id"] == tid for t in listado)
