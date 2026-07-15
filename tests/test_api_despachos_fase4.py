"""Integración API — fase 4: cerrar, metadatos y duplicar campaña."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cerrar_duplicar_y_metadatos_campaña(cliente: AsyncClient, auth_headers: dict):
    """Flujo: activar → completar viaje → cerrar → duplicar → editar metadatos del activo."""
    catalogos = (await cliente.get("/api/v1/catalogos", headers=auth_headers)).json()
    productor = catalogos["productores"][0]
    campo = productor["campos"][0]
    chofer = catalogos["choferes"][0]

    alta = await cliente.post(
        "/api/v1/despachos",
        headers=auth_headers,
        json={
            "nombre": "Campaña Fase 4",
            "productor_id": productor["id"],
            "campo_id": campo["id"],
            "origen": campo["nombre"],
            "entrada_campo": "",
            "material": catalogos["materiales"][0],
            "administrador_id": catalogos["administradores"][0]["id"],
            "vendedor_id": catalogos["vendedores"][0]["id"],
            "fecha_inicio": "2026-07-01",
            "fecha_llegada_estimada": "2026-07-15",
            "estado": "borrador",
            "viajes": [
                {
                    "chofer_id": chofer["id"],
                    "destino": "Puerto Rosario",
                    "toneladas": 28,
                }
            ],
        },
    )
    assert alta.status_code == 201
    despacho = alta.json()
    despacho_id = despacho["id"]
    viaje_id = despacho["viajes"][0]["id"]

    activar = await cliente.post(
        f"/api/v1/despachos/{despacho_id}/activar", headers=auth_headers
    )
    assert activar.status_code == 200

    iniciar = await cliente.post(
        f"/api/v1/despachos/{despacho_id}/viajes/{viaje_id}/iniciar",
        headers=auth_headers,
    )
    assert iniciar.status_code == 200

    completar = await cliente.patch(
        f"/api/v1/despachos/{despacho_id}/viajes/{viaje_id}",
        headers=auth_headers,
        json={"estado": "completado"},
    )
    assert completar.status_code == 200

    metadatos = await cliente.patch(
        f"/api/v1/despachos/{despacho_id}/metadatos",
        headers=auth_headers,
        json={
            "fecha_llegada_estimada": "2026-07-20",
            "observaciones": "Cierre de campaña previsto",
        },
    )
    assert metadatos.status_code == 200
    assert metadatos.json()["observaciones"] == "Cierre de campaña previsto"

    cerrar = await cliente.post(
        f"/api/v1/despachos/{despacho_id}/cerrar", headers=auth_headers
    )
    assert cerrar.status_code == 200
    assert cerrar.json()["estado"] == "cerrado"

    duplicar = await cliente.post(
        f"/api/v1/despachos/{despacho_id}/duplicar",
        headers=auth_headers,
        json={"nombre": "Campaña Fase 4 — réplica"},
    )
    assert duplicar.status_code == 201
    copia = duplicar.json()
    assert copia["estado"] == "borrador"
    assert copia["nombre"] == "Campaña Fase 4 — réplica"
    assert len(copia["viajes"]) == 1
    assert copia["viajes"][0]["estado"] == "borrador"

    agregar_cerrada = await cliente.post(
        f"/api/v1/despachos/{despacho_id}/viajes",
        headers=auth_headers,
        json={"destino": "Otro", "toneladas": 10},
    )
    assert agregar_cerrada.status_code == 422
