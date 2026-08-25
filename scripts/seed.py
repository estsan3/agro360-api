"""Seed de datos de demo, espejo del mock del front Angular (mock-data.ts).

Replica los mismos IDs y datos del mock para que la UI se vea idéntica
al apagar el interceptor. Se ejecuta automáticamente al iniciar la API
en dev (si la base está vacía) o manualmente con:
    poetry run python -m scripts.seed
"""

import asyncio
from datetime import date, datetime, timedelta
from pathlib import Path

from app.core.database import crear_tablas, fabrica_sesiones
from app.core.seguridad import hashear_password
from app.modulos.auth.dao import UsuarioDAO
from app.modulos.auth.models import Usuario
from app.modulos.cartas_porte.documento import generar_pdf_cpe_demo
from app.modulos.cartas_porte.models import CartaPorte
from app.modulos.catalogos.models import (
    Camion,
    Campo,
    Chofer,
    Material,
    Productor,
    PuntoEntrada,
    ResponsableProductor,
    Transportista,
)
from app.modulos.despachos.models import Despacho, Viaje
from app.modulos.liquidaciones.bo import LiquidacionesBO
from app.modulos.liquidaciones.models import MovimientoCtacte
from app.modulos.lista_espera.models import EntradaLista
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
# Volumen de demo para pantallas ABM (paginación, filtros, búsqueda).
CANTIDAD_TRANSPORTISTAS = 30
CANTIDAD_PRODUCTORES = 30
CAMIONES_POR_TRANSPORTISTA = 10
CHOFERES_POR_TRANSPORTISTA = 10
CAMPOS_POR_PRODUCTOR = 10
RESPONSABLES_POR_PRODUCTOR = 10

# Códigos de grano según tabla de ARCA/AFIP (consultarTiposGrano).
# Códigos WSCPE consultarTiposGrano (homo): Maíz=19, Soja=23.
_MATERIALES = [("Soja", 23), ("Maíz", 19), ("Girasol", 27), ("Trigo", 1)]

# Choferes del mock original (referenciados en despachos y mensajería).
_CHOFERES_CORE = [
    ("ch-1", "Carlos", "Ruiz", "t-1", "cm-1"),
    ("ch-2", "Miguel", "Torres", "t-1", "cm-2"),
    ("ch-3", "Roberto", "Gómez", "t-2", "cm-3"),
    ("ch-4", "Pedro", "Ramírez", "t-2", "cm-4"),
]

# Camiones iniciales del mock (patentes usadas en viajes de demo).
_CAMIONES_CORE = {
    "t-1": [
        ("cm-1", "AA123BB", "Mercedes 1114", "Mercedes-Benz", "Camión"),
        ("cm-2", "EF789GH", "Volvo FH 420", "Volvo", "Tractor"),
    ],
    "t-2": [
        ("cm-3", "BC456CD", "Scania R450", "Scania", "Tractor"),
        ("cm-4", "XY789ZA", "Iveco Tector 170", "Iveco", "Camión"),
    ],
}

# Campos iniciales del mock (referenciados en despachos).
_CAMPOS_CORE = {
    "p-1": [
        ("c-1", "Campo Norte", "CN-01", -33.12, -60.95, "Pergamino", "Buenos Aires"),
        ("c-2", "Campo Los Nogales", "LN-02", -33.89, -60.57, "Rojas", "Buenos Aires"),
    ],
    "p-2": [
        ("c-3", "Campo San Pedro", "SP-01", -33.68, -59.66, "San Pedro", "Buenos Aires"),
    ],
}

_PUNTOS_CORE = {
    "c-1": [("pe-c1-1", "Entrada Norte", 1, -32.9442, -60.6505, "Acceso principal por ruta 34")],
    "c-2": [("pe-c2-1", "Entrada Sur", 1, -33.89, -60.57, "Portón sur del lote")],
    "c-3": [("pe-c3-1", "Entrada Sur", 1, -33.01, -60.72, "Ingreso por camino vecinal")],
}

_NOMBRES_TRANSPORTISTA = [
    "Transportes del Plata",
    "Flota Pampeana",
    "Cargas del Sur",
    "Transagro Logística",
    "Ruta 9 Transportes",
    "El Trigal Cargas",
    "Pampeana Express",
    "Granos en Ruta",
    "Logística Benito",
    "Transporte Litoral",
    "Cargas del Oeste",
    "Flecha Verde",
    "Transcampo SA",
    "Ruta del Maíz",
    "Logística Venado Tuerto",
    "Transportes del Centeno",
    "Cargas del Paraná",
    "Flota del Trigo",
    "Transaustral Cargas",
    "Logística Junín",
    "Transporte Chacabuco",
    "Ruta 34 Logística",
    "Cargas del Norte",
    "Flota Santa Fe",
    "Transcereal SA",
    "Logística Pergamino",
    "Transportes del Sud",
    "Cargas del Litoral",
    "Ruta Pampeana",
    "Logística Rosario",
]

_NOMBRES_PRODUCTOR = [
    "Agro SA",
    "Campo Verde SRL",
    "Estancia La Aurora",
    "Campos del Plata",
    "Productores Unidos",
    "Agropecuaria San Martín",
    "La Pampa Graneles",
    "Campos del Sur",
    "Estancia El Trigal",
    "Agro Litoral SA",
    "Productora del Paraná",
    "Campos Pampeanos",
    "Estancia Los Alamos",
    "Agro Norte SRL",
    "Productores del Oeste",
    "Campos de la Ribera",
    "Estancia Santa Clara",
    "Agrocentro SA",
    "La Esperanza Agrícola",
    "Campos del Centeno",
    "Productora Venado Tuerto",
    "Estancia El Rincón",
    "Agro Junín",
    "Campos del Trigo",
    "Estancia La Posta",
    "Productores del Litoral",
    "Agro Chacabuco",
    "Campos del Maíz",
    "Estancia Las Acacias",
    "Agro Rosario Norte",
]

_LOCALIDADES = [
    ("Pergamino", "Buenos Aires", "Pergamino"),
    ("Venado Tuerto", "Santa Fe", "General López"),
    ("Rojas", "Buenos Aires", "Rojas"),
    ("Junín", "Buenos Aires", "Junín"),
    ("Salta Capital", "Salta", "Capital"),
    ("Rosario", "Santa Fe", "Rosario"),
    ("Tandil", "Buenos Aires", "Tandil"),
    ("San Nicolás", "Buenos Aires", "San Nicolás"),
    ("Tres Arroyos", "Buenos Aires", "Tres Arroyos"),
    ("Necochea", "Buenos Aires", "Necochea"),
    ("Bahía Blanca", "Buenos Aires", "Bahía Blanca"),
    ("Pilar", "Buenos Aires", "Pilar"),
    ("Rafaela", "Santa Fe", "Castellanos"),
    ("Villa María", "Córdoba", "General San Martín"),
    ("Paraná", "Entre Ríos", "Paraná"),
]

_MARCAS_CAMION = ["Scania", "Volvo", "Mercedes-Benz", "Iveco", "DAF", "MAN"]
_TIPOS_CAMION = ["Camión", "Tractor", "Bitren", "Acoplado"]
_TIPOS_LICENCIA = ["B1", "B2", "C", "E1", "E2"]
_APELLIDOS = [
    "García", "Rodríguez", "López", "Martínez", "Fernández", "González",
    "Pérez", "Sánchez", "Romero", "Díaz", "Torres", "Ruiz", "Gómez", "Ramírez",
]
_NOMBRES_PERSONA = [
    "Carlos", "Miguel", "Roberto", "Pedro", "Juan", "Luis", "Diego", "Martín",
    "Fernando", "Alejandro", "Sergio", "Pablo", "Andrés", "Gabriel",
]

_LETRAS_PATENTE = "ABCDEFGHJKLMNPRSTVWXYZ"


def _cuit_demo(indice: int) -> str:
    """CUIT ficticio con formato válido de longitud."""
    base = 20_000_000 + indice * 137
    return f"30-{base % 100_000_000:08d}-{indice % 10}"


def _patente_unica(indice: int) -> str:
    """Genera patentes únicas estilo argentino (AA123BB)."""
    a = _LETRAS_PATENTE[indice % len(_LETRAS_PATENTE)]
    b = _LETRAS_PATENTE[(indice // len(_LETRAS_PATENTE)) % len(_LETRAS_PATENTE)]
    num = 100 + (indice % 899)
    c = _LETRAS_PATENTE[(indice // 100) % len(_LETRAS_PATENTE)]
    d = _LETRAS_PATENTE[(indice // 1000) % len(_LETRAS_PATENTE)]
    return f"{a}{b}{num}{c}{d}"


def _modelo_camion(indice: int) -> str:
    modelos = [
        "Scania R450", "Volvo FH 420", "Mercedes Actros 1845", "Iveco Tector 170",
        "DAF XF 480", "MAN TGX 18.440", "Scania G410", "Volvo FM 380",
        "Mercedes 1114", "Iveco Stralis 460",
    ]
    return modelos[indice % len(modelos)]


def _datos_ui_transportista(
    nombre: str, indice: int, activo: bool
) -> dict[str, str | bool]:
    loc = _LOCALIDADES[indice % len(_LOCALIDADES)]
    return {
        "nombre_fantasia": nombre,
        "razon_social": f"{nombre} SRL" if indice % 3 else f"{nombre} SA",
        "direccion": f"Av. Belgrano {1200 + indice}, {loc[0]}",
        "email": f"contacto{indice + 1}@{nombre.lower().replace(' ', '')[:12]}.com.ar",
        "telefono": f"+54 9 11 {5000 + indice:04d}-{1000 + indice:04d}",
        "pagina_web": f"https://www.{nombre.lower().replace(' ', '-')[:18]}.com.ar",
        "_activo_override": activo,
    }


def _datos_ui_camion(marca: str, tipo: str, indice: int) -> dict[str, str]:
    return {
        "marca": marca,
        "tipo": tipo,
        "nro_chasis": f"CH{indice:08d}",
        "nro_motor": f"MO{indice:08d}",
    }


def _datos_ui_chofer(nombre: str, apellido: str, indice: int) -> dict[str, str | int]:
    return {
        "nombre": nombre,
        "apellido": apellido,
        "documento": f"{20_000_000 + indice}",
        "direccion": f"Calle {indice + 10} N° {100 + indice}",
        "telefono": f"+54 9 341 {500 + indice:04d}-{1000 + indice:04d}",
        "edad": 28 + (indice % 25),
        "fecha_nacimiento": f"{1970 + (indice % 30):04d}-{(indice % 12) + 1:02d}-15",
        "licencia_tipo": _TIPOS_LICENCIA[indice % len(_TIPOS_LICENCIA)],
        "licencia_vencimiento": f"202{6 + (indice % 3)}-{(indice % 12) + 1:02d}-28",
    }


def _datos_ui_productor(nombre: str, indice: int) -> dict[str, str]:
    loc = _LOCALIDADES[(indice + 3) % len(_LOCALIDADES)]
    vendedor = "v-1" if indice % 2 == 0 else "v-2"
    return {
        "nombre_fantasia": nombre,
        "razon_social": f"{nombre} SA" if indice % 2 == 0 else f"{nombre} SRL",
        "direccion_fiscal": f"Ruta {indice + 5} km {indice * 2}, {loc[0]}, {loc[1]}",
        "email": f"admin{indice + 1}@{nombre.lower().replace(' ', '')[:10]}.com.ar",
        "telefono": f"+54 9 {3400 + indice}-{2000 + indice:04d}",
        "vendedor_id": vendedor,
        "notas": "Productor demo con datos variados para pruebas de UI."
        if indice % 5 == 0
        else "",
    }


def _datos_ui_campo(indice: int, localidad: str, provincia: str, partido: str) -> dict:
    return {
        "codigo": f"CP-{indice:03d}",
        "superficie_ha": 150 + (indice * 17) % 800,
        "localidad": localidad,
        "provincia": provincia,
        "partido": partido,
        "direccion": f"Camino rural s/n, {localidad}",
        "latitud": -34.0 + (indice % 20) * 0.15,
        "longitud": -61.0 - (indice % 15) * 0.12,
        "contacto_nombre": f"{_NOMBRES_PERSONA[indice % len(_NOMBRES_PERSONA)]} {_APELLIDOS[indice % len(_APELLIDOS)]}",
        "contacto_telefono": f"+54 9 {3400 + indice}-{3000 + indice:04d}",
    }


def _construir_camion(
    camion_id: str,
    transportista_id: str,
    dominio: str,
    modelo: str,
    marca: str,
    tipo: str,
    indice_global: int,
    activo: bool = True,
) -> Camion:
    return Camion(
        id=camion_id,
        dominio=dominio,
        modelo=modelo,
        transportista_id=transportista_id,
        activo=activo,
        capacidad_tn=30.0 + (indice_global % 4) * 5.0,
        tipo_unidad=tipo or "tolva",
        datos_ui=_datos_ui_camion(marca, tipo, indice_global),
    )


def _construir_puntos_entrada(
    campo_id: str, indice_campo: int, datos_campo: dict
) -> list[PuntoEntrada]:
    if campo_id in _PUNTOS_CORE:
        return [
            PuntoEntrada(
                id=pid,
                nombre=nombre,
                orden=orden,
                latitud=lat,
                longitud=lng,
                observacion=obs,
            )
            for pid, nombre, orden, lat, lng, obs in _PUNTOS_CORE[campo_id]
        ]
    lat_base = float(datos_campo.get("latitud", -33.0))
    lng_base = float(datos_campo.get("longitud", -60.0))
    cantidad = 1 + (indice_campo % 3)  # 1 a 3 puntos según casuística
    puntos: list[PuntoEntrada] = []
    for n in range(cantidad):
        puntos.append(
            PuntoEntrada(
                id=f"pe-{campo_id}-{n + 1}",
                nombre=f"Entrada {'Norte Sur Este Oeste'.split()[n % 4]}",
                orden=n + 1,
                latitud=lat_base + n * 0.002,
                longitud=lng_base - n * 0.001,
                observacion="Portón principal" if n == 0 else f"Acceso alternativo {n + 1}",
            )
        )
    return puntos


def _construir_catalogos_demo() -> tuple[list[Productor], list[Transportista], list[Chofer]]:
    """Arma 30 productores y 30 transportistas con hijos anidados."""
    productores: list[Productor] = []
    transportistas: list[Transportista] = []
    choferes: list[Chofer] = []
    indice_patente = 0

    for i in range(CANTIDAD_TRANSPORTISTAS):
        tid = f"t-{i + 1}"
        nombre = _NOMBRES_TRANSPORTISTA[i]
        activo = i not in {27, 28, 29}  # 3 inactivos al final
        ui = _datos_ui_transportista(nombre, i, activo)
        camiones: list[Camion] = []

        # Camiones core del mock (t-1, t-2) o generados.
        if tid in _CAMIONES_CORE:
            for cid, dominio, modelo, marca, tipo in _CAMIONES_CORE[tid]:
                camiones.append(
                    _construir_camion(
                        cid, tid, dominio, modelo, marca, tipo, indice_patente
                    )
                )
                indice_patente += 1
        while len(camiones) < CAMIONES_POR_TRANSPORTISTA:
            n = len(camiones) + 1
            cid = f"cm-{tid}-{n}"
            dominio = _patente_unica(indice_patente)
            indice_patente += 1
            marca = _MARCAS_CAMION[i % len(_MARCAS_CAMION)]
            tipo = _TIPOS_CAMION[(i + n) % len(_TIPOS_CAMION)]
            camiones.append(
                _construir_camion(
                    cid,
                    tid,
                    dominio,
                    _modelo_camion(indice_patente),
                    marca,
                    tipo,
                    indice_patente,
                    activo=not (n == CAMIONES_POR_TRANSPORTISTA and i % 7 == 0),
                )
            )

        transportistas.append(
            Transportista(
                id=tid,
                nombre=nombre,
                cuit="30712345671" if tid == "t-1" else "30709876543" if tid == "t-2" else _cuit_demo(100 + i),
                activo=activo,
                es_flota_propia=(tid == "t-1"),
                datos_ui={k: v for k, v in ui.items() if k != "_activo_override"},
                camiones=camiones,
            )
        )

        # Choferes: primero los del mock, luego generados hasta 10.
        choferes_transportista: list[tuple[str, str, str, str | None]] = []
        for ch_id, nom, ape, t_id, cm_id in _CHOFERES_CORE:
            if t_id == tid:
                choferes_transportista.append((ch_id, nom, ape, cm_id))
        while len(choferes_transportista) < CHOFERES_POR_TRANSPORTISTA:
            n = len(choferes_transportista) + 1
            ch_id = f"ch-{tid}-{n}"
            nom = _NOMBRES_PERSONA[(i + n) % len(_NOMBRES_PERSONA)]
            ape = _APELLIDOS[(i * 3 + n) % len(_APELLIDOS)]
            cm_id = camiones[(n - 1) % len(camiones)].id if n % 4 != 0 else None
            choferes_transportista.append((ch_id, nom, ape, cm_id))

        for j, (ch_id, nom, ape, cm_id) in enumerate(choferes_transportista):
            indice_chofer = i * CHOFERES_POR_TRANSPORTISTA + j
            choferes.append(
                Chofer(
                    id=ch_id,
                    nombre=f"{nom} {ape}",
                    transportista_id=tid,
                    camion_id=cm_id,
                    cuit=_cuit_demo(300 + indice_chofer),
                    activo=j != CHOFERES_POR_TRANSPORTISTA - 1 or i % 9 != 0,
                    datos_ui=_datos_ui_chofer(nom, ape, indice_chofer),
                )
            )

    for i in range(CANTIDAD_PRODUCTORES):
        pid = f"p-{i + 1}"
        nombre = _NOMBRES_PRODUCTOR[i]
        activo = i not in {26, 27, 28}  # 3 inactivos
        ui = _datos_ui_productor(nombre, i)
        campos: list[Campo] = []

        if pid in _CAMPOS_CORE:
            for cid, cnombre, codigo, lat, lng, loc, prov in _CAMPOS_CORE[pid]:
                datos = {
                    "codigo": codigo,
                    "latitud": lat,
                    "longitud": lng,
                    "localidad": loc,
                    "provincia": prov,
                    "partido": loc,
                }
                campos.append(
                    Campo(
                        id=cid,
                        nombre=cnombre,
                        productor_id=pid,
                        activo=True,
                        nro_renspa="12.345.6.78901/00" if len(campos) == 0 else None,
                        datos_ui=_datos_ui_campo(i, loc, prov, loc),
                        puntos_entrada=_construir_puntos_entrada(cid, len(campos), datos),
                    )
                )

        while len(campos) < CAMPOS_POR_PRODUCTOR:
            n = len(campos) + 1
            cid = f"c-{pid}-{n}"
            loc, prov, partido = _LOCALIDADES[(i + n) % len(_LOCALIDADES)]
            nombre_campo = f"Campo {loc} {n}" if n > 1 else f"Lote {nombre.split()[0]}"
            datos = _datos_ui_campo(i * 10 + n, loc, prov, partido)
            campos.append(
                Campo(
                    id=cid,
                    nombre=nombre_campo,
                    productor_id=pid,
                    activo=not (n == CAMPOS_POR_PRODUCTOR and i % 6 == 0),
                    nro_renspa="12.345.6.78901/00" if len(campos) == 0 else None,
                    datos_ui=datos,
                    puntos_entrada=_construir_puntos_entrada(cid, n, datos),
                )
            )

        responsables = [
            ResponsableProductor(
                id=f"rp-{pid}-{j + 1}",
                productor_id=pid,
                nombre=_NOMBRES_PERSONA[(i + j) % len(_NOMBRES_PERSONA)],
                apellido=_APELLIDOS[(i + j * 2) % len(_APELLIDOS)],
                telefono=f"+54 9 11 {6000 + i:04d}-{j:04d}",
                documento=f"{25_000_000 + i * 10 + j}",
                activo=j != RESPONSABLES_POR_PRODUCTOR - 1 or i % 8 != 0,
            )
            for j in range(RESPONSABLES_POR_PRODUCTOR)
        ]

        productores.append(
            Productor(
                id=pid,
                nombre=nombre,
                cuit=_cuit_demo(200 + i),
                activo=activo,
                datos_ui=ui,
                campos=campos,
                responsables=responsables,
            )
        )

    return productores, transportistas, choferes

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


def _movimientos_flete_demo(
    *,
    transportista_id: str,
    detalle: str,
    toneladas: float,
    tarifa: float,
    dador_viaje: str,
    fecha: date,
    sufijo: str,
    tarifa_default: float = 28000.0,
    comision_pct: float = 8.0,
    iva_pct: float = 21.0,
    ley_pct: float = 0.6,
) -> list[MovimientoCtacte]:
    """Arma los 5 renglones de un flete (misma lógica que LiquidacionesService)."""
    prefs = {
        "flete": "FL",
        "iva_flete": "IVAF",
        "comision": "COM",
        "iva_comision": "IVAC",
        "ley_25413": "LEY",
    }
    detalles = {
        "flete": detalle,
        "iva_flete": "IVA flete",
        "comision": "Comisión",
        "iva_comision": "IVA comisión",
        "ley_25413": "Imp. Ley 25.413",
    }
    lineas = LiquidacionesBO.calcular_movimientos_flete(
        toneladas=toneladas,
        tarifa=tarifa or tarifa_default,
        comision_pct=comision_pct,
        iva_pct=iva_pct,
        ley_pct=ley_pct,
    )
    return [
        MovimientoCtacte(
            transportista_id=transportista_id,
            fecha=fecha,
            concepto=concepto,
            comprobante=f"{prefs[concepto]}-{sufijo}",
            detalle=detalles[concepto],
            dador_viaje=dador_viaje,
            toneladas=toneladas if concepto == "flete" else None,
            tarifa=tarifa if concepto == "flete" else None,
            debe=debe,
            haber=haber,
        )
        for concepto, debe, haber in lineas
    ]


def _sembrar_cuenta_corriente_demo() -> list[MovimientoCtacte]:
    """Fletes y movimientos manuales para probar Liquidaciones."""
    hoy = date.today()
    movs: list[MovimientoCtacte] = []
    fletes = [
        ("t-1", "Flete Rosario - Terminal", 32.0, 28500.0, "COFCO", 18, "SEED01"),
        ("t-1", "Flete Bahía Blanca - Terminal", 30.0, 31000.0, "FEDEA", 14, "SEED02"),
        ("t-1", "Flete Necochea - Puerto Quequén", 30.5, 29500.0, "COFCO", 9, "SEED03"),
        ("t-1", "Flete Puerto San Martín", 28.5, 30000.0, "FEDEA", 4, "SEED04"),
        ("t-2", "Flete Buenos Aires - Puerto", 29.0, 32000.0, "COFCO", 12, "SEED05"),
        ("t-2", "Flete Rosario - Terminal", 31.0, 28000.0, "Otro", 6, "SEED06"),
        ("t-3", "Flete Bahía Blanca - Terminal", 33.0, 30500.0, "FEDEA", 10, "SEED07"),
        ("t-3", "Flete Necochea - Puerto Quequén", 28.0, 29000.0, "COFCO", 2, "SEED08"),
    ]
    for tid, detalle, tn, tarifa, dador, dias, sufijo in fletes:
        movs.extend(
            _movimientos_flete_demo(
                transportista_id=tid,
                detalle=detalle,
                toneladas=tn,
                tarifa=tarifa,
                dador_viaje=dador,
                fecha=hoy - timedelta(days=dias),
                sufijo=sufijo,
            )
        )
    manuales = [
        ("t-1", "gasoil", "Carga YPF ruta 9", 85000.0, 0.0, 7),
        ("t-1", "transferencia", "Pago parcial liquidación quincena", 0.0, 450000.0, 3),
        ("t-1", "anticipo", "Anticipo campaña soja", 120000.0, 0.0, 1),
        ("t-2", "cheque", "Cheque diferido 30d", 0.0, 200000.0, 5),
        ("t-3", "gasoil", "Vale gasoil Bahía", 42000.0, 0.0, 8),
    ]
    for tid, concepto, detalle, debe, haber, dias in manuales:
        movs.append(
            MovimientoCtacte(
                transportista_id=tid,
                fecha=hoy - timedelta(days=dias),
                concepto=concepto,
                comprobante=f"MAN-{concepto[:3].upper()}{dias:02d}",
                detalle=detalle,
                debe=debe,
                haber=haber,
            )
        )
    return movs


def _sembrar_lista_espera_demo(
    transportistas: list[Transportista], choferes_lista: list[Chofer]
) -> list[EntradaLista]:
    """Cola FIFO de demo: 5 fleteros anotados (sin flota propia).

    Orden: el más antiguo primero (listo para ofrecer al asignar por lista).
    """
    ahora = datetime.utcnow()
    por_id = {t.id: t for t in transportistas}
    por_chofer = {c.id: c for c in choferes_lista}
    # Unidades de t-2..t-6 (terceros) con chofer vinculado a camión.
    candidatos: list[tuple[str, str, str]] = []
    for tid in ("t-2", "t-3", "t-4", "t-5", "t-6"):
        t = por_id.get(tid)
        if t is None or t.es_flota_propia:
            continue
        camiones = {c.id: c for c in t.camiones if c.activo}
        for chofer in choferes_lista:
            if chofer.transportista_id != tid or not chofer.activo or not chofer.camion_id:
                continue
            camion = camiones.get(chofer.camion_id)
            if camion is None:
                continue
            candidatos.append((tid, chofer.id, camion.id))
            break

    entradas: list[EntradaLista] = []
    for i, (tid, ch_id, cm_id) in enumerate(candidatos[:5]):
        t = por_id[tid]
        chofer = por_chofer[ch_id]
        camion = next(c for c in t.camiones if c.id == cm_id)
        entradas.append(
            EntradaLista(
                id=f"le-{i + 1}",
                empresa_id="default",
                transportista_id=tid,
                camion_id=cm_id,
                chofer_id=ch_id,
                transportista_nombre=t.nombre,
                chofer_nombre=chofer.nombre,
                dominio=camion.dominio,
                capacidad_tn=camion.capacidad_tn,
                tipo_unidad=camion.tipo_unidad or "tolva",
                estado="en_espera",
                anotado_en=ahora - timedelta(hours=5 - i, minutes=i * 7),
            )
        )
    return entradas


def _extras_cpe_despacho(despacho_id: str) -> dict:
    """Campos CPE para campañas demo que alimentan intenciones / payload AFIP."""
    base_74 = {
        "cpe_habilitada": True,
        "cpe_tipo": 74,
        "cpe_sucursal": 1,
        "cpe_cosecha": 2526,
        "cpe_cuit_solicitante": "30700000001",
        "cpe_origen_cod_provincia": 12,
        "cpe_origen_cod_localidad": 1001,
        "cpe_nro_renspa": "12.345.6.78901/00",
        "cpe_codigo_turno": "TURNO-DEMO",
        "cpe_corresponde_retiro_productor": True,
        "cpe_es_solicitante_campo": True,
        "cpe_destino_cuit": "30555666777",
        "cpe_destino_es_campo": False,
        "cpe_destino_cod_provincia": 2,
        "cpe_destino_cod_localidad": 2002,
        "cpe_destino_planta": 150,
        "cpe_peso_tara_kg_default": 15000,
        "cpe_mercaderia_fumigada": False,
        "distancia_km": 280.0,
        "tarifa_por_tn": 49240.0,
    }
    por_id = {
        "d-1": {**base_74},
        "d-3": {
            **base_74,
            "cpe_destino_planta": 220,
            "cpe_destino_cod_localidad": 2100,
            "distancia_km": 190.0,
        },
        "d-4": {
            **base_74,
            "cpe_tipo": 274,
            "cpe_sucursal": 2,
            "distancia_km": 45.0,
            "tarifa_por_tn": 12010.0,
        },
        "d-8": {
            **base_74,
            "cpe_destino_planta": 310,
            "distancia_km": 920.0,
            "tarifa_por_tn": 112000.0,
        },
    }
    return por_id.get(despacho_id, {})


def _payload_demo(
    *,
    tipo_cpe: int,
    material: str,
    origen: str,
    destino: str,
    dominio: str,
    toneladas: float,
    cod_grano: int,
    sucursal: int = 1,
    planta: int = 150,
) -> dict:
    """Payload AFIP mínimo pero completo para demos de listado/detalle."""
    tara = 15000
    bruto = int(round(toneladas * 1000)) + tara
    return {
        "metodo_wscpe": "autorizarCPEAutomotor",
        "tipo_cpe": tipo_cpe,
        "sucursal": sucursal,
        "cuit_solicitante": "30700000001",
        "origen": {
            "cod_provincia": 12,
            "cod_localidad": 1001,
            "planta": None,
            "cuit_productor": "20200000001",
            "coordenadas_gps": {
                "latitud_decimal": -32.9442,
                "longitud_decimal": -60.6505,
            },
        },
        "flags": {
            "corresponde_retiro_productor": True,
            "es_solicitante_campo": True,
        },
        "intervinientes": {},
        "datos_carga": {
            "cod_grano": cod_grano,
            "cosecha": 2526,
            "peso_bruto": bruto,
            "peso_tara": tara,
            "peso_neto": bruto - tara,
        },
        "destino": {
            "cuit": "30555666777",
            "es_destino_campo": False,
            "cod_provincia": 2,
            "cod_localidad": 2002,
            "planta": planta,
        },
        "transporte": {
            "cuit_transportista": "30712345671",
            "dominio": [dominio],
            "fecha_hora_partida": "2026-08-05T08:00:00+00:00",
            "km_recorrer": 280,
            "cuit_chofer": "20300000001",
            "tarifa": 49240.0,
            "mercaderia_fumigada": False,
        },
        "observaciones": "Seed demo Agro360",
        "_meta": {
            "material_nombre": material,
            "origen_descripcion": origen,
            "destino_descripcion": destino,
            "tipo_cpe_etiqueta": (
                "Automotor" if tipo_cpe == 74 else "Automotor flete corto"
            ),
        },
    }


def _carta_demo(
    *,
    id_: str,
    despacho_id: str,
    viaje_id: str,
    tipo_cpe: int,
    estado: str,
    material: str,
    origen: str,
    destino: str,
    dominio: str,
    toneladas: float,
    cod_grano: int,
    nro_carta_porte: str | None = None,
    nro_ctg: str | None = None,
    intentos: int = 0,
    error_detalle: str = "",
    con_pdf: bool = False,
    sucursal: int = 1,
    planta: int = 150,
) -> CartaPorte:
    payload = _payload_demo(
        tipo_cpe=tipo_cpe,
        material=material,
        origen=origen,
        destino=destino,
        dominio=dominio,
        toneladas=toneladas,
        cod_grano=cod_grano,
        sucursal=sucursal,
        planta=planta,
    )
    pdf = None
    if con_pdf and nro_carta_porte and nro_ctg:
        pdf = generar_pdf_cpe_demo(
            nro_carta_porte=nro_carta_porte,
            nro_ctg=nro_ctg,
            tipo_cpe=tipo_cpe,
            material=material,
            origen=origen,
            destino=destino,
            dominio=dominio,
            toneladas=toneladas,
            estado=estado,
        )
    return CartaPorte(
        id=id_,
        despacho_id=despacho_id,
        viaje_id=viaje_id,
        tipo_cpe=tipo_cpe,
        nro_carta_porte=nro_carta_porte,
        nro_ctg=nro_ctg,
        estado=estado,
        material=material,
        origen=origen,
        destino=destino,
        dominio=dominio,
        toneladas=toneladas,
        payload_afip=payload,
        pdf_base64=pdf,
        intentos=intentos,
        error_detalle=error_detalle,
    )


def _sembrar_cartas_porte_demo() -> list[CartaPorte]:
    """Casuísticas demo: pendiente, error, procesada (74/274) con PDF, anulada."""
    return [
        # Procesada automotor 74 — con PDF descargable
        _carta_demo(
            id_="cpe-demo-1",
            despacho_id="d-1",
            viaje_id="#12345",
            tipo_cpe=74,
            estado="procesada",
            material="Maíz",
            origen="Rosario, Santa Fe",
            destino="Buenos Aires - Puerto",
            dominio="AB123CD",
            toneladas=28,
            cod_grano=19,
            nro_carta_porte="74000000001",
            nro_ctg="010112345678",
            con_pdf=True,
        ),
        # Procesada flete corto 274 — con PDF
        _carta_demo(
            id_="cpe-demo-2",
            despacho_id="d-3",
            viaje_id="#12331",
            tipo_cpe=274,
            estado="procesada",
            material="Soja",
            origen="Pergamino, Buenos Aires",
            destino="Rosario - Terminal",
            dominio="BC456CD",
            toneladas=30,
            cod_grano=23,
            nro_carta_porte="27400000002",
            nro_ctg="010122223333",
            sucursal=2,
            planta=220,
            con_pdf=True,
        ),
        # Segunda procesada 74 (viaje ya entregado)
        _carta_demo(
            id_="cpe-demo-3",
            despacho_id="d-3",
            viaje_id="#12330",
            tipo_cpe=74,
            estado="procesada",
            material="Soja",
            origen="Pergamino, Buenos Aires",
            destino="Rosario - Terminal",
            dominio="EF789GH",
            toneladas=32,
            cod_grano=23,
            nro_carta_porte="74000000003",
            nro_ctg="010133334444",
            planta=220,
            con_pdf=True,
        ),
        # Pendiente — lista para enviar a homologación
        _carta_demo(
            id_="cpe-demo-4",
            despacho_id="d-3",
            viaje_id="#12332",
            tipo_cpe=74,
            estado="pendiente",
            material="Soja",
            origen="Pergamino, Buenos Aires",
            destino="Puerto San Martín",
            dominio="AA123BB",
            toneladas=28.5,
            cod_grano=23,
            planta=310,
        ),
        # Error — falló armado/envío (reintentable)
        _carta_demo(
            id_="cpe-demo-5",
            despacho_id="d-1",
            viaje_id="#12342",
            tipo_cpe=74,
            estado="error",
            material="Maíz",
            origen="Rosario, Santa Fe",
            destino="Buenos Aires - Puerto",
            dominio="XY789ZA",
            toneladas=30,
            cod_grano=19,
            intentos=2,
            error_detalle=(
                "ARCA rechazó la solicitud: planta destino 150 no habilitada "
                "para el CUIT destinatario (demo)."
            ),
        ),
        # Anulada — ya no vigente
        _carta_demo(
            id_="cpe-demo-6",
            despacho_id="d-1",
            viaje_id="#12340",
            tipo_cpe=74,
            estado="anulada",
            material="Maíz",
            origen="Rosario, Santa Fe",
            destino="Buenos Aires - Puerto",
            dominio="DE456FG",
            toneladas=29,
            cod_grano=19,
            nro_carta_porte="74000000006",
            nro_ctg="010166667777",
            intentos=1,
            error_detalle="Anulada por error de carga (demo).",
            con_pdf=True,
        ),
        # Pendiente flete corto en campaña larga
        _carta_demo(
            id_="cpe-demo-7",
            despacho_id="d-8",
            viaje_id="#12390",
            tipo_cpe=274,
            estado="pendiente",
            material="Trigo",
            origen="Salta Capital, Salta",
            destino="Rosario - Terminal",
            dominio="EF789GH",
            toneladas=32,
            cod_grano=1,
            sucursal=2,
            planta=310,
        ),
        # Procesada 74 en viaje en curso
        _carta_demo(
            id_="cpe-demo-8",
            despacho_id="d-8",
            viaje_id="#12391",
            tipo_cpe=74,
            estado="procesada",
            material="Trigo",
            origen="Salta Capital, Salta",
            destino="Rosario - Terminal",
            dominio="AA123BB",
            toneladas=30.5,
            cod_grano=1,
            nro_carta_porte="74000000008",
            nro_ctg="010188889999",
            planta=310,
            con_pdf=True,
        ),
    ]


def _despacho_lista_espera_demo() -> Despacho:
    """Campaña activa con viajes sin chofer, pensada para probar asignar-por-lista."""
    return Despacho(
        id="d-lista-1",
        nombre="Demo Lista de Espera",
        productor_id="p-1",
        campo_id="c-1",
        origen="Pergamino, Buenos Aires",
        entrada_campo="Entrada Norte",
        material="Soja",
        administrador_id="a-1",
        vendedor_id="v-1",
        fecha_inicio=date(2026, 7, 28),
        fecha_llegada_estimada=date(2026, 8, 5),
        estado="activo",
        dador_viaje="Agro Demo SA",
        tarifa_por_tn=45000.0,
        cuando="ahora",
        observaciones="Viajes sin asignar para probar flota propia + lista FIFO",
        viajes=[
            Viaje(
                id="viaje-lista-1",
                destino="Rosario - Terminal",
                toneladas=28,
                estado="pendiente",
                progreso=0,
                observaciones="Probar: Asignar por lista",
            ),
            Viaje(
                id="viaje-lista-2",
                destino="Puerto San Martín",
                toneladas=30,
                estado="pendiente",
                progreso=0,
                observaciones="Segundo viaje sin chofer",
            ),
            Viaje(
                id="viaje-lista-3",
                destino="San Lorenzo - Puerto",
                toneladas=25,
                estado="pendiente",
                progreso=0,
                observaciones="Tercer viaje sin chofer",
            ),
        ],
    )


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

        # Catálogos (30 transportistas × 10 camiones/choferes; 30 productores × 10 campos/responsables).
        productores, transportistas, choferes_lista = _construir_catalogos_demo()
        sesion.add_all(productores)
        sesion.add_all(
            [Material(nombre=n, codigo_grano_afip=c) for n, c in _MATERIALES]
        )
        sesion.add_all(transportistas)
        await sesion.flush()
        sesion.add_all(choferes_lista)
        await sesion.flush()

        # Índice de choferes por nombre completo (viajes del mock referencian por nombre).
        choferes = {c.nombre: c for c in choferes_lista}
        camiones_por_transportista = {
            t.id: {c.dominio: c for c in t.camiones} for t in transportistas
        }

        # Despachos con sus viajes (los IDs y estados son los del mock).
        for (id_, nombre, productor, campo, origen, entrada, material, admin,
             vendedor, inicio, llegada, estado, viajes) in _DESPACHOS:
            extras_cpe = _extras_cpe_despacho(id_)
            sesion.add(
                Despacho(
                    id=id_, nombre=nombre, productor_id=productor, campo_id=campo,
                    origen=origen, entrada_campo=entrada, material=material,
                    administrador_id=admin, vendedor_id=vendedor,
                    fecha_inicio=inicio, fecha_llegada_estimada=llegada, estado=estado,
                    distancia_km=extras_cpe.get("distancia_km"),
                    tarifa_por_tn=extras_cpe.get("tarifa_por_tn"),
                    **{k: v for k, v in extras_cpe.items()
                       if k not in ("distancia_km", "tarifa_por_tn")},
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

        # Campaña extra + cola FIFO para probar lista de espera.
        sesion.add(_despacho_lista_espera_demo())
        sesion.add_all(_sembrar_lista_espera_demo(transportistas, choferes_lista))

        # Intenciones / CPE demo (pendiente, error, procesada con PDF, anulada, 74/274).
        sesion.add_all(_sembrar_cartas_porte_demo())

        # Casuística desde CPE PDF reales (Maíz→COFCO, Soja→LDC); nombres sim-* = ilegibles.
        from scripts.casuistica_cpe import (
            construir_cartas_casuistica,
            construir_catalogos_casuistica,
            construir_despachos_casuistica,
            texto_gap_analisis_md,
        )

        prod_cpe, trans_cpe, chof_cpe = construir_catalogos_casuistica()
        sesion.add_all(prod_cpe)
        sesion.add_all(trans_cpe)
        await sesion.flush()
        sesion.add_all(chof_cpe)
        await sesion.flush()
        sesion.add_all(construir_despachos_casuistica())
        sesion.add_all(construir_cartas_casuistica())

        gap_path = (
            Path(__file__).resolve().parents[1]
            / "postman"
            / "arca-wscpe"
            / "docs"
            / "gap-analisis-cpe-agro360.md"
        )
        gap_path.parent.mkdir(parents=True, exist_ok=True)
        gap_path.write_text(texto_gap_analisis_md(), encoding="utf-8")

        # Conversaciones vinculadas a los viajes de arriba.
        for (id_, chofer_id, despacho_id, viaje_id, origen, destino, no_leidos,
             mensajes) in _CONVERSACIONES:
            chofer = next(c for c in choferes_lista if c.id == chofer_id)
            flota = camiones_por_transportista.get(chofer.transportista_id or "", {})
            dominio_conv = next(iter(flota), "") if flota else ""
            if chofer.camion_id:
                camion_asignado = next(
                    (c for c in flota.values() if c.id == chofer.camion_id), None
                )
                if camion_asignado:
                    dominio_conv = camion_asignado.dominio
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

        # Cuenta corriente: fletes + movimientos manuales (t-1, t-2, t-3).
        sesion.add_all(_sembrar_cuenta_corriente_demo())

        await sesion.commit()


if __name__ == "__main__":
    import sys

    # Ejecución manual: crea las tablas y siembra.
    # Uso: python -m scripts.seed [--force]
    async def _main() -> None:
        forzar = "--force" in sys.argv
        if forzar:
            from app.core.database import Base, engine

            # Registrar metadata de todos los módulos antes de dropear.
            await crear_tablas()
            async with engine.begin() as conexion:
                await conexion.run_sync(Base.metadata.drop_all)
            print("Base vaciada (--force).")

        await crear_tablas()
        async with fabrica_sesiones() as sesion:
            ya_habia = await UsuarioDAO(sesion).contar() > 0
        await sembrar_datos_demo()
        if ya_habia and not forzar:
            print(
                "La base ya tenía datos; no se re-sembró. "
                "Usá: python -m scripts.seed --force"
            )
            return
        print(
            f"Seed listo. Login demo: {EMAIL_DEMO} / {PASSWORD_DEMO}\n"
            f"  · {CANTIDAD_TRANSPORTISTAS} transportistas "
            f"({CAMIONES_POR_TRANSPORTISTA} camiones + {CHOFERES_POR_TRANSPORTISTA} choferes c/u)\n"
            f"  · {CANTIDAD_PRODUCTORES} productores "
            f"({CAMPOS_POR_PRODUCTOR} campos + {RESPONSABLES_POR_PRODUCTOR} responsables c/u)\n"
            f"  · Lista de espera: 5 unidades en cola (t-2…)\n"
            f"  · Campaña 'Demo Lista de Espera' (d-lista-1) con 3 viajes sin asignar\n"
            f"  · Flota propia: Transportes del Plata (t-1)\n"
            f"  · Cartas de porte: intenciones demo (pendiente/error/procesada/anulada, 74 y 274)\n"
            f"  · Casuística CPE PDF: d-cpe-maiz-cofco + d-cpe-soja-ldc "
            f"(ver postman/arca-wscpe/docs/gap-analisis-cpe-agro360.md)"
        )

    asyncio.run(_main())