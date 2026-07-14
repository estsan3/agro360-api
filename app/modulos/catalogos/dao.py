"""Capa DAO del módulo catálogos."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modulos.catalogos.models import Campo, Chofer, Material, Productor


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
        return await self._sesion.get(Productor, productor_id)

    async def buscar_productor_por_nombre(self, nombre: str) -> Productor | None:
        resultado = await self._sesion.execute(
            select(Productor).where(Productor.nombre == nombre)
        )
        return resultado.scalar_one_or_none()

    async def buscar_campo(self, campo_id: str) -> Campo | None:
        return await self._sesion.get(Campo, campo_id)

    # ------------------------------ Materiales ------------------------------

    async def listar_materiales(self) -> list[Material]:
        resultado = await self._sesion.execute(select(Material).order_by(Material.nombre))
        return list(resultado.scalars())

    async def buscar_material_por_nombre(self, nombre: str) -> Material | None:
        resultado = await self._sesion.execute(
            select(Material).where(Material.nombre == nombre)
        )
        return resultado.scalar_one_or_none()

    # ------------------------------- Choferes -------------------------------

    async def listar_choferes(self, solo_activos: bool = True) -> list[Chofer]:
        consulta = select(Chofer).order_by(Chofer.nombre)
        if solo_activos:
            consulta = consulta.where(Chofer.activo.is_(True))
        resultado = await self._sesion.execute(consulta)
        return list(resultado.scalars())

    async def buscar_chofer(self, chofer_id: str) -> Chofer | None:
        return await self._sesion.get(Chofer, chofer_id)

    # -------------------------------- Genérico ------------------------------

    async def guardar(self, entidad: object) -> None:
        """Agrega cualquier entidad del módulo a la sesión (commit en service)."""
        self._sesion.add(entidad)
        await self._sesion.flush()
