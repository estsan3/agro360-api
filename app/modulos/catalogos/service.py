"""Capa SERVICE del módulo catálogos."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excepciones import RecursoNoEncontrado
from app.modulos.catalogos.bo import CatalogosBO
from app.modulos.catalogos.dao import CatalogosDAO
from app.modulos.catalogos.models import Campo, Chofer, Material, Productor
from app.modulos.catalogos.schemas import (
    ChoferResponse,
    CrearCampoRequest,
    CrearChoferRequest,
    CrearMaterialRequest,
    CrearProductorRequest,
    MaterialResponse,
    ProductorResponse,
)


class CatalogosService:
    """Casos de uso de los catálogos maestros."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion
        self._dao = CatalogosDAO(sesion)
        self._bo = CatalogosBO()

    # ------------------------- Productores / Campos -------------------------

    async def listar_productores(self) -> list[ProductorResponse]:
        productores = await self._dao.listar_productores()
        return [ProductorResponse.model_validate(p) for p in productores]

    async def crear_productor(self, datos: CrearProductorRequest) -> ProductorResponse:
        existente = await self._dao.buscar_productor_por_nombre(datos.nombre)
        self._bo.validar_productor_nuevo(nombre_ya_existe=existente is not None)

        productor = Productor(
            nombre=datos.nombre,
            cuit=datos.cuit,
            campos=[Campo(nombre=nombre) for nombre in datos.campos],
        )
        await self._dao.guardar(productor)
        await self._sesion.commit()
        return ProductorResponse.model_validate(productor)

    async def agregar_campo(
        self, productor_id: str, datos: CrearCampoRequest
    ) -> ProductorResponse:
        productor = await self._dao.buscar_productor(productor_id)
        if productor is None:
            raise RecursoNoEncontrado("Productor no encontrado")

        productor.campos.append(Campo(nombre=datos.nombre))
        await self._sesion.commit()
        return ProductorResponse.model_validate(productor)

    # ------------------------------ Materiales ------------------------------

    async def listar_materiales(self) -> list[MaterialResponse]:
        materiales = await self._dao.listar_materiales()
        return [MaterialResponse.model_validate(m) for m in materiales]

    async def crear_material(self, datos: CrearMaterialRequest) -> MaterialResponse:
        existente = await self._dao.buscar_material_por_nombre(datos.nombre)
        self._bo.validar_material_nuevo(nombre_ya_existe=existente is not None)

        material = Material(nombre=datos.nombre, codigo_grano_afip=datos.codigo_grano_afip)
        await self._dao.guardar(material)
        await self._sesion.commit()
        return MaterialResponse.model_validate(material)

    # ------------------------------- Choferes -------------------------------

    async def listar_choferes(self) -> list[ChoferResponse]:
        choferes = await self._dao.listar_choferes()
        return [ChoferResponse.model_validate(c) for c in choferes]

    async def crear_chofer(self, datos: CrearChoferRequest) -> ChoferResponse:
        dominio = self._bo.validar_dominio(datos.dominio)

        chofer = Chofer(nombre=datos.nombre, dominio=dominio, cuit=datos.cuit)
        await self._dao.guardar(chofer)
        await self._sesion.commit()
        return ChoferResponse.model_validate(chofer)
