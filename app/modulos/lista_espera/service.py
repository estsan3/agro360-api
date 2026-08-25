"""Capa SERVICE del módulo lista de espera."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.eventos import EventoDominio, bus_eventos
from app.core.excepciones import RecursoNoEncontrado, ReglaDeNegocioViolada
from app.modulos.catalogos.contrato import CatalogosLocal, ContratoCatalogos
from app.modulos.lista_espera.bo import (
    DEFAULT_TIMEOUT_MINUTOS,
    ListaEsperaBO,
    RequisitosViaje,
)
from app.modulos.lista_espera.dao import ListaEsperaDAO
from app.modulos.lista_espera.models import EntradaLista
from app.modulos.lista_espera.schemas import (
    AnotarListaRequest,
    EntradaListaResponse,
    OfertaListaResponse,
    OfertarSiguienteRequest,
)


class ListaEsperaService:
    """Casos de uso de la cola FIFO."""

    def __init__(
        self,
        sesion: AsyncSession,
        catalogos: ContratoCatalogos | None = None,
    ) -> None:
        self._sesion = sesion
        self._dao = ListaEsperaDAO(sesion)
        self._bo = ListaEsperaBO()
        self._catalogos = catalogos or CatalogosLocal(sesion)

    async def listar(
        self, empresa_id: str = "default", *, solo_activas: bool = True
    ) -> list[EntradaListaResponse]:
        await self.procesar_timeouts(empresa_id)
        entradas = await self._dao.listar(empresa_id, solo_activas=solo_activas)
        ordenadas = self._bo.ordenar_fifo(entradas)
        return [EntradaListaResponse.model_validate(e) for e in ordenadas]

    async def anotar(self, datos: AnotarListaRequest) -> EntradaListaResponse:
        unidad = await self._catalogos.obtener_unidad_por_chofer_camion(
            datos.chofer_id, datos.camion_id
        )
        if unidad is None:
            raise ReglaDeNegocioViolada(
                "Chofer/camión inexistentes, inactivos o no vinculados"
            )
        self._bo.validar_anotacion_no_propia(unidad.es_flota_propia)

        existente = await self._dao.buscar_activa_por_camion(
            datos.empresa_id, datos.camion_id
        )
        if existente is not None:
            raise ReglaDeNegocioViolada("Esa unidad ya está en la lista de espera")

        ahora = datetime.now(UTC)
        entrada = EntradaLista(
            empresa_id=datos.empresa_id,
            transportista_id=unidad.transportista_id,
            camion_id=unidad.camion_id,
            chofer_id=unidad.chofer_id,
            transportista_nombre=unidad.transportista_nombre,
            chofer_nombre=unidad.chofer_nombre,
            dominio=unidad.dominio,
            capacidad_tn=unidad.capacidad_tn,
            tipo_unidad=unidad.tipo_unidad,
            estado="en_espera",
            anotado_en=ahora,
        )
        await self._dao.guardar(entrada)
        await self._sesion.commit()
        await bus_eventos.publicar(
            EventoDominio(
                nombre="lista_espera.entrada.anotada",
                datos={
                    "entrada_id": entrada.id,
                    "empresa_id": entrada.empresa_id,
                    "camion_id": entrada.camion_id,
                    "chofer_id": entrada.chofer_id,
                },
            )
        )
        return EntradaListaResponse.model_validate(entrada)

    async def quitar(self, entrada_id: str) -> None:
        entrada = await self._buscar_o_fallar(entrada_id)
        self._bo.validar_quitar(entrada)
        await self._dao.eliminar(entrada)
        await self._sesion.commit()

    async def ofertar_siguiente(
        self, datos: OfertarSiguienteRequest
    ) -> OfertaListaResponse:
        await self.procesar_timeouts(datos.empresa_id, commit=False)

        oferta_actual = await self._dao.buscar_oferta_por_viaje(
            datos.empresa_id, datos.viaje_id
        )
        if oferta_actual is not None:
            return OfertaListaResponse(
                entrada=EntradaListaResponse.model_validate(oferta_actual),
                mensaje="Ya hay una oferta activa para este viaje",
            )

        entradas = await self._dao.listar(datos.empresa_id, solo_activas=True)
        req = RequisitosViaje(
            toneladas=datos.toneladas, tipo_unidad=datos.tipo_unidad
        )
        siguiente = self._bo.elegir_siguiente(entradas, req)
        if siguiente is None:
            await self._sesion.commit()
            return OfertaListaResponse(
                entrada=None,
                mensaje="No hay unidades compatibles en espera",
            )

        ahora = datetime.now(UTC)
        self._bo.ofertar(siguiente, datos.viaje_id, ahora)
        await self._sesion.commit()
        await bus_eventos.publicar(
            EventoDominio(
                nombre="lista_espera.entrada.ofertada",
                datos={
                    "entrada_id": siguiente.id,
                    "viaje_id": datos.viaje_id,
                    "chofer_id": siguiente.chofer_id,
                    "camion_id": siguiente.camion_id,
                },
            )
        )
        return OfertaListaResponse(
            entrada=EntradaListaResponse.model_validate(siguiente),
            mensaje="Oferta enviada al siguiente de la lista",
        )

    async def aceptar_oferta(
        self, entrada_id: str, viaje_id: str
    ) -> EntradaListaResponse:
        entrada = await self._buscar_o_fallar(entrada_id)
        self._bo.marcar_asignada(entrada, viaje_id)
        await self._sesion.commit()
        await bus_eventos.publicar(
            EventoDominio(
                nombre="lista_espera.entrada.asignada",
                datos={
                    "entrada_id": entrada.id,
                    "viaje_id": viaje_id,
                    "chofer_id": entrada.chofer_id,
                    "camion_id": entrada.camion_id,
                },
            )
        )
        return EntradaListaResponse.model_validate(entrada)

    async def rechazar_oferta(self, entrada_id: str) -> EntradaListaResponse:
        entrada = await self._buscar_o_fallar(entrada_id)
        if entrada.estado != "ofertado":
            raise ReglaDeNegocioViolada("La entrada no tiene una oferta activa")
        ahora = datetime.now(UTC)
        viaje_id = entrada.viaje_ofertado_id
        self._bo.mandar_al_fondo(entrada, ahora)
        await self._sesion.commit()
        await bus_eventos.publicar(
            EventoDominio(
                nombre="lista_espera.entrada.al_fondo",
                datos={
                    "entrada_id": entrada.id,
                    "viaje_id": viaje_id,
                    "motivo": "rechazo",
                },
            )
        )
        return EntradaListaResponse.model_validate(entrada)

    async def procesar_timeouts(
        self,
        empresa_id: str = "default",
        *,
        timeout_minutos: int = DEFAULT_TIMEOUT_MINUTOS,
        commit: bool = True,
    ) -> list[EntradaListaResponse]:
        ofertadas = await self._dao.listar_ofertadas(empresa_id)
        ahora = datetime.now(UTC)
        movidas: list[EntradaLista] = []
        for entrada in ofertadas:
            if self._bo.oferta_vencida(entrada, ahora, timeout_minutos):
                viaje_id = entrada.viaje_ofertado_id
                self._bo.mandar_al_fondo(entrada, ahora)
                movidas.append(entrada)
                await bus_eventos.publicar(
                    EventoDominio(
                        nombre="lista_espera.entrada.al_fondo",
                        datos={
                            "entrada_id": entrada.id,
                            "viaje_id": viaje_id,
                            "motivo": "timeout",
                        },
                    )
                )
        if commit and movidas:
            await self._sesion.commit()
        elif not commit:
            await self._sesion.flush()
        return [EntradaListaResponse.model_validate(e) for e in movidas]

    async def reencolar_al_completar(self, viaje_id: str) -> EntradaListaResponse | None:
        entrada = await self._dao.buscar_asignada_por_viaje(viaje_id)
        if entrada is None:
            return None
        ahora = datetime.now(UTC)
        self._bo.reencolar(entrada, ahora)
        await self._sesion.commit()
        await bus_eventos.publicar(
            EventoDominio(
                nombre="lista_espera.entrada.reencolada",
                datos={
                    "entrada_id": entrada.id,
                    "viaje_id": viaje_id,
                    "chofer_id": entrada.chofer_id,
                },
            )
        )
        return EntradaListaResponse.model_validate(entrada)

    async def _buscar_o_fallar(self, entrada_id: str) -> EntradaLista:
        entrada = await self._dao.buscar(entrada_id)
        if entrada is None:
            raise RecursoNoEncontrado("Entrada de lista de espera no encontrada")
        return entrada
