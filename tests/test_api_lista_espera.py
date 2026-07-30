"""Integración API: lista de espera FIFO, rechazo al fondo y reencole."""

from app.core.database import fabrica_sesiones
from app.modulos.catalogos.models import Camion, Chofer, Material, Productor, Campo, Transportista


async def _sembrar_catalogos_lista() -> dict[str, str]:
    """Crea flota propia + dos terceros listos para anotar."""
    async with fabrica_sesiones() as sesion:
        if await sesion.get(Material, "mat-soja-lista") is None:
            sesion.add(Material(id="mat-soja-lista", nombre="SojaLista"))
        prod = Productor(id="p-lista", nombre="Prod Lista")
        campo = Campo(id="c-lista", nombre="Campo Lista", productor_id="p-lista")
        prod.campos.append(campo)

        propia = Transportista(
            id="t-propia-lista",
            nombre="Flota Propia Lista",
            es_flota_propia=True,
            activo=True,
        )
        cam_propia = Camion(
            id="cm-propia",
            dominio="PP111PP",
            modelo="Scania",
            transportista_id="t-propia-lista",
            capacidad_tn=40,
            tipo_unidad="tolva",
        )
        propia.camiones.append(cam_propia)
        ch_propia = Chofer(
            id="ch-propia",
            nombre="Chofer Propio",
            transportista_id="t-propia-lista",
            camion_id="cm-propia",
            activo=True,
        )

        t1 = Transportista(id="t-lista-1", nombre="Fletero Uno", es_flota_propia=False)
        c1 = Camion(
            id="cm-lista-1",
            dominio="FF111FF",
            modelo="Iveco",
            transportista_id="t-lista-1",
            capacidad_tn=35,
            tipo_unidad="tolva",
        )
        t1.camiones.append(c1)
        ch1 = Chofer(
            id="ch-lista-1",
            nombre="Chofer Uno",
            transportista_id="t-lista-1",
            camion_id="cm-lista-1",
        )

        t2 = Transportista(id="t-lista-2", nombre="Fletero Dos", es_flota_propia=False)
        c2 = Camion(
            id="cm-lista-2",
            dominio="FF222FF",
            modelo="Volvo",
            transportista_id="t-lista-2",
            capacidad_tn=35,
            tipo_unidad="tolva",
        )
        t2.camiones.append(c2)
        ch2 = Chofer(
            id="ch-lista-2",
            nombre="Chofer Dos",
            transportista_id="t-lista-2",
            camion_id="cm-lista-2",
        )

        # Idempotencia: si ya existen, no duplicar.
        if await sesion.get(Transportista, "t-propia-lista") is None:
            sesion.add_all([prod, propia, ch_propia, t1, ch1, t2, ch2])
            await sesion.commit()

    return {
        "productor_id": "p-lista",
        "campo_id": "c-lista",
        "ch1": "ch-lista-1",
        "cm1": "cm-lista-1",
        "ch2": "ch-lista-2",
        "cm2": "cm-lista-2",
        "ch_propia": "ch-propia",
    }


async def test_anotar_rechazar_al_fondo_y_fifo(cliente, auth_headers):
    ids = await _sembrar_catalogos_lista()

    # Flota propia no puede anotarse.
    resp = await cliente.post(
        "/api/v1/lista-espera",
        json={"chofer_id": ids["ch_propia"], "camion_id": "cm-propia"},
        headers=auth_headers,
    )
    assert resp.status_code == 422

    e1 = (
        await cliente.post(
            "/api/v1/lista-espera",
            json={"chofer_id": ids["ch1"], "camion_id": ids["cm1"]},
            headers=auth_headers,
        )
    ).json()
    e2 = (
        await cliente.post(
            "/api/v1/lista-espera",
            json={"chofer_id": ids["ch2"], "camion_id": ids["cm2"]},
            headers=auth_headers,
        )
    ).json()
    assert e1["estado"] == "en_espera"
    assert e2["estado"] == "en_espera"

    lista = (
        await cliente.get("/api/v1/lista-espera", headers=auth_headers)
    ).json()
    assert [x["id"] for x in lista[:2]] == [e1["id"], e2["id"]]

    # Campaña con viaje sin chofer (propia ocuparemos luego; aquí forzamos lista
    # ocupando al propio con otro viaje primero).
    despacho = (
        await cliente.post(
            "/api/v1/despachos",
            json={
                "nombre": "Camp Lista",
                "productor_id": ids["productor_id"],
                "campo_id": ids["campo_id"],
                "origen": "Origen Test",
                "material": "SojaLista",
                "administrador_id": "a-1",
                "vendedor_id": "v-1",
                "fecha_inicio": "2026-07-01",
                "viajes": [{"destino": "Destino A", "toneladas": 28}],
                "estado": "borrador",
            },
            headers=auth_headers,
        )
    ).json()
    viaje_id = despacho["viajes"][0]["id"]

    # Ocupar flota propia para forzar uso de lista.
    await cliente.post(
        "/api/v1/despachos",
        json={
            "nombre": "Camp Propia Ocupada",
            "productor_id": ids["productor_id"],
            "campo_id": ids["campo_id"],
            "origen": "Origen Test",
            "material": "SojaLista",
            "administrador_id": "a-1",
            "vendedor_id": "v-1",
            "fecha_inicio": "2026-07-01",
            "viajes": [
                {
                    "chofer_id": ids["ch_propia"],
                    "destino": "Destino B",
                    "toneladas": 20,
                }
            ],
            "estado": "activo",
        },
        headers=auth_headers,
    )

    # Activar campaña lista con viaje sin chofer: agregar chofer dummy no;
    # activar exige chofer. Usamos campaña activa agregando viaje.
    # Mejor: activar no — usamos asignar_por_lista sobre borrador.
    asignar = await cliente.post(
        f"/api/v1/despachos/{despacho['id']}/viajes/{viaje_id}/asignar-por-lista",
        json={},
        headers=auth_headers,
    )
    assert asignar.status_code == 200, asignar.text
    oferta_lista = (
        await cliente.get("/api/v1/lista-espera", headers=auth_headers)
    ).json()
    ofertada = next(x for x in oferta_lista if x["estado"] == "ofertado")
    assert ofertada["id"] == e1["id"]

    # Rechazar → e1 al fondo, ofrece a e2.
    rechazar = await cliente.post(
        f"/api/v1/despachos/{despacho['id']}/viajes/{viaje_id}/rechazar-oferta-lista",
        headers=auth_headers,
    )
    assert rechazar.status_code == 200, rechazar.text
    oferta_lista = (
        await cliente.get("/api/v1/lista-espera", headers=auth_headers)
    ).json()
    ofertada = next(x for x in oferta_lista if x["estado"] == "ofertado")
    assert ofertada["id"] == e2["id"]
    e1_actual = next(x for x in oferta_lista if x["id"] == e1["id"])
    assert e1_actual["estado"] == "en_espera"
    # e1 quedó al fondo (anotado_en más reciente).
    assert oferta_lista[-1]["id"] == e1["id"] or oferta_lista.index(
        e1_actual
    ) > oferta_lista.index(next(x for x in oferta_lista if x["id"] == e2["id"]))

    # Aceptar e2.
    aceptar = await cliente.post(
        f"/api/v1/despachos/{despacho['id']}/viajes/{viaje_id}/aceptar-oferta-lista",
        params={"entrada_id": e2["id"]},
        headers=auth_headers,
    )
    assert aceptar.status_code == 200, aceptar.text
    viaje = aceptar.json()["viajes"][0]
    assert viaje["chofer_id"] == ids["ch2"]
    assert viaje["estado"] == "pendiente"

    # Completar ciclo: iniciar + completar → reencola e2.
    await cliente.post(
        f"/api/v1/despachos/{despacho['id']}/activar",
        headers=auth_headers,
    )
    # Activar falla si hay viajes sin chofer? Solo hay uno con chofer.
    # El despacho estaba en borrador; activar requiere todos con chofer.
    # Re-fetch: ya tiene chofer.
    iniciar = await cliente.post(
        f"/api/v1/despachos/{despacho['id']}/viajes/{viaje_id}/iniciar",
        headers=auth_headers,
    )
    # Puede fallar si aún borrador — activar primero.
    if iniciar.status_code != 200:
        act = await cliente.post(
            f"/api/v1/despachos/{despacho['id']}/activar", headers=auth_headers
        )
        assert act.status_code == 200, act.text
        iniciar = await cliente.post(
            f"/api/v1/despachos/{despacho['id']}/viajes/{viaje_id}/iniciar",
            headers=auth_headers,
        )
    assert iniciar.status_code == 200, iniciar.text

    completar = await cliente.patch(
        f"/api/v1/despachos/{despacho['id']}/viajes/{viaje_id}",
        json={"estado": "completado"},
        headers=auth_headers,
    )
    assert completar.status_code == 200, completar.text

    lista_final = (
        await cliente.get("/api/v1/lista-espera", headers=auth_headers)
    ).json()
    ids_lista = [x["chofer_id"] for x in lista_final if x["estado"] == "en_espera"]
    assert ids["ch2"] in ids_lista
