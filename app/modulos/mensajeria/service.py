"""Capa SERVICE del módulo mensajería."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excepciones import RecursoNoEncontrado, ReglaDeNegocioViolada
from app.modulos.catalogos.contrato import CatalogosLocal, ContratoCatalogos
from app.modulos.despachos.contrato import ContratoDespachos, DespachosLocal
from app.modulos.mensajeria.bo import MensajeriaBO
from app.modulos.mensajeria.dao import MensajeriaDAO
from app.modulos.mensajeria.models import Conversacion, Mensaje
from app.modulos.mensajeria.schemas import (
    ConversacionResponse,
    EnviarMensajeRequest,
    MensajeResponse,
)


class MensajeriaService:
    """Casos de uso del chat admin ↔ chofer."""

    def __init__(
        self,
        sesion: AsyncSession,
        catalogos: ContratoCatalogos | None = None,
        despachos: ContratoDespachos | None = None,
    ) -> None:
        self._sesion = sesion
        self._dao = MensajeriaDAO(sesion)
        self._bo = MensajeriaBO()
        self._catalogos = catalogos or CatalogosLocal(sesion)
        # Contrato de despachos para reflejar el estado actual del viaje.
        self._despachos = despachos or DespachosLocal(sesion)

    async def listar_conversaciones(self) -> list[ConversacionResponse]:
        conversaciones = await self._dao.listar_conversaciones()
        return [await self._a_response(c) for c in conversaciones]

    async def obtener_conversacion(self, conversacion_id: str) -> ConversacionResponse:
        """Devuelve el hilo completo y marca los mensajes como leídos."""
        conversacion = await self._buscar_o_fallar(conversacion_id)
        # Abrir la conversación implica leer lo pendiente.
        conversacion.no_leidos = 0
        for mensaje in conversacion.mensajes:
            mensaje.leido = True
        await self._sesion.commit()
        return await self._a_response(conversacion)

    async def enviar_mensaje(
        self, conversacion_id: str, datos: EnviarMensajeRequest, autor: str = "admin"
    ) -> MensajeResponse:
        """Agrega un mensaje al hilo y lo devuelve (contrato del front)."""
        self._bo.validar_autor(autor)
        conversacion = await self._buscar_o_fallar(conversacion_id)

        mensaje = await self._dao.agregar_mensaje(
            Mensaje(
                conversacion_id=conversacion.id,
                autor=autor,
                texto=datos.texto,
                # Los mensajes del propio admin nacen leídos.
                leido=autor == "admin",
            )
        )
        conversacion.no_leidos = self._bo.calcular_no_leidos(conversacion.no_leidos, autor)
        await self._sesion.commit()
        return MensajeResponse.model_validate(mensaje)

    async def iniciar_conversacion(self, chofer_id: str) -> ConversacionResponse:
        """Crea (o devuelve) la conversación con un chofer del catálogo."""
        existente = await self._dao.buscar_por_chofer(chofer_id)
        if existente is not None:
            return await self._a_response(existente)

        chofer = await self._catalogos.obtener_chofer(chofer_id)
        if chofer is None:
            raise ReglaDeNegocioViolada(f"Chofer inexistente: {chofer_id}")

        conversacion = Conversacion(
            chofer_id=chofer.id,
            chofer_nombre=chofer.nombre,
            dominio=chofer.dominio,
        )
        await self._dao.guardar_conversacion(conversacion)
        await self._sesion.commit()
        return await self._a_response(conversacion)

    async def notificar_evento_viaje(self, chofer_id: str | None, texto: str) -> None:
        """Inserta un mensaje de sistema en el hilo del chofer (si existe).

        Lo usan los manejadores de eventos de dominio (ver `eventos.py`).
        """
        if chofer_id is None:
            return
        conversacion = await self._dao.buscar_por_chofer(chofer_id)
        if conversacion is None:
            return
        await self._dao.agregar_mensaje(
            Mensaje(conversacion_id=conversacion.id, autor="sistema", texto=texto)
        )
        conversacion.no_leidos = self._bo.calcular_no_leidos(
            conversacion.no_leidos, "sistema"
        )
        await self._sesion.commit()

    async def vincular_viaje(
        self, chofer_id: str, despacho_id: str, viaje_id: str, origen: str, destino: str
    ) -> None:
        """Asocia la conversación del chofer a su viaje actual (vía eventos)."""
        conversacion = await self._dao.buscar_por_chofer(chofer_id)
        if conversacion is None:
            return
        conversacion.despacho_id = despacho_id
        conversacion.viaje_id = viaje_id
        conversacion.origen = origen
        conversacion.destino = destino
        await self._sesion.commit()

    # ------------------------------- Privados -------------------------------

    async def _buscar_o_fallar(self, conversacion_id: str) -> Conversacion:
        conversacion = await self._dao.buscar_conversacion(conversacion_id)
        if conversacion is None:
            raise RecursoNoEncontrado("Conversación no encontrada")
        return conversacion

    async def _a_response(self, conversacion: Conversacion) -> ConversacionResponse:
        """Compone la respuesta con el estado actual del viaje asociado."""
        estado_viaje = "pendiente"
        if conversacion.despacho_id and conversacion.viaje_id:
            viaje = await self._despachos.obtener_viaje(
                conversacion.despacho_id, conversacion.viaje_id
            )
            if viaje is not None and viaje.estado != "borrador":
                estado_viaje = viaje.estado

        return ConversacionResponse(
            id=conversacion.id,
            chofer=conversacion.chofer_nombre,
            dominio=conversacion.dominio,
            viaje_id=conversacion.viaje_id or "",
            origen=conversacion.origen,
            destino=conversacion.destino,
            estado_viaje=estado_viaje,  # type: ignore[arg-type]
            no_leidos=conversacion.no_leidos,
            mensajes=[MensajeResponse.model_validate(m) for m in conversacion.mensajes],
        )
