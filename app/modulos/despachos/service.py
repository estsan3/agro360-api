"""Capa SERVICE del módulo despachos: casos de uso de campañas y viajes.

Este service es un buen ejemplo de las dos vías de comunicación entre
módulos:
- Valida referencias contra catálogos vía su CONTRATO (sincrónico).
- Publica EVENTOS de dominio (viaje completado, campaña activada) que
  otros módulos escuchan sin acoplarse.
"""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.eventos import EventoDominio, bus_eventos
from app.core.excepciones import RecursoNoEncontrado, ReglaDeNegocioViolada
from app.modulos.catalogos.contrato import CatalogosLocal, ContratoCatalogos
from app.modulos.despachos.bo import DespachoBO
from app.modulos.despachos.dao import DespachoDAO
from app.modulos.despachos.models import Despacho, TarifaNacional, Viaje
from app.modulos.despachos.schemas import (
    ActualizarMetadatosDespachoRequest,
    ActualizarViajeRequest,
    BuscarTransportistasRequest,
    CrearDespachoRequest,
    CrearViajeRequest,
    DespachoResponse,
    DuplicarDespachoRequest,
    ResolverTarifaResponse,
    TarifaNacionalItem,
    TarifaNacionalResponse,
)


class DespachosService:
    """Casos de uso de campañas de despacho."""

    def __init__(
        self,
        sesion: AsyncSession,
        catalogos: ContratoCatalogos | None = None,
    ) -> None:
        self._sesion = sesion
        self._dao = DespachoDAO(sesion)
        self._bo = DespachoBO()
        # El contrato es inyectable: en tests se pasa un fake; cuando
        # catálogos sea microservicio, se pasa el cliente HTTP.
        self._catalogos = catalogos or CatalogosLocal(sesion)

    # ------------------------------- Campañas -------------------------------

    async def listar(self, estado: str | None = None) -> list[DespachoResponse]:
        despachos = await self._dao.listar(estado)
        return [DespachoResponse.model_validate(d) for d in despachos]

    async def obtener(self, despacho_id: str) -> DespachoResponse:
        despacho = await self._buscar_o_fallar(despacho_id)
        return DespachoResponse.model_validate(despacho)

    async def crear(self, datos: CrearDespachoRequest) -> DespachoResponse:
        """Crea una campaña (borrador o directamente activa)."""
        await self._validar_referencias(datos)

        fecha_llegada = self._resolver_fecha_llegada(
            datos.fecha_inicio, datos.fecha_llegada_estimada
        )
        despacho = Despacho(
            nombre=datos.nombre,
            productor_id=datos.productor_id,
            campo_id=datos.campo_id,
            origen=datos.origen,
            entrada_campo=datos.entrada_campo,
            material=datos.material,
            administrador_id=datos.administrador_id,
            vendedor_id=datos.vendedor_id,
            fecha_inicio=datos.fecha_inicio,
            fecha_llegada_estimada=fecha_llegada,
        )
        await self._aplicar_campos_comerciales(despacho, datos)
        self._bo.validar_fechas(despacho)

        # Alta de los viajes iniciales: nacen en borrador junto con la campaña.
        exigir_chofer = datos.estado == "activo"
        for datos_viaje in datos.viajes:
            despacho.viajes.append(
                await self._construir_viaje(
                    datos_viaje, estado="borrador", exigir_chofer=exigir_chofer
                )
            )

        if datos.estado == "activo":
            self._bo.activar(despacho)

        await self._dao.guardar(despacho)
        await self._sesion.commit()
        # Carga explícita de la relación: si la campaña nació sin viajes,
        # Pydantic dispararía un lazy load fuera del contexto async.
        await self._sesion.refresh(despacho, attribute_names=["viajes"])

        if despacho.estado == "activo":
            await self._publicar_activacion(despacho)
        return DespachoResponse.model_validate(despacho)

    async def actualizar(
        self, despacho_id: str, datos: CrearDespachoRequest
    ) -> DespachoResponse:
        """Edición de una campaña en borrador (el front reenvía el formulario).

        Los viajes se reemplazan por los del payload (en borrador todos los
        viajes son editables). Con `estado="activo"` además se envía.
        """
        despacho = await self._buscar_o_fallar(despacho_id)
        self._bo.validar_edicion(despacho)
        await self._validar_referencias(datos)

        despacho.nombre = datos.nombre
        despacho.productor_id = datos.productor_id
        despacho.campo_id = datos.campo_id
        despacho.origen = datos.origen
        despacho.entrada_campo = datos.entrada_campo
        despacho.material = datos.material
        despacho.administrador_id = datos.administrador_id
        despacho.vendedor_id = datos.vendedor_id
        despacho.fecha_inicio = datos.fecha_inicio
        despacho.fecha_llegada_estimada = self._resolver_fecha_llegada(
            datos.fecha_inicio, datos.fecha_llegada_estimada
        )
        await self._aplicar_campos_comerciales(despacho, datos)
        self._bo.validar_fechas(despacho)

        despacho.viajes.clear()
        exigir_chofer = datos.estado == "activo"
        for datos_viaje in datos.viajes:
            despacho.viajes.append(
                await self._construir_viaje(
                    datos_viaje, estado="borrador", exigir_chofer=exigir_chofer
                )
            )

        if datos.estado == "activo":
            self._bo.activar(despacho)

        await self._sesion.commit()
        await self._sesion.refresh(despacho, attribute_names=["viajes"])

        if despacho.estado == "activo":
            await self._publicar_activacion(despacho)
        return DespachoResponse.model_validate(despacho)

    async def activar(self, despacho_id: str) -> DespachoResponse:
        """Pasa una campaña de borrador a activa ("Enviar" en el front)."""
        despacho = await self._buscar_o_fallar(despacho_id)
        self._bo.activar(despacho)
        await self._sesion.commit()
        await self._publicar_activacion(despacho)
        return DespachoResponse.model_validate(despacho)

    async def eliminar(self, despacho_id: str) -> None:
        """Elimina una campaña en borrador."""
        despacho = await self._buscar_o_fallar(despacho_id)
        self._bo.validar_eliminacion(despacho)
        await self._dao.eliminar(despacho)
        await self._sesion.commit()

    async def cerrar(self, despacho_id: str) -> DespachoResponse:
        """Cierra una campaña activa cuando todos sus viajes están completados."""
        despacho = await self._buscar_o_fallar(despacho_id)
        self._bo.cerrar(despacho)
        await self._sesion.commit()
        await bus_eventos.publicar(
            EventoDominio(
                nombre="despachos.despacho.cerrado",
                datos={"despacho_id": despacho.id, "nombre": despacho.nombre},
            )
        )
        return DespachoResponse.model_validate(despacho)

    async def actualizar_metadatos(
        self, despacho_id: str, datos: ActualizarMetadatosDespachoRequest
    ) -> DespachoResponse:
        """Ajusta fechas y observaciones de una campaña activa."""
        despacho = await self._buscar_o_fallar(despacho_id)
        self._bo.validar_edicion_metadatos(despacho)
        despacho.fecha_llegada_estimada = datos.fecha_llegada_estimada
        despacho.observaciones = datos.observaciones
        self._bo.validar_fechas(despacho)
        await self._sesion.commit()
        return DespachoResponse.model_validate(despacho)

    async def duplicar(
        self, despacho_id: str, datos: DuplicarDespachoRequest | None = None
    ) -> DespachoResponse:
        """Crea un borrador copia de la campaña (mismos datos y viajes en borrador)."""
        original = await self._buscar_o_fallar(despacho_id)
        nombre = (
            datos.nombre.strip()
            if datos and datos.nombre
            else f"{original.nombre} (copia)"
        )
        copia = Despacho(
            nombre=nombre,
            productor_id=original.productor_id,
            campo_id=original.campo_id,
            origen=original.origen,
            entrada_campo=original.entrada_campo,
            material=original.material,
            administrador_id=original.administrador_id,
            vendedor_id=original.vendedor_id,
            fecha_inicio=original.fecha_inicio,
            fecha_llegada_estimada=original.fecha_llegada_estimada,
            observaciones=original.observaciones,
            estado="borrador",
            dador_viaje=original.dador_viaje,
            tarifa_llena=original.tarifa_llena,
            tarifa_por_tn=original.tarifa_por_tn,
            distancia_km=original.distancia_km,
            cuando=original.cuando,
            cuando_fecha=original.cuando_fecha,
        )
        for viaje in original.viajes:
            copia.viajes.append(
                Viaje(
                    chofer_id=viaje.chofer_id,
                    chofer_nombre=viaje.chofer_nombre,
                    dominio=viaje.dominio,
                    destino=viaje.destino,
                    toneladas=viaje.toneladas,
                    observaciones=viaje.observaciones,
                    estado="borrador",
                    progreso=0,
                )
            )
        await self._dao.guardar(copia)
        await self._sesion.commit()
        await self._sesion.refresh(copia, attribute_names=["viajes"])
        return DespachoResponse.model_validate(copia)

    # -------------------------------- Viajes --------------------------------

    async def agregar_viaje(
        self, despacho_id: str, datos: CrearViajeRequest
    ) -> DespachoResponse:
        despacho = await self._buscar_o_fallar(despacho_id)
        self._bo.validar_campaña_operable(despacho)
        # En campaña borrador el viaje nace borrador; en activa, pendiente.
        estado = "borrador" if despacho.estado == "borrador" else "pendiente"
        despacho.viajes.append(await self._construir_viaje_agregar(datos, estado=estado))
        await self._sesion.commit()
        return DespachoResponse.model_validate(despacho)

    async def iniciar_viaje(self, despacho_id: str, viaje_id: str) -> DespachoResponse:
        """El viaje sale a la ruta: pasa a en_viaje."""
        despacho = await self._buscar_o_fallar(despacho_id)
        self._bo.validar_campaña_operable(despacho)
        viaje = await self._buscar_viaje_o_fallar(despacho_id, viaje_id)
        self._bo.validar_inicio_viaje(viaje)
        self._bo.aplicar_estado_viaje(viaje, "en_viaje")
        await self._sesion.commit()

        # Mensajería escucha este evento para abrir/vincular el chat del chofer.
        await bus_eventos.publicar(
            EventoDominio(
                nombre="despachos.viaje.iniciado",
                datos={
                    "despacho_id": despacho.id,
                    "viaje_id": viaje.id,
                    "chofer_id": viaje.chofer_id,
                    "origen": despacho.origen,
                    "destino": viaje.destino,
                },
            )
        )
        return DespachoResponse.model_validate(despacho)

    async def duplicar_viaje(self, despacho_id: str, viaje_id: str) -> DespachoResponse:
        """Copia un viaje (mismo chofer/destino/toneladas) listo para salir."""
        despacho = await self._buscar_o_fallar(despacho_id)
        self._bo.validar_campaña_operable(despacho)
        original = await self._buscar_viaje_o_fallar(despacho_id, viaje_id)

        copia = Viaje(
            chofer_id=original.chofer_id,
            chofer_nombre=original.chofer_nombre,
            dominio=original.dominio,
            destino=original.destino,
            toneladas=original.toneladas,
            observaciones=original.observaciones,
            estado="borrador" if despacho.estado == "borrador" else "pendiente",
        )
        despacho.viajes.append(copia)
        await self._sesion.commit()
        return DespachoResponse.model_validate(despacho)

    async def eliminar_viaje(self, despacho_id: str, viaje_id: str) -> DespachoResponse:
        """Elimina un viaje que todavía no salió a la ruta."""
        despacho = await self._buscar_o_fallar(despacho_id)
        self._bo.validar_campaña_operable(despacho)
        viaje = await self._buscar_viaje_o_fallar(despacho_id, viaje_id)
        self._bo.validar_eliminacion_viaje(viaje)
        despacho.viajes.remove(viaje)
        await self._sesion.commit()
        return DespachoResponse.model_validate(despacho)

    async def actualizar_viaje(
        self, despacho_id: str, viaje_id: str, datos: ActualizarViajeRequest
    ) -> DespachoResponse:
        """Actualización parcial: asignar chofer, cambiar estado o progreso."""
        despacho = await self._buscar_o_fallar(despacho_id)
        self._bo.validar_campaña_operable(despacho)
        viaje = await self._dao.buscar_viaje(despacho_id, viaje_id)
        if viaje is None:
            raise RecursoNoEncontrado("Viaje no encontrado en esa campaña")

        if datos.chofer_id is not None:
            await self._asignar_chofer(viaje, datos.chofer_id)
        if datos.observaciones is not None:
            viaje.observaciones = datos.observaciones
        if datos.progreso is not None:
            viaje.progreso = datos.progreso

        estado_cambio_a_completado = False
        if datos.estado is not None and datos.estado != viaje.estado:
            self._bo.aplicar_estado_viaje(viaje, datos.estado)
            estado_cambio_a_completado = datos.estado == "completado"

        await self._sesion.commit()

        # Evento de dominio: mensajería/notificaciones lo escuchan sin acople.
        if estado_cambio_a_completado:
            await bus_eventos.publicar(
                EventoDominio(
                    nombre="despachos.viaje.completado",
                    datos={"despacho_id": despacho.id, "viaje_id": viaje.id},
                )
            )
        elif datos.estado == "retrasado":
            await bus_eventos.publicar(
                EventoDominio(
                    nombre="despachos.viaje.retrasado",
                    datos={"despacho_id": despacho.id, "viaje_id": viaje.id},
                )
            )
        return DespachoResponse.model_validate(despacho)

    # ----------------------- Tarifas / búsqueda ---------------------------

    async def listar_tarifas_nacionales(self) -> list[TarifaNacionalResponse]:
        filas = await self._dao.listar_tarifas_nacionales()
        if not filas:
            await self._sembrar_tarifas_default()
            filas = await self._dao.listar_tarifas_nacionales()
        return [TarifaNacionalResponse.model_validate(f) for f in filas]

    async def guardar_tarifas_nacionales(
        self, tramos: list[TarifaNacionalItem]
    ) -> list[TarifaNacionalResponse]:
        entidades = [
            TarifaNacional(
                km_desde=t.km_desde,
                km_hasta=t.km_hasta,
                precio_por_tn=t.precio_por_tn,
                vigencia=t.vigencia,
            )
            for t in tramos
        ]
        filas = await self._dao.reemplazar_tarifas_nacionales(entidades)
        await self._sesion.commit()
        return [TarifaNacionalResponse.model_validate(f) for f in filas]

    async def resolver_tarifa(self, distancia_km: float) -> ResolverTarifaResponse:
        precio, vigencia = await self._precio_tarifa_nacional(distancia_km)
        return ResolverTarifaResponse(
            distancia_km=distancia_km, precio_por_tn=precio, vigencia=vigencia
        )

    async def buscar_transportistas(
        self,
        despacho_id: str,
        datos: BuscarTransportistasRequest | None = None,
    ) -> DespachoResponse:
        """Crea/marca viajes en búsqueda y publica oferta a transportistas."""
        despacho = await self._buscar_o_fallar(despacho_id)
        if despacho.tarifa_llena and despacho.distancia_km:
            precio, _ = await self._precio_tarifa_nacional(despacho.distancia_km)
            despacho.tarifa_por_tn = precio
        self._bo.validar_busqueda_transportistas(despacho)

        candidatos = [
            v
            for v in despacho.viajes
            if v.estado in {"borrador", "en_busqueda_transportistas"}
        ]
        if not candidatos:
            # La tabla de viajes no es prerequisito: se genera el viaje de oferta.
            req = datos or BuscarTransportistasRequest()
            destino, toneladas = self._bo.validar_datos_viaje_busqueda(
                req.destino, req.toneladas
            )
            nuevo = Viaje(
                destino=destino,
                toneladas=toneladas,
                estado="en_busqueda_transportistas",
            )
            despacho.viajes.append(nuevo)
            candidatos = [nuevo]
        else:
            for viaje in candidatos:
                viaje.estado = "en_busqueda_transportistas"

        await self._sesion.commit()
        await self._sesion.refresh(despacho, attribute_names=["viajes"])

        cuando_txt = self._bo.formatear_cuando(
            despacho.cuando, despacho.cuando_fecha, date.today()
        )
        for viaje in despacho.viajes:
            if viaje.estado != "en_busqueda_transportistas":
                continue
            texto = self._bo.armar_mensaje_oferta(
                material=despacho.material,
                cuando_texto=cuando_txt,
                origen=despacho.origen,
                destino=viaje.destino,
                tarifa_por_tn=float(despacho.tarifa_por_tn or 0),
                tarifa_llena=despacho.tarifa_llena,
                dador_viaje=despacho.dador_viaje,
                toneladas=viaje.toneladas,
            )
            await bus_eventos.publicar(
                EventoDominio(
                    nombre="despachos.viaje.en_busqueda",
                    datos={
                        "despacho_id": despacho.id,
                        "viaje_id": viaje.id,
                        "origen": despacho.origen,
                        "destino": viaje.destino,
                        "mensaje": texto,
                    },
                )
            )
        return DespachoResponse.model_validate(despacho)

    # ------------------------------- Privados -------------------------------

    async def _buscar_o_fallar(self, despacho_id: str) -> Despacho:
        despacho = await self._dao.buscar_por_id(despacho_id)
        if despacho is None:
            raise RecursoNoEncontrado("Campaña de despacho no encontrada")
        return despacho

    async def _buscar_viaje_o_fallar(self, despacho_id: str, viaje_id: str) -> Viaje:
        viaje = await self._dao.buscar_viaje(despacho_id, viaje_id)
        if viaje is None:
            raise RecursoNoEncontrado("Viaje no encontrado en esa campaña")
        return viaje

    async def _validar_referencias(self, datos: CrearDespachoRequest) -> None:
        """Valida productor/campo/material contra el contrato de catálogos."""
        if not await self._catalogos.existe_productor_con_campo(
            datos.productor_id, datos.campo_id
        ):
            raise ReglaDeNegocioViolada(
                "El campo indicado no existe o no pertenece a ese productor"
            )
        if not await self._catalogos.existe_material(datos.material):
            raise ReglaDeNegocioViolada(f"Material desconocido: {datos.material}")

    @staticmethod
    def _resolver_fecha_llegada(fecha_inicio, fecha_llegada):
        """Si el front no informa llegada estimada, usa la fecha de inicio."""
        return fecha_llegada if fecha_llegada is not None else fecha_inicio

    async def _construir_viaje(
        self,
        datos: CrearViajeRequest,
        estado: str = "pendiente",
        *,
        exigir_chofer: bool = True,
    ) -> Viaje:
        """Crea la entidad Viaje resolviendo el chofer contra catálogos."""
        if exigir_chofer and not datos.chofer_id:
            raise ReglaDeNegocioViolada("Debe seleccionar un chofer")

        viaje = Viaje(
            destino=datos.destino,
            toneladas=datos.toneladas,
            observaciones=datos.observaciones,
            estado=estado,
        )
        if datos.chofer_id:
            await self._asignar_chofer(viaje, datos.chofer_id)
        if datos.dominio:
            viaje.dominio = datos.dominio.strip().upper()
        return viaje

    async def _construir_viaje_agregar(
        self, datos: CrearViajeRequest, estado: str = "pendiente"
    ) -> Viaje:
        """Alta de viaje en campaña existente (chofer opcional)."""
        return await self._construir_viaje(datos, estado=estado, exigir_chofer=False)

    async def _asignar_chofer(self, viaje: Viaje, chofer_id: str) -> None:
        """Asigna un chofer copiando nombre y dominio (desnormalización)."""
        chofer = await self._catalogos.obtener_chofer(chofer_id)
        if chofer is None:
            raise ReglaDeNegocioViolada(f"Chofer inexistente: {chofer_id}")
        viaje.chofer_id = chofer.id
        viaje.chofer_nombre = chofer.nombre
        viaje.dominio = chofer.dominio

    async def _aplicar_campos_comerciales(
        self, despacho: Despacho, datos: CrearDespachoRequest
    ) -> None:
        despacho.dador_viaje = (datos.dador_viaje or "").strip()
        despacho.tarifa_llena = datos.tarifa_llena
        despacho.distancia_km = datos.distancia_km
        despacho.cuando = datos.cuando
        despacho.cuando_fecha = datos.cuando_fecha if datos.cuando == "fecha" else None
        if datos.tarifa_llena:
            if datos.distancia_km is None:
                raise ReglaDeNegocioViolada("Tarifa llena requiere distancia en km")
            precio, _ = await self._precio_tarifa_nacional(datos.distancia_km)
            despacho.tarifa_por_tn = precio
        else:
            despacho.tarifa_por_tn = datos.tarifa_por_tn

    async def _precio_tarifa_nacional(self, distancia_km: float) -> tuple[float, str]:
        filas = await self._dao.listar_tarifas_nacionales()
        if not filas:
            await self._sembrar_tarifas_default()
            filas = await self._dao.listar_tarifas_nacionales()
            await self._sesion.commit()
        tramos = [(f.km_desde, f.km_hasta, f.precio_por_tn) for f in filas]
        precio = self._bo.resolver_tarifa_por_km(distancia_km, tramos)
        vigencia = filas[0].vigencia if filas else "2026-03"
        for f in filas:
            if f.km_desde <= distancia_km <= f.km_hasta:
                vigencia = f.vigencia
                break
        return precio, vigencia

    async def _sembrar_tarifas_default(self) -> None:
        """Tramos orientativos tipo FADEEAC (cereales, vig. marzo 2026)."""
        # Fuente: FADEEAC tarifa orientativa cereales/oleaginosas (valores demo).
        defaults = [
            (0, 50, 12010.0),
            (51, 100, 25400.0),
            (101, 150, 33500.0),
            (151, 200, 40000.0),
            (201, 250, 49240.0),
            (251, 300, 56000.0),
            (301, 400, 65000.0),
            (401, 500, 76000.0),
            (501, 700, 92000.0),
            (701, 1000, 112000.0),
            (1001, 1500, 146360.0),
        ]
        await self._dao.reemplazar_tarifas_nacionales(
            [
                TarifaNacional(
                    km_desde=a,
                    km_hasta=b,
                    precio_por_tn=p,
                    vigencia="2026-03",
                )
                for a, b, p in defaults
            ]
        )

    async def _publicar_activacion(self, despacho: Despacho) -> None:
        await bus_eventos.publicar(
            EventoDominio(
                nombre="despachos.despacho.activado",
                datos={"despacho_id": despacho.id, "nombre": despacho.nombre},
            )
        )
