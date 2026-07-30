"""Capa DAO del módulo lista de espera."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modulos.lista_espera.models import EntradaLista


class ListaEsperaDAO:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def listar(
        self,
        empresa_id: str,
        *,
        solo_activas: bool = True,
    ) -> list[EntradaLista]:
        consulta = select(EntradaLista).where(EntradaLista.empresa_id == empresa_id)
        if solo_activas:
            consulta = consulta.where(EntradaLista.estado.in_(["en_espera", "ofertado"]))
        consulta = consulta.order_by(EntradaLista.anotado_en)
        resultado = await self._sesion.execute(consulta)
        return list(resultado.scalars())

    async def buscar(self, entrada_id: str) -> EntradaLista | None:
        return await self._sesion.get(EntradaLista, entrada_id)

    async def buscar_activa_por_camion(
        self, empresa_id: str, camion_id: str
    ) -> EntradaLista | None:
        resultado = await self._sesion.execute(
            select(EntradaLista).where(
                EntradaLista.empresa_id == empresa_id,
                EntradaLista.camion_id == camion_id,
                EntradaLista.estado.in_(["en_espera", "ofertado"]),
            )
        )
        return resultado.scalar_one_or_none()

    async def buscar_oferta_por_viaje(
        self, empresa_id: str, viaje_id: str
    ) -> EntradaLista | None:
        resultado = await self._sesion.execute(
            select(EntradaLista).where(
                EntradaLista.empresa_id == empresa_id,
                EntradaLista.viaje_ofertado_id == viaje_id,
                EntradaLista.estado == "ofertado",
            )
        )
        return resultado.scalar_one_or_none()

    async def buscar_asignada_por_viaje(self, viaje_id: str) -> EntradaLista | None:
        resultado = await self._sesion.execute(
            select(EntradaLista).where(
                EntradaLista.viaje_asignado_id == viaje_id,
                EntradaLista.estado == "fuera",
            )
        )
        return resultado.scalar_one_or_none()

    async def listar_ofertadas(self, empresa_id: str) -> list[EntradaLista]:
        resultado = await self._sesion.execute(
            select(EntradaLista).where(
                EntradaLista.empresa_id == empresa_id,
                EntradaLista.estado == "ofertado",
            )
        )
        return list(resultado.scalars())

    async def guardar(self, entrada: EntradaLista) -> None:
        self._sesion.add(entrada)
        await self._sesion.flush()

    async def eliminar(self, entrada: EntradaLista) -> None:
        await self._sesion.delete(entrada)
        await self._sesion.flush()
