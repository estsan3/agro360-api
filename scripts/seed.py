"""Seed de datos de demo, espejo del mock del front Angular (mock-data.ts).

Se ejecuta automáticamente al iniciar la API en dev (si la base está
vacía) o manualmente con:
    poetry run python -m scripts.seed
"""

import asyncio
from datetime import date

from app.core.database import crear_tablas, fabrica_sesiones
from app.core.seguridad import hashear_password
from app.modulos.auth.dao import UsuarioDAO
from app.modulos.auth.models import Usuario
from app.modulos.catalogos.models import Campo, Chofer, Material, Productor
from app.modulos.despachos.models import Despacho, Viaje
from app.modulos.mensajeria.models import Conversacion, Mensaje

# Credenciales de demo (las mismas que el mock del front).
EMAIL_DEMO = "admin@agro360.com"
PASSWORD_DEMO = "demo12345"


async def sembrar_datos_demo() -> None:
    """Inserta usuarios, catálogos, campañas y conversaciones de demo."""
    async with fabrica_sesiones() as sesion:
        # Si ya hay usuarios, la base no está vacía: no se re-siembra.
        if await UsuarioDAO(sesion).contar() > 0:
            return

        # ------------------------------ Usuarios -------------------------------
        sesion.add_all(
            [
                Usuario(
                    nombre="María González",
                    dni="27888999",
                    email=EMAIL_DEMO,
                    password_hash=hashear_password(PASSWORD_DEMO),
                    rol="administrador",
                ),
                Usuario(
                    nombre="Juan Pérez",
                    dni="12345678",
                    email="juan.perez@email.com",
                    password_hash=hashear_password(PASSWORD_DEMO),
                    rol="vendedor",
                ),
            ]
        )

        # ------------------------------ Catálogos ------------------------------
        productor_agro_sa = Productor(
            nombre="Agro SA",
            campos=[Campo(nombre="Campo Norte"), Campo(nombre="Campo Los Nogales")],
        )
        productor_campo_verde = Productor(
            nombre="Campo Verde SRL",
            campos=[Campo(nombre="Campo San Pedro")],
        )
        sesion.add_all([productor_agro_sa, productor_campo_verde])

        sesion.add_all(
            [
                # Códigos de grano según tabla de ARCA/AFIP (consultarTiposGrano).
                Material(nombre="Soja", codigo_grano_afip=23),
                Material(nombre="Maíz", codigo_grano_afip=2),
                Material(nombre="Girasol", codigo_grano_afip=27),
                Material(nombre="Trigo", codigo_grano_afip=1),
            ]
        )

        chofer_carlos = Chofer(nombre="Carlos Ruiz", dominio="AA123BB")
        chofer_miguel = Chofer(nombre="Miguel Torres", dominio="EF789GH")
        chofer_roberto = Chofer(nombre="Roberto Gómez", dominio="BC456CD")
        chofer_pedro = Chofer(nombre="Pedro Ramírez", dominio="XY789ZA")
        sesion.add_all([chofer_carlos, chofer_miguel, chofer_roberto, chofer_pedro])

        # Flush para que las entidades tengan ID asignado antes de referenciarlas.
        await sesion.flush()

        # ------------------------------ Despachos ------------------------------
        campo_norte = productor_agro_sa.campos[0]
        campania_maiz = Despacho(
            nombre="Campaña Maíz 2026",
            productor_id=productor_agro_sa.id,
            campo_id=campo_norte.id,
            origen="Rosario, Santa Fe",
            entrada_campo="Entrada Norte (Lat: -32.9442, Lng: -60.6505)",
            material="Maíz",
            administrador_id="a-1",
            vendedor_id="v-1",
            fecha_inicio=date(2026, 7, 1),
            fecha_llegada_estimada=date(2026, 7, 20),
            estado="activo",
            viajes=[
                Viaje(
                    chofer_id=chofer_carlos.id,
                    chofer_nombre=chofer_carlos.nombre,
                    dominio=chofer_carlos.dominio,
                    destino="Buenos Aires - Puerto",
                    toneladas=28,
                    estado="en_viaje",
                    progreso=65,
                    observaciones="Viaje normal",
                ),
                Viaje(
                    destino="Buenos Aires - Puerto",
                    toneladas=28,
                    observaciones="Pendiente asignación",
                ),
                Viaje(
                    chofer_id=chofer_pedro.id,
                    chofer_nombre=chofer_pedro.nombre,
                    dominio=chofer_pedro.dominio,
                    destino="Buenos Aires - Puerto",
                    toneladas=30,
                    estado="retrasado",
                    progreso=42,
                    observaciones="Desperfecto técnico en ruta",
                ),
            ],
        )
        campania_borrador = Despacho(
            nombre="Campaña Maíz Primavera",
            productor_id=productor_campo_verde.id,
            campo_id=productor_campo_verde.campos[0].id,
            origen="Campo Verde SRL",
            entrada_campo="Campo San Pedro",
            material="Maíz",
            administrador_id="a-1",
            vendedor_id="v-2",
            fecha_inicio=date(2026, 9, 15),
            fecha_llegada_estimada=date(2026, 10, 1),
            estado="borrador",
        )
        sesion.add_all([campania_maiz, campania_borrador])

        # ----------------------------- Mensajería ------------------------------
        conversacion = Conversacion(
            chofer_id=chofer_carlos.id,
            chofer_nombre=chofer_carlos.nombre,
            dominio=chofer_carlos.dominio,
            no_leidos=1,
        )
        sesion.add(conversacion)
        await sesion.flush()
        sesion.add_all(
            [
                Mensaje(
                    conversacion_id=conversacion.id,
                    autor="admin",
                    texto="Hola Carlos, ¿cómo va el viaje?",
                ),
                Mensaje(
                    conversacion_id=conversacion.id,
                    autor="chofer",
                    texto="Todo bien, la carga va segura. Llego al puerto en 2 horas.",
                ),
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
