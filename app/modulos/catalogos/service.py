"""Capa SERVICE del módulo catálogos."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excepciones import RecursoNoEncontrado
from app.modulos.auth.contrato import AuthLocal, ContratoAuth
from app.modulos.catalogos.bo import CatalogosBO
from app.modulos.catalogos.dao import CatalogosDAO
from app.modulos.catalogos.models import Campo, Camion, Chofer, Material, Productor, Transportista
from app.modulos.catalogos.schemas import (
    ActualizarCamionRequest,
    ActualizarTransportistaRequest,
    CamionAgregadoResponse,
    CamionResponse,
    CatalogosAgregadosResponse,
    ChoferAgregadoResponse,
    ChoferResponse,
    CrearCamionRequest,
    CrearCampoRequest,
    CrearChoferRequest,
    CrearMaterialRequest,
    CrearProductorRequest,
    CrearTransportistaRequest,
    MaterialResponse,
    PersonaResumenResponse,
    ProductorResponse,
    TransportistaAgregadoResponse,
    TransportistaResponse,
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
        transportistas = await self._dao.listar_transportistas()
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
            transportistas=[
                TransportistaAgregadoResponse(
                    id=t.id,
                    nombre=t.nombre,
                    camiones=[
                        CamionAgregadoResponse(id=c.id, dominio=c.dominio, modelo=c.modelo)
                        for c in t.camiones
                        if c.activo
                    ],
                )
                for t in transportistas
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

    # ------------------------- Transportistas / Camiones -------------------------

    async def listar_transportistas(self) -> list[TransportistaResponse]:
        transportistas = await self._dao.listar_transportistas()
        return [TransportistaResponse.model_validate(t) for t in transportistas]

    async def crear_transportista(
        self, datos: CrearTransportistaRequest
    ) -> TransportistaResponse:
        existente = await self._dao.buscar_transportista_por_nombre(datos.nombre)
        self._bo.validar_transportista_nuevo(nombre_ya_existe=existente is not None)

        transportista = Transportista(nombre=datos.nombre, cuit=datos.cuit)
        await self._dao.guardar(transportista)
        await self._sesion.commit()
        await self._sesion.refresh(transportista, attribute_names=["camiones"])
        return TransportistaResponse.model_validate(transportista)

    async def actualizar_transportista(
        self, transportista_id: str, datos: ActualizarTransportistaRequest
    ) -> TransportistaResponse:
        transportista = await self._dao.buscar_transportista(transportista_id)
        if transportista is None:
            raise RecursoNoEncontrado("Transportista no encontrado")

        if datos.nombre is not None and datos.nombre != transportista.nombre:
            existente = await self._dao.buscar_transportista_por_nombre(datos.nombre)
            self._bo.validar_transportista_nuevo(nombre_ya_existe=existente is not None)
            transportista.nombre = datos.nombre
        if datos.cuit is not None:
            transportista.cuit = datos.cuit
        if datos.activo is not None:
            transportista.activo = datos.activo

        await self._sesion.commit()
        await self._sesion.refresh(transportista, attribute_names=["camiones"])
        return TransportistaResponse.model_validate(transportista)

    async def eliminar_transportista(self, transportista_id: str) -> None:
        transportista = await self._dao.buscar_transportista(transportista_id)
        if transportista is None:
            raise RecursoNoEncontrado("Transportista no encontrado")
        transportista.activo = False
        for camion in transportista.camiones:
            camion.activo = False
        await self._sesion.commit()

    async def agregar_camion(
        self, transportista_id: str, datos: CrearCamionRequest
    ) -> TransportistaResponse:
        transportista = await self._dao.buscar_transportista(transportista_id)
        if transportista is None:
            raise RecursoNoEncontrado("Transportista no encontrado")

        dominio = self._bo.validar_dominio(datos.dominio)
        existente = await self._dao.buscar_camion_por_dominio(dominio)
        self._bo.validar_camion_nuevo(dominio_ya_existe=existente is not None)

        transportista.camiones.append(Camion(dominio=dominio, modelo=datos.modelo))
        await self._sesion.commit()
        await self._sesion.refresh(transportista, attribute_names=["camiones"])
        return TransportistaResponse.model_validate(transportista)

    async def actualizar_camion(
        self, transportista_id: str, camion_id: str, datos: ActualizarCamionRequest
    ) -> TransportistaResponse:
        transportista = await self._dao.buscar_transportista(transportista_id)
        if transportista is None:
            raise RecursoNoEncontrado("Transportista no encontrado")

        camion = await self._dao.buscar_camion_de_transportista(transportista_id, camion_id)
        if camion is None:
            raise RecursoNoEncontrado("Camión no encontrado en ese transportista")

        if datos.dominio is not None:
            dominio = self._bo.validar_dominio(datos.dominio)
            if dominio != camion.dominio:
                existente = await self._dao.buscar_camion_por_dominio(dominio)
                self._bo.validar_camion_nuevo(dominio_ya_existe=existente is not None)
                camion.dominio = dominio
        if datos.modelo is not None:
            camion.modelo = datos.modelo
        if datos.activo is not None:
            camion.activo = datos.activo

        await self._sesion.commit()
        await self._sesion.refresh(transportista, attribute_names=["camiones"])
        return TransportistaResponse.model_validate(transportista)

    async def eliminar_camion(self, transportista_id: str, camion_id: str) -> None:
        camion = await self._dao.buscar_camion_de_transportista(transportista_id, camion_id)
        if camion is None:
            raise RecursoNoEncontrado("Camión no encontrado en ese transportista")
        camion.activo = False
        await self._sesion.commit()

    # --------------------------------- Bajas ---------------------------------

    async def eliminar_productor(self, productor_id: str) -> None:
        """Elimina un productor con sus campos (cascada)."""
        productor = await self._dao.buscar_productor(productor_id)
        if productor is None:
            raise RecursoNoEncontrado("Productor no encontrado")
        await self._dao.eliminar(productor)
        await self._sesion.commit()

    async def eliminar_material(self, material_id: str) -> None:
        """Elimina por id o, si el front manda el nombre, lo resuelve por nombre."""
        material = await self._dao.buscar_material(material_id)
        if material is None:
            material = await self._dao.buscar_material_por_nombre(material_id)
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
