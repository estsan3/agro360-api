"""Capa SERVICE del módulo mensajería."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excepciones import RecursoNoEncontrado, ReglaDeNegocioViolada
from app.modulos.catalogos.contrato import CatalogosLocal, ContratoCatalogos
from app.modulos.mensajeria.bo import MensajeriaBO
from app.modulos.mensajeria.dao import MensajeriaDAO
from app.modulos.mensajeria.models import Conversacion, Mensaje
from app.modulos.mensajeria.schemas import (
    ConversacionResponse,
    ConversacionResumenResponse,
    EnviarMensajeRequest,
)


class MensajeriaService:
    """Casos de uso del chat admin ↔ chofer."""

    def __init__(
        self,
        sesion: AsyncSession,
        catalogos: ContratoCatalogos | None = None,
    ) -> None:
        self._sesion = sesion
        self._dao = MensajeriaDAO(sesion)
        self._bo = MensajeriaBO()
        self._catalogos = catalogos or CatalogosLocal(sesion)

    async def listar_conversaciones(self) -> list[ConversacionResumenResponse]:
        conversaciones = await self._dao.listar_conversaciones()
        return [ConversacionResumenResponse.model_validate(c) for c in conversaciones]

    async def obtener_conversacion(self, conversacion_id: str) -> ConversacionResponse:
        """Devuelve el hilo completo y marca los mensajes como leídos."""
        conversacion = await self._buscar_o_fallar(conversacion_id)
        # Abrir la conversación implica leer lo pendiente.
        conversacion.no_leidos = 0
        await self._sesion.commit()
        return ConversacionResponse.model_validate(conversacion)

    async def enviar_mensaje(
        self, conversacion_id: str, datos: EnviarMensajeRequest, autor: str = "admin"
    ) -> ConversacionResponse:
        """Agrega un mensaje al hilo (desde la web el autor siempre es admin)."""
        self._bo.validar_autor(autor)
        conversacion = await self._buscar_o_fallar(conversacion_id)

        await self._dao.agregar_mensaje(
            Mensaje(conversacion_id=conversacion.id, autor=autor, texto=datos.texto)
        )
        conversacion.no_leidos = self._bo.calcular_no_leidos(conversacion.no_leidos, autor)
        await self._sesion.commit()

        # Refrescamos para que la respuesta incluya el mensaje nuevo.
        await self._sesion.refresh(conversacion)
        return ConversacionResponse.model_validate(conversacion)

    async def iniciar_conversacion(self, chofer_id: str) -> ConversacionResponse:
        """Crea (o devuelve) la conversación con un chofer del catálogo."""
        existente = await self._dao.buscar_por_chofer(chofer_id)
        if existente is not None:
            return ConversacionResponse.model_validate(existente)

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
        return ConversacionResponse.model_validate(conversacion)

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

    async def _buscar_o_fallar(self, conversacion_id: str) -> Conversacion:
        conversacion = await self._dao.buscar_conversacion(conversacion_id)
        if conversacion is None:
            raise RecursoNoEncontrado("Conversación no encontrada")
        return conversacion
