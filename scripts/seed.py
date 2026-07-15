"""Seed de datos de demo, espejo del mock del front Angular (mock-data.ts).

Replica los mismos IDs y datos del mock para que la UI se vea idéntica
al apagar el interceptor. Se ejecuta automáticamente al iniciar la API
en dev (si la base está vacía) o manualmente con:
    poetry run python -m scripts.seed
"""

import asyncio
from datetime import date, datetime

from app.core.database import crear_tablas, fabrica_sesiones
from app.core.seguridad import hashear_password
from app.modulos.auth.dao import UsuarioDAO
from app.modulos.auth.models import Usuario
from app.modulos.catalogos.models import Camion, Campo, Chofer, Material, Productor, Transportista
from app.modulos.despachos.models import Despacho, Viaje
from app.modulos.mensajeria.models import Conversacion, Mensaje

# Credenciales de demo (las mismas que el mock del front).
EMAIL_DEMO = "admin@agro360.com"
PASSWORD_DEMO = "demo12345"

# ------------------------------ Usuarios ------------------------------
# Administradores (a-*) y vendedores (v-*): el endpoint agregado de
# catálogos los compone desde acá por rol.
_USUARIOS = [
    ("a-1", "María González", "27888999", EMAIL_DEMO, "administrador"),
    ("a-2", "Antonio Samuel", "20111222", "antonio.samuel@agro360.com", "administrador"),
    ("v-1", "Juan Pérez", "12345678", "juan.perez@email.com", "vendedor"),
    ("v-2", "Carlos Rodríguez", "23456789", "carlos.rodriguez@agro360.com", "vendedor"),
]

# ------------------------------ Catálogos -----------------------------
_PRODUCTORES = [
    ("p-1", "Agro SA", [("c-1", "Campo Norte"), ("c-2", "Campo Los Nogales")]),
    ("p-2", "Campo Verde SRL", [("c-3", "Campo San Pedro")]),
]

# Códigos de grano según tabla de ARCA/AFIP (consultarTiposGrano).
_MATERIALES = [("Soja", 23), ("Maíz", 2), ("Girasol", 27), ("Trigo", 1)]

_CHOFERES = [
    ("ch-1", "Carlos Ruiz", "t-1"),
    ("ch-2", "Miguel Torres", "t-1"),
    ("ch-3", "Roberto Gómez", "t-2"),
    ("ch-4", "Pedro Ramírez", "t-2"),
]

# Empresas de transporte con flota (patentes alineadas a los choferes seed).
_TRANSPORTISTAS = [
    (
        "t-1",
        "Transportes del Plata",
        "30712345671",
        [
            ("cm-1", "AA123BB", "Mercedes 1114"),
            ("cm-2", "EF789GH", "Volvo FH 420"),
        ],
    ),
    (
        "t-2",
        "Flota Pampeana",
        "30709876543",
        [
            ("cm-3", "BC456CD", "Scania R450"),
            ("cm-4", "XY789ZA", "Iveco Tector 170"),
        ],
    ),
]

# ------------------------------ Despachos -----------------------------
# (id, nombre, productor, campo, origen, entrada, material, admin, vendedor,
#  inicio, llegada, estado, viajes)
# Viaje: (id, chofer_nombre, dominio, destino, toneladas, estado, progreso, obs)
_DESPACHOS = [
    (
        "d-1", "Campaña Maíz 2026", "p-1", "c-1", "Rosario, Santa Fe",
        "Entrada Norte (Lat: -32.9442, Lng: -60.6505)", "Maíz", "a-1", "v-1",
        date(2026, 7, 1), date(2026, 7, 20), "activo",
        [
            ("#12345", "Juan Pérez", "AB123CD", "Buenos Aires - Puerto", 28, "en_viaje", 65, "Viaje normal"),
            ("#12343", "Sin asignar", "-", "Buenos Aires - Puerto", 28, "pendiente", 0, "Pendiente asignación"),
            ("#12342", "Pedro Ramírez", "XY789ZA", "Buenos Aires - Puerto", 30, "retrasado", 42, "Desperfecto técnico en ruta"),
            ("#12340", "Carlos Ruiz", "DE456FG", "Buenos Aires - Puerto", 29, "completado", 100, "Entregado"),
        ],
    ),
    (
        "d-3", "Campaña Soja 2026", "p-1", "c-2", "Pergamino, Buenos Aires",
        "Entrada Sur", "Soja", "a-2", "v-2",
        date(2026, 6, 20), date(2026, 7, 15), "activo",
        [
            ("#12330", "Miguel Torres", "EF789GH", "Rosario - Terminal", 32, "completado", 100, "Entregado"),
            ("#12331", "Roberto Gómez", "BC456CD", "Rosario - Terminal", 30, "en_viaje", 80, "Llegada anticipada"),
            ("#12332", "Carlos Ruiz", "AA123BB", "Puerto San Martín", 28.5, "en_viaje", 35, "Viaje normal"),
        ],
    ),
    (
        "d-11", "Campaña Maíz Otoño", "p-1", "c-2", "Pergamino, Buenos Aires",
        "Entrada Norte (Lat: -32.9442, Lng: -60.6505)", "Maíz", "a-1", "v-1",
        date(2026, 4, 8), date(2026, 4, 30), "activo",
        [
            ("#12200", "Carlos Ruiz", "AA123BB", "Bahía Blanca - Terminal", 30, "completado", 100, "Entregado"),
            ("#12201", "Miguel Torres", "EF789GH", "Bahía Blanca - Terminal", 31, "completado", 100, "Entregado"),
            ("#12202", "Pedro Ramírez", "XY789ZA", "Buenos Aires - Puerto", 28, "completado", 100, "Entregado"),
            ("#12203", "Roberto Gómez", "BC456CD", "Buenos Aires - Puerto", 29, "completado", 100, "Entregado"),
        ],
    ),
    (
        "d-12", "Campaña Girasol Mayo", "p-2", "c-3", "Junín, Buenos Aires",
        "Entrada Sur (Lat: -33.0100, Lng: -60.7200)", "Girasol", "a-2", "v-2",
        date(2026, 5, 12), date(2026, 5, 28), "activo",
        [
            ("#12210", "Carlos Ruiz", "AA123BB", "Necochea - Puerto Quequén", 32, "completado", 100, "Entregado"),
            ("#12211", "Roberto Gómez", "BC456CD", "Bahía Blanca - Terminal", 30.5, "completado", 100, "Entregado"),
        ],
    ),
    (
        "d-13", "Campaña Soja Mayo", "p-1", "c-2", "Venado Tuerto, Santa Fe",
        "Entrada Norte (Lat: -32.9442, Lng: -60.6505)", "Soja", "a-1", "v-2",
        date(2026, 5, 20), date(2026, 6, 5), "activo",
        [
            ("#12220", "Miguel Torres", "EF789GH", "Puerto San Martín", 29.5, "completado", 100, "Entregado"),
            ("#12221", "Pedro Ramírez", "XY789ZA", "Puerto San Martín", 30, "completado", 100, "Entregado"),
            ("#12222", "Carlos Ruiz", "AA123BB", "Rosario - Terminal", 28, "completado", 100, "Entregado"),
        ],
    ),
    (
        "d-8", "Campaña Trigo Norte", "p-1", "c-2", "Salta Capital, Salta",
        "Entrada Norte (Lat: -32.9442, Lng: -60.6505)", "Trigo", "a-2", "v-1",
        date(2026, 7, 5), date(2026, 7, 22), "activo",
        [
            ("#12390", "Miguel Torres", "EF789GH", "Rosario - Terminal", 32, "en_viaje", 45, "Viaje normal"),
            ("#12391", "Carlos Ruiz", "AA123BB", "Rosario - Terminal", 30.5, "en_viaje", 82, "Llegada anticipada"),
            ("#12392", "Pedro Ramírez", "XY789ZA", "San Lorenzo - Puerto", 29, "retrasado", 55, "Corte de ruta en km 120"),
            ("#12393", "Sin asignar", "-", "San Lorenzo - Puerto", 28, "pendiente", 0, "Pendiente asignación"),
            ("#12394", "Roberto Gómez", "BC456CD", "Rosario - Terminal", 31, "completado", 100, "Entregado"),
        ],
    ),
    (
        "d-9", "Campaña Girasol Sur (finalizada)", "p-2", "c-3", "Tandil, Buenos Aires",
        "Entrada Sur (Lat: -33.0100, Lng: -60.7200)", "Girasol", "a-1", "v-2",
        date(2026, 6, 10), date(2026, 6, 28), "activo",
        [
            ("#12310", "Carlos Ruiz", "AA123BB", "Necochea - Puerto Quequén", 30, "completado", 100, "Entregado"),
            ("#12311", "Miguel Torres", "EF789GH", "Necochea - Puerto Quequén", 32.5, "completado", 100, "Entregado"),
            ("#12312", "Roberto Gómez", "BC456CD", "Necochea - Puerto Quequén", 28, "completado", 100, "Entregado con demora menor"),
        ],
    ),
    (
        "d-10", "Campaña Soja Express", "p-2", "c-3", "San Nicolás, Buenos Aires",
        "Entrada Sur (Lat: -33.0100, Lng: -60.7200)", "Soja", "a-1", "v-1",
        date(2026, 7, 14), date(2026, 7, 20), "activo",
        [
            ("#12395", "Sin asignar", "-", "Puerto San Martín", 29, "pendiente", 0, "Pendiente asignación"),
            ("#12396", "Sin asignar", "-", "Puerto San Martín", 30, "pendiente", 0, "Pendiente asignación"),
        ],
    ),
    (
        "d-4", "Campaña Girasol 2026", "p-1", "c-1", "Pergamino, Buenos Aires",
        "Entrada Norte (Lat: -32.9442, Lng: -60.6505)", "Girasol", "a-2", "v-1",
        date(2026, 8, 5), date(2026, 8, 25), "borrador",
        [
            ("#12370", "Carlos Ruiz", "AA123BB", "Buenos Aires - Puerto", 30, "borrador", 0, ""),
            ("#12371", "Miguel Torres", "EF789GH", "Buenos Aires - Puerto", 31.5, "borrador", 0, ""),
            ("#12372", "Pedro Ramírez", "XY789ZA", "Bahía Blanca - Terminal", 28, "borrador", 0, ""),
            ("#12373", "Roberto Gómez", "BC456CD", "Bahía Blanca - Terminal", 29.5, "borrador", 0, ""),
        ],
    ),
    (
        "d-5", "Campaña Trigo Sur", "p-2", "c-3", "Tres Arroyos, Buenos Aires",
        "Entrada Sur (Lat: -33.0100, Lng: -60.7200)", "Trigo", "a-1", "v-2",
        date(2026, 7, 25), date(2026, 8, 2), "borrador",
        [
            ("#12375", "Miguel Torres", "EF789GH", "Necochea - Puerto Quequén", 33, "borrador", 0, ""),
        ],
    ),
    (
        "d-6", "Campaña Soja Tardía", "p-1", "c-2", "Venado Tuerto, Santa Fe",
        "Entrada Norte (Lat: -32.9442, Lng: -60.6505)", "Soja", "a-2", "v-2",
        date(2026, 7, 18), date(2026, 7, 30), "borrador",
        [
            ("#12380", "Carlos Ruiz", "AA123BB", "Rosario - Terminal", 28.5, "en_viaje", 20, "Viaje iniciado"),
            ("#12381", "Pedro Ramírez", "XY789ZA", "Rosario - Terminal", 30, "borrador", 0, ""),
            ("#12382", "Roberto Gómez", "BC456CD", "Puerto San Martín", 27, "borrador", 0, ""),
        ],
    ),
    (
        "d-7", "Campaña Maíz Tardío (sin viajes)", "p-2", "c-3", "Junín, Buenos Aires",
        "Entrada Sur (Lat: -33.0100, Lng: -60.7200)", "Maíz", "a-1", "v-1",
        date(2026, 10, 1), date(2026, 10, 15), "borrador",
        [],
    ),
    (
        "d-2", "Campaña Maíz Primavera", "p-2", "c-3", "Campo Verde SRL",
        "Campo San Pedro", "Maíz", "a-1", "v-2",
        date(2026, 9, 15), date(2026, 10, 1), "borrador",
        [
            ("#12360", "Carlos Ruiz", "AA123BB", "Puerto San Martín", 28.5, "borrador", 0, ""),
            ("#12361", "Roberto Gómez", "BC456CD", "Puerto San Martín", 27.5, "borrador", 0, ""),
        ],
    ),
]

# ----------------------------- Mensajería -----------------------------
# (id, chofer, despacho_id, viaje_id, origen, destino, no_leidos, mensajes)
# Mensaje: (id, autor, texto, fecha, leido)
_CONVERSACIONES = [
    (
        "conv-1", "ch-1", "d-8", "#12391", "Salta Capital", "Rosario - Terminal", 2,
        [
            ("m-1", "admin", "Hola Carlos, ¿cómo va el viaje?", datetime(2026, 7, 13, 8, 15), True),
            ("m-2", "chofer", "Todo bien, voy por la ruta 34. Sin problemas hasta ahora.", datetime(2026, 7, 13, 8, 22), True),
            ("m-3", "chofer", "Perfecto, ya estoy llegando a destino.", datetime(2026, 7, 13, 10, 5), False),
        ],
    ),
    (
        "conv-2", "ch-4", "d-8", "#12392", "Salta Capital", "San Lorenzo - Puerto", 1,
        [
            ("m-4", "chofer", "Hay un problema en la ruta, corte total en el km 120. Voy a demorar.", datetime(2026, 7, 13, 9, 40), False),
        ],
    ),
    (
        "conv-3", "ch-2", "d-8", "#12390", "Salta Capital", "Rosario - Terminal", 0,
        [
            ("m-5", "admin", "Miguel, ¿pudiste cargar completo?", datetime(2026, 7, 12, 18, 0), True),
            ("m-6", "chofer", "Sí, 32 toneladas. Salgo mañana temprano.", datetime(2026, 7, 12, 18, 12), True),
            ("m-7", "admin", "Perfecto, buen viaje.", datetime(2026, 7, 13, 7, 30), True),
        ],
    ),
    (
        "conv-4", "ch-3", "d-8", "#12394", "Salta Capital", "Rosario - Terminal", 0,
        [
            ("m-8", "chofer", "Descarga terminada, todo en orden. Firmaron el remito.", datetime(2026, 7, 12, 16, 45), True),
            ("m-9", "admin", "Gracias Roberto, quedó registrado.", datetime(2026, 7, 12, 17, 0), True),
        ],
    ),
    (
        "conv-5", "ch-1", "d-3", "#12332", "Pergamino", "Puerto San Martín", 0,
        [
            ("m-10", "admin", "Carlos, este es el canal del viaje a Puerto San Martín.", datetime(2026, 7, 13, 6, 50), True),
        ],
    ),
]


async def sembrar_datos_demo() -> None:
    """Inserta usuarios, catálogos, campañas y conversaciones de demo."""
    async with fabrica_sesiones() as sesion:
        # Si ya hay usuarios, la base no está vacía: no se re-siembra.
        if await UsuarioDAO(sesion).contar() > 0:
            return

        # Usuarios (admins y vendedores con la misma contraseña de demo).
        password_hash = hashear_password(PASSWORD_DEMO)
        sesion.add_all(
            [
                Usuario(id=id_, nombre=nombre, dni=dni, email=email, rol=rol,
                        password_hash=password_hash)
                for id_, nombre, dni, email, rol in _USUARIOS
            ]
        )

        # Catálogos.
        sesion.add_all(
            [
                Productor(
                    id=id_, nombre=nombre,
                    campos=[Campo(id=cid, nombre=cnombre) for cid, cnombre in campos],
                )
                for id_, nombre, campos in _PRODUCTORES
            ]
        )
        sesion.add_all(
            [Material(nombre=n, codigo_grano_afip=c) for n, c in _MATERIALES]
        )
        sesion.add_all(
            [
                Transportista(
                    id=tid,
                    nombre=nombre,
                    cuit=cuit,
                    camiones=[
                        Camion(id=cid, dominio=dominio, modelo=modelo)
                        for cid, dominio, modelo in camiones
                    ],
                )
                for tid, nombre, cuit, camiones in _TRANSPORTISTAS
            ]
        )
        await sesion.flush()
        choferes = {
            nombre: Chofer(id=id_, nombre=nombre, transportista_id=tid)
            for id_, nombre, tid in _CHOFERES
        }
        sesion.add_all(choferes.values())
        await sesion.flush()

        # Despachos con sus viajes (los IDs y estados son los del mock).
        for (id_, nombre, productor, campo, origen, entrada, material, admin,
             vendedor, inicio, llegada, estado, viajes) in _DESPACHOS:
            sesion.add(
                Despacho(
                    id=id_, nombre=nombre, productor_id=productor, campo_id=campo,
                    origen=origen, entrada_campo=entrada, material=material,
                    administrador_id=admin, vendedor_id=vendedor,
                    fecha_inicio=inicio, fecha_llegada_estimada=llegada, estado=estado,
                    viajes=[
                        Viaje(
                            id=vid,
                            # El chofer del catálogo si coincide el nombre;
                            # el mock tiene viajes con choferes "sueltos".
                            chofer_id=(
                                choferes[chofer].id if chofer in choferes else None
                            ),
                            chofer_nombre=chofer, dominio=dominio, destino=destino,
                            toneladas=toneladas, estado=estado_v,
                            progreso=progreso, observaciones=obs,
                        )
                        for vid, chofer, dominio, destino, toneladas, estado_v,
                            progreso, obs in viajes
                    ],
                )
            )

        # Conversaciones vinculadas a los viajes de arriba.
        for (id_, chofer_id, despacho_id, viaje_id, origen, destino, no_leidos,
             mensajes) in _CONVERSACIONES:
            chofer = next(c for c in choferes.values() if c.id == chofer_id)
            dominio_conv = next(
                (
                    dominio
                    for tid, _, _, camiones in _TRANSPORTISTAS
                    if tid == chofer.transportista_id
                    for _, dominio, _ in camiones
                ),
                "",
            )
            conversacion = Conversacion(
                id=id_, chofer_id=chofer.id, chofer_nombre=chofer.nombre,
                dominio=dominio_conv, despacho_id=despacho_id, viaje_id=viaje_id,
                origen=origen, destino=destino, no_leidos=no_leidos,
            )
            sesion.add(conversacion)
            await sesion.flush()
            sesion.add_all(
                [
                    Mensaje(id=mid, conversacion_id=conversacion.id, autor=autor,
                            texto=texto, fecha=fecha, leido=leido)
                    for mid, autor, texto, fecha, leido in mensajes
                ]
            )

        await sesion.commit()


if __name__ == "__main__":
    # Ejecución manual: crea las tablas y siembra.
    async def _main() -> None:
        await crear_tablas()
        await sembrar_datos_demo()
        print(f"Seed listo. Login demo: {EMAIL_DEMO} / {PASSWORD_DEMO}")

    asyncio.run(_main())
