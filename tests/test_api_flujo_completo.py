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


async def test_contrato_front(cliente, auth_headers):
    """Verifica el contrato wire que consume el front Angular."""
    # Catálogos base con nombres únicos (la base en memoria persiste).
    productor = (
        await cliente.post(
            "/api/v1/catalogos/productores",
            json={"nombre": "Productor Front", "campos": ["Campo Front"]},
            headers=auth_headers,
        )
    ).json()
    await cliente.post(
        "/api/v1/catalogos/materiales",
        json={"nombre": "Girasol"},
        headers=auth_headers,
    )
    chofer = (
        await cliente.post(
            "/api/v1/catalogos/choferes",
            json={"nombre": "Chofer Front", "dominio": "CD456EF", "modelo": "Scania R450"},
            headers=auth_headers,
        )
    ).json()

    # 1. GET /catalogos agregado: la forma exacta que espera el front.
    catalogos = (await cliente.get("/api/v1/catalogos", headers=auth_headers)).json()
    assert {"productores", "administradores", "vendedores", "materiales", "choferes"} <= set(
        catalogos
    )
    assert "Girasol" in catalogos["materiales"]  # materiales como nombres
    assert "transportistas" in catalogos
    assert any(c["modelo"] == "Scania R450" for c in catalogos["choferes"])
    assert any(u["nombre"] == "Admin Test" for u in catalogos["administradores"])

    # 2. Crear campaña con estado (contrato del front) y viajes borrador.
    despacho = (
        await cliente.post(
            "/api/v1/despachos",
            json={
                "nombre": "Campaña Front",
                "productor_id": productor["id"],
                "campo_id": productor["campos"][0]["id"],
                "origen": "Salta Capital",
                "material": "Girasol",
                "administrador_id": "a-1",
                "vendedor_id": "v-1",
                "fecha_inicio": "2026-07-01",
                "fecha_llegada_estimada": "2026-07-20",
                "estado": "borrador",
                "viajes": [
                    {"chofer_id": chofer["id"], "destino": "Rosario", "toneladas": 30}
                ],
            },
            headers=auth_headers,
        )
    ).json()
    assert despacho["viajes"][0]["estado"] == "borrador"

    # 3. PUT: editar el borrador y enviarlo (estado activo) en un paso.
    respuesta = await cliente.put(
        f"/api/v1/despachos/{despacho['id']}",
        json={
            "nombre": "Campaña Front (editada)",
            "productor_id": productor["id"],
            "campo_id": productor["campos"][0]["id"],
            "origen": "Salta Capital",
            "material": "Girasol",
            "administrador_id": "a-1",
            "vendedor_id": "v-1",
            "fecha_inicio": "2026-07-01",
            "fecha_llegada_estimada": "2026-07-20",
            "estado": "activo",
            "viajes": [
                {"chofer_id": chofer["id"], "destino": "Rosario", "toneladas": 32}
            ],
        },
        headers=auth_headers,
    )
    despacho = respuesta.json()
    assert despacho["estado"] == "activo"
    assert despacho["viajes"][0]["estado"] == "pendiente"  # promovido al activar
    viaje_id = despacho["viajes"][0]["id"]

    # 4. Duplicar e iniciar viajes (acciones de la pantalla de borradores).
    despacho = (
        await cliente.post(
            f"/api/v1/despachos/{despacho['id']}/viajes/{viaje_id}/duplicar",
            headers=auth_headers,
        )
    ).json()
    assert len(despacho["viajes"]) == 2

    despacho = (
        await cliente.post(
            f"/api/v1/despachos/{despacho['id']}/viajes/{viaje_id}/iniciar",
            headers=auth_headers,
        )
    ).json()
    viaje = next(v for v in despacho["viajes"] if v["id"] == viaje_id)
    assert viaje["estado"] == "en_viaje"

    # 5. El evento del viaje iniciado abrió el chat del chofer con contexto.
    conversaciones = (
        await cliente.get("/api/v1/conversaciones", headers=auth_headers)
    ).json()
    conv = next(c for c in conversaciones if c["chofer"] == "Chofer Front")
    assert conv["viaje_id"] == viaje_id
    assert conv["estado_viaje"] == "en_viaje"
    assert conv["en_linea"] is False

    # 6. Enviar mensaje devuelve el mensaje creado (no la conversación).
    mensaje = (
        await cliente.post(
            f"/api/v1/conversaciones/{conv['id']}/mensajes",
            json={"texto": "¿Cómo vas?"},
            headers=auth_headers,
        )
    ).json()
    assert mensaje["autor"] == "admin"
    assert mensaje["leido"] is True

    # 7. Rutas de parámetros y preferencias a nivel raíz.
    parametros = (await cliente.get("/api/v1/parametros", headers=auth_headers)).json()
    assert "precio_por_tonelada" in parametros
    preferencias = (
        await cliente.get("/api/v1/preferencias", headers=auth_headers)
    ).json()
    assert "viaje_retrasado" in preferencias

    # 8. Gestión de usuarios en /usuarios (con baja).
    usuario = (
        await cliente.post(
            "/api/v1/usuarios",
            json={
                "nombre": "Vendedor Baja",
                "dni": "99887766",
                "email": "baja@test.com",
                "rol": "vendedor",
            },
            headers=auth_headers,
        )
    ).json()
    respuesta = await cliente.delete(
        f"/api/v1/usuarios/{usuario['id']}", headers=auth_headers
    )
    assert respuesta.status_code == 204

    # 9. Logout responde 204 (el front descarta el token).
    respuesta = await cliente.post("/api/v1/auth/logout", headers=auth_headers)
    assert respuesta.status_code == 204


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
