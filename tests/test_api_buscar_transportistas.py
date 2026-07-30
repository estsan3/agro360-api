"""Tests de integración: tarifas nacionales y buscar transportistas."""

import pytest
from httpx import AsyncClient

from app.core.database import fabrica_sesiones
from app.modulos.catalogos.models import Campo, Material, Productor, Transportista
from app.modulos.mensajeria.models import Conversacion


@pytest.fixture
async def contexto_despacho() -> dict[str, str]:
    async with fabrica_sesiones() as sesion:
        p = Productor(nombre="Prod Busqueda", cuit="30-11112222-3", activo=True)
        sesion.add(p)
        await sesion.flush()
        c = Campo(nombre="Campo B", productor_id=p.id, activo=True)
        sesion.add(c)
        from sqlalchemy import select

        existe_mat = await sesion.execute(
            select(Material).where(Material.nombre == "Soja")
        )
        if existe_mat.scalar_one_or_none() is None:
            sesion.add(Material(nombre="Soja", codigo_grano_afip=23))
        t = Transportista(nombre="Transporte Oferta SA", cuit="30-99998888-1", activo=True)
        sesion.add(t)
        await sesion.commit()
        return {
            "productor_id": p.id,
            "campo_id": c.id,
            "transportista_id": t.id,
        }


@pytest.mark.asyncio
async def test_tarifas_nacionales_y_resolver(
    cliente: AsyncClient, auth_headers: dict[str, str]
) -> None:
    lista = await cliente.get(
        "/api/v1/despachos/tarifas-nacionales", headers=auth_headers
    )
    assert lista.status_code == 200
    tramos = lista.json()
    assert len(tramos) >= 1

    resolucion = await cliente.post(
        "/api/v1/despachos/tarifas-nacionales/resolver",
        headers=auth_headers,
        json={"distancia_km": 250},
    )
    assert resolucion.status_code == 200
    assert resolucion.json()["precio_por_tn"] > 0


@pytest.mark.asyncio
async def test_buscar_transportistas_sin_chofer(
    cliente: AsyncClient,
    auth_headers: dict[str, str],
    contexto_despacho: dict[str, str],
) -> None:
    crear = await cliente.post(
        "/api/v1/despachos",
        headers=auth_headers,
        json={
            "nombre": "Campaña búsqueda",
            "productor_id": contexto_despacho["productor_id"],
            "campo_id": contexto_despacho["campo_id"],
            "origen": "Pergamino",
            "entrada_campo": "Entrada Norte",
            "material": "Soja",
            "administrador_id": "a-1",
            "vendedor_id": "v-1",
            "fecha_inicio": "2026-07-20",
            "estado": "borrador",
            "dador_viaje": "COFCO",
            "tarifa_llena": True,
            "distancia_km": 250,
            "cuando": "manana",
            "viajes": [{"destino": "Rosario", "toneladas": 30}],
        },
    )
    assert crear.status_code == 201, crear.text
    body = crear.json()
    assert body["tarifa_por_tn"] is not None
    assert body["viajes"][0]["chofer_id"] is None
    despacho_id = body["id"]

    buscar = await cliente.post(
        f"/api/v1/despachos/{despacho_id}/buscar-transportistas",
        headers=auth_headers,
    )
    assert buscar.status_code == 200, buscar.text
    assert buscar.json()["viajes"][0]["estado"] == "en_busqueda_transportistas"

    async with fabrica_sesiones() as sesion:
        from sqlalchemy import select

        resultado = await sesion.execute(
            select(Conversacion).where(Conversacion.tipo == "transportista")
        )
        conversaciones = list(resultado.scalars())
        assert len(conversaciones) >= 1
        assert any(c.mensajes for c in conversaciones)


@pytest.mark.asyncio
async def test_buscar_transportistas_crea_viaje_si_no_hay(
    cliente: AsyncClient,
    auth_headers: dict[str, str],
    contexto_despacho: dict[str, str],
) -> None:
    """Sin filas en la tabla de viajes: el endpoint genera el viaje en búsqueda."""
    crear = await cliente.post(
        "/api/v1/despachos",
        headers=auth_headers,
        json={
            "nombre": "Campaña sin viajes previos",
            "productor_id": contexto_despacho["productor_id"],
            "campo_id": contexto_despacho["campo_id"],
            "origen": "Pergamino",
            "entrada_campo": "Entrada Norte",
            "material": "Soja",
            "administrador_id": "a-1",
            "vendedor_id": "v-1",
            "fecha_inicio": "2026-07-20",
            "estado": "borrador",
            "dador_viaje": "FEDEA",
            "tarifa_llena": False,
            "tarifa_por_tn": 32000,
            "cuando": "ahora",
            "viajes": [],
        },
    )
    assert crear.status_code == 201, crear.text
    assert crear.json()["viajes"] == []
    despacho_id = crear.json()["id"]

    buscar = await cliente.post(
        f"/api/v1/despachos/{despacho_id}/buscar-transportistas",
        headers=auth_headers,
        json={"destino": "Timbúes", "toneladas": 32},
    )
    assert buscar.status_code == 200, buscar.text
    viajes = buscar.json()["viajes"]
    assert len(viajes) == 1
    assert viajes[0]["estado"] == "en_busqueda_transportistas"
    assert viajes[0]["destino"] == "Timbúes"
    assert viajes[0]["toneladas"] == 32
    assert viajes[0]["chofer_id"] is None
