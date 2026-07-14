"""Capa SERVICE del módulo despachos: casos de uso de campañas y viajes.

Este service es un buen ejemplo de las dos vías de comunicación entre
módulos:
- Valida referencias contra catálogos vía su CONTRATO (sincrónico).
- Publica EVENTOS de dominio (viaje completado, campaña activada) que
  otros módulos escuchan sin acoplarse.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.eventos import EventoDominio, bus_eventos
from app.core.excepciones import RecursoNoEncontrado, ReglaDeNegocioViolada
from app.modulos.catalogos.contrato import CatalogosLocal, ContratoCatalogos
from app.modulos.despachos.bo import DespachoBO
from app.modulos.despachos.dao import DespachoDAO
from app.modulos.despachos.models import Despacho, Viaje
from app.modulos.despachos.schemas import (
    ActualizarViajeRequest,
    CrearDespachoRequest,
    CrearViajeRequest,
    DespachoResponse,
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
        # Validación de referencias contra el contrato de catálogos.
        if not await self._catalogos.existe_productor_con_campo(
            datos.productor_id, datos.campo_id
        ):
            raise ReglaDeNegocioViolada(
                "El campo indicado no existe o no pertenece a ese productor"
            )
        if not await self._catalogos.existe_material(datos.material):
            raise ReglaDeNegocioViolada(f"Material desconocido: {datos.material}")

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
            fecha_llegada_estimada=datos.fecha_llegada_estimada,
        )
        self._bo.validar_fechas(despacho)

        # Alta de los viajes iniciales de la campaña.
        for datos_viaje in datos.viajes:
            despacho.viajes.append(await self._construir_viaje(datos_viaje))

        if datos.activar:
            self._bo.validar_activacion(despacho)
            despacho.estado = "activo"

        await self._dao.guardar(despacho)
        await self._sesion.commit()
        # Carga explícita de la relación: si la campaña nació sin viajes,
        # Pydantic dispararía un lazy load fuera del contexto async.
        await self._sesion.refresh(despacho, attribute_names=["viajes"])

        if despacho.estado == "activo":
            await self._publicar_activacion(despacho)
        return DespachoResponse.model_validate(despacho)

    async def activar(self, despacho_id: str) -> DespachoResponse:
        """Pasa una campaña de borrador a activa ("Enviar" en el front)."""
        despacho = await self._buscar_o_fallar(despacho_id)
        self._bo.validar_activacion(despacho)
        despacho.estado = "activo"
        await self._sesion.commit()
        await self._publicar_activacion(despacho)
        return DespachoResponse.model_validate(despacho)

    async def eliminar(self, despacho_id: str) -> None:
        """Elimina una campaña en borrador."""
        despacho = await self._buscar_o_fallar(despacho_id)
        self._bo.validar_eliminacion(despacho)
        await self._dao.eliminar(despacho)
        await self._sesion.commit()

    # -------------------------------- Viajes --------------------------------

    async def agregar_viaje(
        self, despacho_id: str, datos: CrearViajeRequest
    ) -> DespachoResponse:
        despacho = await self._buscar_o_fallar(despacho_id)
        despacho.viajes.append(await self._construir_viaje(datos))
        await self._sesion.commit()
        return DespachoResponse.model_validate(despacho)

    async def actualizar_viaje(
        self, despacho_id: str, viaje_id: str, datos: ActualizarViajeRequest
    ) -> DespachoResponse:
        """Actualización parcial: asignar chofer, cambiar estado o progreso."""
        despacho = await self._buscar_o_fallar(despacho_id)
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

    # ------------------------------- Privados -------------------------------

    async def _buscar_o_fallar(self, despacho_id: str) -> Despacho:
        despacho = await self._dao.buscar_por_id(despacho_id)
        if despacho is None:
            raise RecursoNoEncontrado("Campaña de despacho no encontrada")
        return despacho

    async def _construir_viaje(self, datos: CrearViajeRequest) -> Viaje:
        """Crea la entidad Viaje resolviendo el chofer contra catálogos."""
        viaje = Viaje(
            destino=datos.destino,
            toneladas=datos.toneladas,
            observaciones=datos.observaciones,
        )
        if datos.chofer_id:
            await self._asignar_chofer(viaje, datos.chofer_id)
        return viaje

    async def _asignar_chofer(self, viaje: Viaje, chofer_id: str) -> None:
        """Asigna un chofer copiando nombre y dominio (desnormalización)."""
        chofer = await self._catalogos.obtener_chofer(chofer_id)
        if chofer is None:
            raise ReglaDeNegocioViolada(f"Chofer inexistente: {chofer_id}")
        viaje.chofer_id = chofer.id
        viaje.chofer_nombre = chofer.nombre
        viaje.dominio = chofer.dominio

    async def _publicar_activacion(self, despacho: Despacho) -> None:
        await bus_eventos.publicar(
            EventoDominio(
                nombre="despachos.despacho.activado",
                datos={"despacho_id": despacho.id, "nombre": despacho.nombre},
            )
        )
