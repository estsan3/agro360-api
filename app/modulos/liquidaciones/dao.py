"""Acceso a datos del módulo liquidaciones."""

from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modulos.liquidaciones.models import MovimientoCtacte, ParametroLiquidacion


class LiquidacionesDAO:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def guardar_movimiento(self, movimiento: MovimientoCtacte) -> MovimientoCtacte:
        self._sesion.add(movimiento)
        await self._sesion.flush()
        return movimiento

    async def guardar_movimientos(
        self, movimientos: list[MovimientoCtacte]
    ) -> list[MovimientoCtacte]:
        self._sesion.add_all(movimientos)
        await self._sesion.flush()
        return movimientos

    async def obtener_por_id(self, movimiento_id: str) -> MovimientoCtacte | None:
        return await self._sesion.get(MovimientoCtacte, movimiento_id)

    async def eliminar(self, movimiento: MovimientoCtacte) -> None:
        await self._sesion.delete(movimiento)
        await self._sesion.flush()

    async def existe_flete_para_viaje(self, viaje_id: str) -> bool:
        consulta = select(MovimientoCtacte.id).where(
            MovimientoCtacte.viaje_id == viaje_id,
            MovimientoCtacte.concepto == "flete",
        )
        resultado = await self._sesion.execute(consulta)
        return resultado.scalar_one_or_none() is not None

    def _filtro_periodo(
        self,
        consulta: Select[tuple[MovimientoCtacte]],
        transportista_id: str,
        desde: date | None,
        hasta: date | None,
    ) -> Select[tuple[MovimientoCtacte]]:
        consulta = consulta.where(MovimientoCtacte.transportista_id == transportista_id)
        if desde is not None:
            consulta = consulta.where(MovimientoCtacte.fecha >= desde)
        if hasta is not None:
            consulta = consulta.where(MovimientoCtacte.fecha <= hasta)
        return consulta.order_by(MovimientoCtacte.fecha, MovimientoCtacte.creado_en)

    async def listar_por_transportista(
        self,
        transportista_id: str,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[MovimientoCtacte]:
        consulta = self._filtro_periodo(
            select(MovimientoCtacte), transportista_id, desde, hasta
        )
        resultado = await self._sesion.execute(consulta)
        return list(resultado.scalars().all())

    async def saldo_antes_de(self, transportista_id: str, fecha: date) -> float:
        consulta = select(
            func.coalesce(func.sum(MovimientoCtacte.haber - MovimientoCtacte.debe), 0.0)
        ).where(
            MovimientoCtacte.transportista_id == transportista_id,
            MovimientoCtacte.fecha < fecha,
        )
        resultado = await self._sesion.execute(consulta)
        return float(resultado.scalar_one())

    async def saldo_actual(self, transportista_id: str) -> float:
        consulta = select(
            func.coalesce(func.sum(MovimientoCtacte.haber - MovimientoCtacte.debe), 0.0)
        ).where(MovimientoCtacte.transportista_id == transportista_id)
        resultado = await self._sesion.execute(consulta)
        return float(resultado.scalar_one())

    async def contar_movimientos(self, transportista_id: str) -> int:
        consulta = select(func.count()).where(
            MovimientoCtacte.transportista_id == transportista_id
        )
        resultado = await self._sesion.execute(consulta)
        return int(resultado.scalar_one())

    async def listar_transportista_ids(self) -> list[str]:
        consulta = select(MovimientoCtacte.transportista_id).distinct()
        resultado = await self._sesion.execute(consulta)
        return list(resultado.scalars().all())

    async def obtener_parametros(self) -> dict[str, str]:
        resultado = await self._sesion.execute(select(ParametroLiquidacion))
        return {p.clave: p.valor for p in resultado.scalars().all()}

    async def guardar_parametros(self, valores: dict[str, str]) -> None:
        existentes = await self.obtener_parametros()
        for clave, valor in valores.items():
            if clave in existentes:
                fila = await self._sesion.get(ParametroLiquidacion, clave)
                if fila is not None:
                    fila.valor = valor
            else:
                self._sesion.add(ParametroLiquidacion(clave=clave, valor=valor))
        await self._sesion.flush()
