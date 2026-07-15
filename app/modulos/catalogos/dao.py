"""Capa DAO del módulo catálogos."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modulos.catalogos.models import Camion, Campo, Chofer, Material, Productor, Transportista


class CatalogosDAO:
    """Persistencia de los cuatro maestros del módulo.

    Son entidades chicas y homogéneas; un DAO único evita boilerplate.
    Si algún maestro crece en complejidad, se separa en su propio DAO.
    """

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    # ------------------------- Productores / Campos -------------------------

    async def listar_productores(self) -> list[Productor]:
        resultado = await self._sesion.execute(
            select(Productor).order_by(Productor.nombre)
        )
        return list(resultado.scalars())

    async def buscar_productor(self, productor_id: str) -> Productor | None:
        resultado = await self._sesion.execute(
            select(Productor)
            .where(Productor.id == productor_id)
            .options(
                selectinload(Productor.campos).selectinload(Campo.puntos_entrada),
                selectinload(Productor.responsables),
            )
        )
        return resultado.scalar_one_or_none()

    async def buscar_productor_por_nombre(self, nombre: str) -> Productor | None:
        resultado = await self._sesion.execute(
            select(Productor).where(Productor.nombre == nombre)
        )
        return resultado.scalar_one_or_none()

    async def buscar_campo(self, campo_id: str) -> Campo | None:
        resultado = await self._sesion.execute(
            select(Campo)
            .where(Campo.id == campo_id)
            .options(selectinload(Campo.puntos_entrada))
        )
        return resultado.scalar_one_or_none()

    # ------------------------------ Materiales ------------------------------

    async def listar_materiales(self) -> list[Material]:
        resultado = await self._sesion.execute(select(Material).order_by(Material.nombre))
        return list(resultado.scalars())

    async def buscar_material_por_nombre(self, nombre: str) -> Material | None:
        resultado = await self._sesion.execute(
            select(Material).where(Material.nombre == nombre)
        )
        return resultado.scalar_one_or_none()

    async def buscar_material(self, material_id: str) -> Material | None:
        return await self._sesion.get(Material, material_id)

    # ------------------------------- Choferes -------------------------------

    async def listar_choferes(self, solo_activos: bool = True) -> list[Chofer]:
        consulta = select(Chofer).order_by(Chofer.nombre)
        if solo_activos:
            consulta = consulta.where(Chofer.activo.is_(True))
        resultado = await self._sesion.execute(consulta)
        return list(resultado.scalars())

    async def buscar_chofer(self, chofer_id: str) -> Chofer | None:
        return await self._sesion.get(Chofer, chofer_id)

    # --------------------------- Transportistas / Camiones ---------------------------

    async def listar_transportistas(self, solo_activos: bool = True) -> list[Transportista]:
        consulta = select(Transportista).order_by(Transportista.nombre)
        if solo_activos:
            consulta = consulta.where(Transportista.activo.is_(True))
        resultado = await self._sesion.execute(consulta)
        return list(resultado.scalars())

    async def buscar_transportista(self, transportista_id: str) -> Transportista | None:
        resultado = await self._sesion.execute(
            select(Transportista)
            .where(Transportista.id == transportista_id)
            .options(
                selectinload(Transportista.choferes),
                selectinload(Transportista.camiones),
            )
        )
        return resultado.scalar_one_or_none()

    async def buscar_transportista_por_nombre(self, nombre: str) -> Transportista | None:
        resultado = await self._sesion.execute(
            select(Transportista).where(Transportista.nombre == nombre)
        )
        return resultado.scalar_one_or_none()

    async def buscar_camion(self, camion_id: str) -> Camion | None:
        return await self._sesion.get(Camion, camion_id)

    async def buscar_camion_por_dominio(self, dominio: str) -> Camion | None:
        resultado = await self._sesion.execute(
            select(Camion).where(Camion.dominio == dominio)
        )
        return resultado.scalar_one_or_none()

    async def buscar_camion_de_transportista(
        self, transportista_id: str, camion_id: str
    ) -> Camion | None:
        camion = await self.buscar_camion(camion_id)
        if camion is None or camion.transportista_id != transportista_id:
            return None
        return camion

    # -------------------------------- Genérico ------------------------------

    async def guardar(self, entidad: object) -> None:
        """Agrega cualquier entidad del módulo a la sesión (commit en service)."""
        self._sesion.add(entidad)
        await self._sesion.flush()

    async def eliminar(self, entidad: object) -> None:
        """Elimina la entidad de la sesión (commit en service)."""
        await self._sesion.delete(entidad)
        await self._sesion.flush()
