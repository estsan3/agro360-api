"""Integración: intención de CPE con payload AFIP completo (sin envío a ARCA)."""

from app.core.database import fabrica_sesiones
from app.modulos.catalogos.models import (
    Camion,
    Campo,
    Chofer,
    Material,
    Productor,
    PuntoEntrada,
    Transportista,
)


async def _sembrar() -> dict[str, str]:
    async with fabrica_sesiones() as sesion:
        if await sesion.get(Material, "mat-cpe") is None:
            sesion.add(Material(id="mat-cpe", nombre="SojaCPE", codigo_grano_afip=23))
        if await sesion.get(Productor, "p-cpe") is None:
            prod = Productor(id="p-cpe", nombre="Prod CPE", cuit="20111222333")
            campo = Campo(id="c-cpe", nombre="Campo CPE", productor_id="p-cpe")
            campo.puntos_entrada.append(
                PuntoEntrada(
                    id="pe-cpe",
                    campo_id="c-cpe",
                    nombre="Entrada",
                    orden=1,
                    latitud=-32.95,
                    longitud=-60.65,
                )
            )
            prod.campos.append(campo)
            t = Transportista(
                id="t-cpe", nombre="Transporte CPE", cuit="30799888777", activo=True
            )
            cam = Camion(
                id="cm-cpe",
                dominio="CP123CE",
                modelo="Scania",
                transportista_id="t-cpe",
                capacidad_tn=40,
            )
            t.camiones.append(cam)
            ch = Chofer(
                id="ch-cpe",
                nombre="Chofer CPE",
                transportista_id="t-cpe",
                camion_id="cm-cpe",
                cuit="20333444555",
                activo=True,
            )
            sesion.add_all([prod, t, ch])
            await sesion.commit()
    return {
        "productor_id": "p-cpe",
        "campo_id": "c-cpe",
        "entrada": "pe-cpe",
        "chofer_id": "ch-cpe",
        "material": "SojaCPE",
    }


def _payload_despacho(ids: dict[str, str]) -> dict:
    return {
        "nombre": "Campaña CPE test",
        "productor_id": ids["productor_id"],
        "campo_id": ids["campo_id"],
        "origen": "Campo CPE",
        "entrada_campo": ids["entrada"],
        "material": ids["material"],
        "administrador_id": "adm-1",
        "vendedor_id": "vend-1",
        "fecha_inicio": "2026-08-05",
        "fecha_llegada_estimada": "2026-08-06",
        "estado": "borrador",
        "distancia_km": 250,
        "tarifa_por_tn": 12010,
        "cpe_habilitada": True,
        "cpe_tipo": 74,
        "cpe_sucursal": 1,
        "cpe_cosecha": 2526,
        "cpe_origen_cod_provincia": 12,
        "cpe_origen_cod_localidad": 1001,
        "cpe_nro_renspa": "12.345.6.78901/00",
        "cpe_codigo_turno": "TURNO-PEDIDO",
        "cpe_hora_partida": "20:00",
        "cpe_cuit_remitente_comercial_vs2": "20111222333",
        "cpe_cuit_remitente_comercial_productor": "20111222333",
        "cpe_destino_cuit": "30555666777",
        "cpe_destino_es_campo": False,
        "cpe_destino_cod_provincia": 12,
        "cpe_destino_cod_localidad": 2002,
        "cpe_destino_planta": 150,
        "cpe_peso_tara_kg_default": 15000,
        "viajes": [
            {
                "chofer_id": ids["chofer_id"],
                "dominio": "CP123CE",
                "destino": "Timbúes",
                "toneladas": 30,
                "cpe_codigo_turno": "COSM6752-TEST",
                "cpe_dominio_acoplado": "AF495WZ",
            }
        ],
    }


async def test_crear_reintentar_y_eliminar_intencion(cliente, auth_headers):
    ids = await _sembrar()

    creado = await cliente.post(
        "/api/v1/despachos", json=_payload_despacho(ids), headers=auth_headers
    )
    assert creado.status_code == 201, creado.text
    despacho = creado.json()
    viaje_id = despacho["viajes"][0]["id"]
    assert despacho["cpe_habilitada"] is True
    assert despacho["cpe_tipo"] == 74
    assert despacho["cpe_nro_renspa"] == "12.345.6.78901/00"
    assert despacho["cpe_codigo_turno"] == "TURNO-PEDIDO"
    assert despacho["viajes"][0]["cpe_codigo_turno"] == "COSM6752-TEST"

    intencion = await cliente.post(
        "/api/v1/cartas-porte",
        json={"despacho_id": despacho["id"], "viaje_id": viaje_id},
        headers=auth_headers,
    )
    assert intencion.status_code == 201, intencion.text
    carta = intencion.json()
    assert carta["estado"] == "pendiente"
    assert carta["tipo_cpe"] == 74
    assert carta["payload_afip"]["tipo_cpe"] == 74
    assert carta["payload_afip"]["datos_carga"]["cod_grano"] == 23
    assert carta["payload_afip"]["destino"]["planta"] == 150
    assert carta["payload_afip"]["origen"]["nro_renspa"] == "12.345.6.78901/00"
    assert carta["payload_afip"]["transporte"]["codigo_turno"] == "COSM6752-TEST"
    assert carta["payload_afip"]["transporte"]["dominio"] == ["CP123CE", "AF495WZ"]
    assert carta["payload_afip"]["transporte"]["fecha_hora_partida"].startswith(
        "2026-08-05T20:00:00"
    )
    assert (
        carta["payload_afip"]["intervinientes"]["cuit_remitente_comercial_venta_secundaria_2"]
        == "20111222333"
    )
    assert (
        carta["payload_afip"]["intervinientes"]["cuit_remitente_comercial_productor"]
        == "20111222333"
    )
    assert carta["nro_ctg"] is None

    listado = await cliente.get("/api/v1/cartas-porte", headers=auth_headers)
    assert listado.status_code == 200
    assert any(c["id"] == carta["id"] for c in listado.json())

    reintento = await cliente.post(
        f"/api/v1/cartas-porte/{carta['id']}/reintentar", headers=auth_headers
    )
    assert reintento.status_code == 200, reintento.text
    assert reintento.json()["intentos"] == 1
    assert reintento.json()["estado"] == "pendiente"

    detalle = await cliente.get(
        f"/api/v1/cartas-porte/{carta['id']}", headers=auth_headers
    )
    assert detalle.status_code == 200
    assert detalle.json()["payload_afip"]["sucursal"] == 1

    borrado = await cliente.delete(
        f"/api/v1/cartas-porte/{carta['id']}", headers=auth_headers
    )
    assert borrado.status_code == 204

    faltante = await cliente.get(
        f"/api/v1/cartas-porte/{carta['id']}", headers=auth_headers
    )
    assert faltante.status_code == 404


async def test_documento_solo_si_procesada(cliente, auth_headers):
    """Una CPE procesada con PDF se puede descargar; una pendiente no."""
    from app.core.database import fabrica_sesiones
    from app.modulos.cartas_porte.documento import generar_pdf_cpe_demo
    from app.modulos.cartas_porte.models import CartaPorte

    ids = await _sembrar()
    body = _payload_despacho(ids)
    body["nombre"] = "Campaña doc CPE"
    creado = await cliente.post("/api/v1/despachos", json=body, headers=auth_headers)
    assert creado.status_code == 201, creado.text
    despacho = creado.json()
    viaje_id = despacho["viajes"][0]["id"]

    intencion = await cliente.post(
        "/api/v1/cartas-porte",
        json={"despacho_id": despacho["id"], "viaje_id": viaje_id},
        headers=auth_headers,
    )
    assert intencion.status_code == 201
    carta_id = intencion.json()["id"]
    assert intencion.json()["tiene_documento"] is False

    sin_doc = await cliente.get(
        f"/api/v1/cartas-porte/{carta_id}/documento", headers=auth_headers
    )
    assert sin_doc.status_code == 422

    async with fabrica_sesiones() as sesion:
        carta = await sesion.get(CartaPorte, carta_id)
        assert carta is not None
        carta.estado = "procesada"
        carta.nro_carta_porte = "74009999001"
        carta.nro_ctg = "010199990001"
        carta.pdf_base64 = generar_pdf_cpe_demo(
            nro_carta_porte="74009999001",
            nro_ctg="010199990001",
            tipo_cpe=74,
            material=carta.material,
            origen=carta.origen,
            destino=carta.destino,
            dominio=carta.dominio,
            toneladas=carta.toneladas,
        )
        await sesion.commit()

    detalle = await cliente.get(f"/api/v1/cartas-porte/{carta_id}", headers=auth_headers)
    assert detalle.status_code == 200
    assert detalle.json()["tiene_documento"] is True
    assert detalle.json()["estado"] == "procesada"

    pdf = await cliente.get(
        f"/api/v1/cartas-porte/{carta_id}/documento", headers=auth_headers
    )
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content[:4] == b"%PDF"


async def test_editar_despacho_y_reintentar_intencion(cliente, auth_headers):
    """Corrige la campaña activa sin recrear viajes y regenera el payload CPE."""
    ids = await _sembrar()
    body = _payload_despacho(ids)
    body["nombre"] = "Campaña editar CPE"
    body["estado"] = "activo"
    creado = await cliente.post("/api/v1/despachos", json=body, headers=auth_headers)
    assert creado.status_code == 201, creado.text
    despacho = creado.json()
    viaje_id = despacho["viajes"][0]["id"]

    intencion = await cliente.post(
        "/api/v1/cartas-porte",
        json={"despacho_id": despacho["id"], "viaje_id": viaje_id},
        headers=auth_headers,
    )
    assert intencion.status_code == 201, intencion.text
    carta_id = intencion.json()["id"]

    editado = await cliente.patch(
        f"/api/v1/despachos/{despacho['id']}/para-intencion-cpe",
        json={
            **body,
            "cpe_sucursal": 9,
            "cpe_destino_planta": 777,
            "viajes": [
                {
                    "id": viaje_id,
                    "chofer_id": ids["chofer_id"],
                    "dominio": "CP123CE",
                    "destino": "San Lorenzo",
                    "toneladas": 32,
                }
            ],
        },
        headers=auth_headers,
    )
    assert editado.status_code == 200, editado.text
    assert editado.json()["cpe_sucursal"] == 9
    assert editado.json()["cpe_destino_planta"] == 777
    assert editado.json()["viajes"][0]["id"] == viaje_id
    assert editado.json()["viajes"][0]["destino"] == "San Lorenzo"

    reintento = await cliente.post(
        f"/api/v1/cartas-porte/{carta_id}/reintentar", headers=auth_headers
    )
    assert reintento.status_code == 200, reintento.text
    carta = reintento.json()
    assert carta["estado"] == "pendiente"
    assert carta["viaje_id"] == viaje_id
    assert carta["destino"] == "San Lorenzo"
    assert carta["payload_afip"]["sucursal"] == 9
    assert carta["payload_afip"]["destino"]["planta"] == 777


async def test_flete_corto_274(cliente, auth_headers):
    ids = await _sembrar()
    body = _payload_despacho(ids)
    body["cpe_tipo"] = 274
    body["nombre"] = "Campaña flete corto"

    creado = await cliente.post("/api/v1/despachos", json=body, headers=auth_headers)
    assert creado.status_code == 201, creado.text
    despacho = creado.json()
    viaje_id = despacho["viajes"][0]["id"]

    intencion = await cliente.post(
        "/api/v1/cartas-porte",
        json={"despacho_id": despacho["id"], "viaje_id": viaje_id},
        headers=auth_headers,
    )
    assert intencion.status_code == 201, intencion.text
    assert intencion.json()["tipo_cpe"] == 274
    assert (
        intencion.json()["payload_afip"]["_meta"]["tipo_cpe_etiqueta"]
        == "Automotor flete corto"
    )


async def test_enviar_y_anular_con_adaptador_simulado(cliente, auth_headers):
    ids = await _sembrar()
    body = _payload_despacho(ids)
    body["nombre"] = "Campaña enviar CPE"
    creado = await cliente.post("/api/v1/despachos", json=body, headers=auth_headers)
    assert creado.status_code == 201, creado.text
    despacho = creado.json()
    viaje_id = despacho["viajes"][0]["id"]

    intencion = await cliente.post(
        "/api/v1/cartas-porte",
        json={"despacho_id": despacho["id"], "viaje_id": viaje_id},
        headers=auth_headers,
    )
    assert intencion.status_code == 201
    carta_id = intencion.json()["id"]
    assert intencion.json()["estado"] == "pendiente"

    enviado = await cliente.post(
        f"/api/v1/cartas-porte/{carta_id}/enviar", headers=auth_headers
    )
    assert enviado.status_code == 200, enviado.text
    carta = enviado.json()
    assert carta["estado"] == "procesada"
    assert carta["nro_ctg"]
    assert carta["nro_carta_porte"]
    assert carta["tiene_documento"] is True
    assert carta["payload_afip"]["nro_orden"] == 1

    pdf = await cliente.get(
        f"/api/v1/cartas-porte/{carta_id}/documento", headers=auth_headers
    )
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"

    repetir = await cliente.post(
        f"/api/v1/cartas-porte/{carta_id}/enviar", headers=auth_headers
    )
    assert repetir.status_code == 422

    anulado = await cliente.post(
        f"/api/v1/cartas-porte/{carta_id}/anular", headers=auth_headers
    )
    assert anulado.status_code == 200, anulado.text
    assert anulado.json()["estado"] == "anulada"
