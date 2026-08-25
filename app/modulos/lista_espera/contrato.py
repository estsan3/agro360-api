"""Contrato público del módulo lista de espera."""

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.modulos.lista_espera.dao import ListaEsperaDAO
from app.modulos.lista_espera.schemas import (
    EntradaListaResponse,
    OfertaListaResponse,
    OfertarSiguienteRequest,
)
from app.modulos.lista_espera.service import ListaEsperaService


@dataclass(frozen=True)
class OfertaResumen:
    entrada_id: str | None
    chofer_id: str | None
    camion_id: str | None
    dominio: str | None
    mensaje: str


class ContratoListaEspera(Protocol):
    async def ofertar_siguiente(
        self,
        viaje_id: str,
        toneladas: float,
        *,
        tipo_unidad: str | None = None,
        empresa_id: str = "default",
    ) -> OfertaResumen: ...

    async def aceptar_oferta(
        self, entrada_id: str, viaje_id: str
    ) -> EntradaListaResponse: ...

    async def rechazar_oferta(self, entrada_id: str) -> EntradaListaResponse: ...

    async def obtener_oferta_viaje(
        self, empresa_id: str, viaje_id: str
    ) -> EntradaListaResponse | None: ...

    async def reencolar_al_completar(
        self, viaje_id: str
    ) -> EntradaListaResponse | None: ...

    async def procesar_timeouts(self, empresa_id: str = "default") -> None: ...


class ListaEsperaLocal:
    """Implementación local del contrato."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion
        self._service = ListaEsperaService(sesion)
        self._dao = ListaEsperaDAO(sesion)

    async def ofertar_siguiente(
        self,
        viaje_id: str,
        toneladas: float,
        *,
        tipo_unidad: str | None = None,
        empresa_id: str = "default",
    ) -> OfertaResumen:
        resultado: OfertaListaResponse = await self._service.ofertar_siguiente(
            OfertarSiguienteRequest(
                viaje_id=viaje_id,
                toneladas=toneladas,
                tipo_unidad=tipo_unidad,
                empresa_id=empresa_id,
            )
        )
        entrada = resultado.entrada
        return OfertaResumen(
            entrada_id=entrada.id if entrada else None,
            chofer_id=entrada.chofer_id if entrada else None,
            camion_id=entrada.camion_id if entrada else None,
            dominio=entrada.dominio if entrada else None,
            mensaje=resultado.mensaje,
        )

    async def aceptar_oferta(
        self, entrada_id: str, viaje_id: str
    ) -> EntradaListaResponse:
        return await self._service.aceptar_oferta(entrada_id, viaje_id)

    async def rechazar_oferta(self, entrada_id: str) -> EntradaListaResponse:
        return await self._service.rechazar_oferta(entrada_id)

    async def obtener_oferta_viaje(
        self, empresa_id: str, viaje_id: str
    ) -> EntradaListaResponse | None:
        entrada = await self._dao.buscar_oferta_por_viaje(empresa_id, viaje_id)
        if entrada is None:
            return None
        return EntradaListaResponse.model_validate(entrada)

    async def reencolar_al_completar(
        self, viaje_id: str
    ) -> EntradaListaResponse | None:
        return await self._service.reencolar_al_completar(viaje_id)

    async def procesar_timeouts(self, empresa_id: str = "default") -> None:
        await self._service.procesar_timeouts(empresa_id)
