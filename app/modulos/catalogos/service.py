"""Capa SERVICE del módulo catálogos."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excepciones import RecursoNoEncontrado
from app.modulos.auth.contrato import AuthLocal, ContratoAuth
from app.modulos.catalogos.bo import CatalogosBO
from app.modulos.catalogos.dao import CatalogosDAO
from app.modulos.catalogos.models import Campo, Chofer, Material, Productor
from app.modulos.catalogos.schemas import (
    CatalogosAgregadosResponse,
    ChoferAgregadoResponse,
    ChoferResponse,
    CrearCampoRequest,
    CrearChoferRequest,
    CrearMaterialRequest,
    CrearProductorRequest,
    MaterialResponse,
    PersonaResumenResponse,
    ProductorResponse,
)


class CatalogosService:
    """Casos de uso de los catálogos maestros."""

    def __init__(self, sesion: AsyncSession, auth: ContratoAuth | None = None) -> None:
        self._sesion = sesion
        self._dao = CatalogosDAO(sesion)
        self._bo = CatalogosBO()
        # Contrato de auth para componer administradores/vendedores (inyectable).
        self._auth = auth or AuthLocal(sesion)

    # ------------------------- Respuesta agregada ---------------------------

    async def obtener_agregados(self) -> CatalogosAgregadosResponse:
        """Todos los catálogos en una sola respuesta (contrato del front).

        Administradores y vendedores son usuarios del módulo auth: se
        consultan por su contrato, nunca por sus modelos internos.
        """
        productores = await self._dao.listar_productores()
        materiales = await self._dao.listar_materiales()
        choferes = await self._dao.listar_choferes()
        administradores = await self._auth.listar_por_rol("administrador")
        vendedores = await self._auth.listar_por_rol("vendedor")

        return CatalogosAgregadosResponse(
            productores=[ProductorResponse.model_validate(p) for p in productores],
            administradores=[
                PersonaResumenResponse(id=u.id, nombre=u.nombre) for u in administradores
            ],
            vendedores=[
                PersonaResumenResponse(id=u.id, nombre=u.nombre) for u in vendedores
            ],
            materiales=[m.nombre for m in materiales],
            choferes=[
                ChoferAgregadoResponse(
                    id=c.id, nombre=c.nombre, dominio=c.dominio, modelo=c.modelo
                )
                for c in choferes
            ],
        )

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

        chofer = Chofer(
            nombre=datos.nombre, dominio=dominio, modelo=datos.modelo, cuit=datos.cuit
        )
        await self._dao.guardar(chofer)
        await self._sesion.commit()
        return ChoferResponse.model_validate(chofer)

    # --------------------------------- Bajas ---------------------------------

    async def eliminar_productor(self, productor_id: str) -> None:
        """Elimina un productor con sus campos (cascada)."""
        productor = await self._dao.buscar_productor(productor_id)
        if productor is None:
            raise RecursoNoEncontrado("Productor no encontrado")
        await self._dao.eliminar(productor)
        await self._sesion.commit()

    async def eliminar_material(self, material_id: str) -> None:
        material = await self._dao.buscar_material(material_id)
        if material is None:
            raise RecursoNoEncontrado("Material no encontrado")
        await self._dao.eliminar(material)
        await self._sesion.commit()

    async def eliminar_chofer(self, chofer_id: str) -> None:
        """Baja lógica: los viajes históricos conservan la referencia."""
        chofer = await self._dao.buscar_chofer(chofer_id)
        if chofer is None:
            raise RecursoNoEncontrado("Chofer no encontrado")
        chofer.activo = False
        await self._sesion.commit()
