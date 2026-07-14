"""Test de integración: flujo de negocio punta a punta contra la API.

Cubre: login → catálogos → campaña con viaje → activación →
carta de porte → KPIs. Sirve además como documentación ejecutable
del uso de la API.
"""


async def test_login_invalido(cliente):
    """Credenciales incorrectas devuelven 401 con el formato de error unificado."""
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={"email": "nadie@test.com", "password": "incorrecta1"},
    )
    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["codigo"] == "no_autenticado"


async def test_endpoints_requieren_token(cliente):
    """Sin token, los módulos protegidos devuelven 401."""
    respuesta = await cliente.get("/api/v1/despachos")
    assert respuesta.status_code == 401


async def test_flujo_completo(cliente, auth_headers):
    """Recorre el ciclo completo: catálogos → campaña → CPE → KPIs."""
    # 1. Alta de catálogos maestros.
    productor = (
        await cliente.post(
            "/api/v1/catalogos/productores",
            json={"nombre": "Agro Test SA", "campos": ["Campo Uno"]},
            headers=auth_headers,
        )
    ).json()
    campo_id = productor["campos"][0]["id"]

    await cliente.post(
        "/api/v1/catalogos/materiales",
        json={"nombre": "Soja", "codigo_grano_afip": 23},
        headers=auth_headers,
    )
    chofer = (
        await cliente.post(
            "/api/v1/catalogos/choferes",
            json={"nombre": "Chofer Test", "dominio": "AB123CD"},
            headers=auth_headers,
        )
    ).json()

    # 2. Crear campaña en borrador con un viaje asignado.
    respuesta = await cliente.post(
        "/api/v1/despachos",
        json={
            "nombre": "Campaña Test",
            "productor_id": productor["id"],
            "campo_id": campo_id,
            "origen": "Rosario, Santa Fe",
            "material": "Soja",
            "administrador_id": "a-1",
            "vendedor_id": "v-1",
            "fecha_inicio": "2026-07-01",
            "fecha_llegada_estimada": "2026-07-20",
            "viajes": [
                {"chofer_id": chofer["id"], "destino": "Puerto BA", "toneladas": 30}
            ],
        },
        headers=auth_headers,
    )
    assert respuesta.status_code == 201
    despacho = respuesta.json()
    assert despacho["estado"] == "borrador"
    # El viaje copió nombre y dominio del chofer desde catálogos.
    assert despacho["viajes"][0]["dominio"] == "AB123CD"

    # 3. Activar la campaña.
    respuesta = await cliente.post(
        f"/api/v1/despachos/{despacho['id']}/activar", headers=auth_headers
    )
    assert respuesta.json()["estado"] == "activo"

    # 4. Emitir la carta de porte del viaje (adaptador simulado).
    viaje_id = despacho["viajes"][0]["id"]
    respuesta = await cliente.post(
        "/api/v1/cartas-porte",
        json={"despacho_id": despacho["id"], "viaje_id": viaje_id},
        headers=auth_headers,
    )
    assert respuesta.status_code == 201
    carta = respuesta.json()
    assert carta["estado"] == "autorizada"
    assert carta["nro_ctg"] is not None

    # 5. Emitir de nuevo para el mismo viaje debe fallar (regla de negocio).
    respuesta = await cliente.post(
        "/api/v1/cartas-porte",
        json={"despacho_id": despacho["id"], "viaje_id": viaje_id},
        headers=auth_headers,
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "regla_violada"

    # 6. KPIs reflejan la campaña activa.
    respuesta = await cliente.get("/api/v1/reporteria/kpis", headers=auth_headers)
    kpis = respuesta.json()
    assert kpis["campanias_activas"] >= 1
    assert kpis["toneladas_totales"] >= 30


async def test_activar_campania_sin_viajes_falla(cliente, auth_headers):
    """Regla de negocio: no se activa una campaña sin viajes."""
    productor = (
        await cliente.post(
            "/api/v1/catalogos/productores",
            json={"nombre": "Productor Sin Viajes", "campos": ["Campo X"]},
            headers=auth_headers,
        )
    ).json()
    await cliente.post(
        "/api/v1/catalogos/materiales",
        json={"nombre": "Trigo"},
        headers=auth_headers,
    )

    despacho = (
        await cliente.post(
            "/api/v1/despachos",
            json={
                "nombre": "Campaña Vacía",
                "productor_id": productor["id"],
                "campo_id": productor["campos"][0]["id"],
                "origen": "Pergamino",
                "material": "Trigo",
                "administrador_id": "a-1",
                "vendedor_id": "v-1",
                "fecha_inicio": "2026-08-01",
                "fecha_llegada_estimada": "2026-08-10",
            },
            headers=auth_headers,
        )
    ).json()

    respuesta = await cliente.post(
        f"/api/v1/despachos/{despacho['id']}/activar", headers=auth_headers
    )
    assert respuesta.status_code == 422
