"""Casos de uso ABM expuestos en /transportistas y /productores."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excepciones import RecursoNoEncontrado
from app.modulos.auth.contrato import AuthLocal, ContratoAuth
from app.modulos.catalogos.abm_mappers import (
    aplicar_camion_ui,
    aplicar_campo_ui,
    aplicar_chofer_ui,
    aplicar_productor_ui,
    aplicar_transportista_ui,
    campo_a_abm,
    productor_a_abm,
    productor_detalle_a_abm,
    responsable_a_abm,
    texto_busqueda_productor,
    texto_busqueda_transportista,
    transportista_a_abm,
    transportista_detalle_a_abm,
)
from app.modulos.catalogos.bo import CatalogosBO
from app.modulos.catalogos.dao import CatalogosDAO
from app.modulos.catalogos.models import (
    Camion,
    Campo,
    Chofer,
    Productor,
    PuntoEntrada,
    ResponsableProductor,
    Transportista,
)
from app.modulos.catalogos.schemas import (
    ActualizarCamionRequest,
    ActualizarTransportistaRequest,
    CrearCamionRequest,
)
from app.modulos.catalogos.schemas_abm import (
    CambiarActivoAbm,
    GuardarCamionAbm,
    GuardarCampoAbm,
    GuardarChoferAbm,
    GuardarProductorAbm,
    GuardarResponsableAbm,
    GuardarTransportistaAbm,
    ProductorAbm,
    ProductorDetalleAbm,
    TransportistaAbm,
    TransportistaDetalleAbm,
    VendedorOptionAbm,
)
from app.modulos.catalogos.service import CatalogosService


class CatalogosAbmService:
    """Operaciones de las pantallas admin de transportistas y productores."""

    def __init__(self, sesion: AsyncSession, auth: ContratoAuth | None = None) -> None:
        self._sesion = sesion
        self._dao = CatalogosDAO(sesion)
        self._bo = CatalogosBO()
        self._catalogos = CatalogosService(sesion, auth)
        self._auth = auth or AuthLocal(sesion)

    # ----------------------------- Transportistas -----------------------------

    async def listar_transportistas(
        self, filtro: str = "activos", busqueda: str = ""
    ) -> list[TransportistaAbm]:
        transportistas = await self._dao.listar_transportistas(solo_activos=False)
        resultado: list[TransportistaAbm] = []
        q = busqueda.strip().lower()
        for t in transportistas:
            abm = transportista_a_abm(t)
            if filtro == "activos" and not t.activo:
                continue
            if filtro == "inactivos" and t.activo:
                continue
            if q and q not in texto_busqueda_transportista(t):
                continue
            resultado.append(abm)
        return resultado

    async def obtener_transportista(self, transportista_id: str) -> TransportistaDetalleAbm:
        transportista = await self._requerir_transportista(transportista_id)
        return transportista_detalle_a_abm(transportista)

    async def crear_transportista(
        self, datos: GuardarTransportistaAbm
    ) -> TransportistaDetalleAbm:
        existente = await self._dao.buscar_transportista_por_nombre(
            datos.nombre_fantasia or datos.razon_social
        )
        self._bo.validar_transportista_nuevo(nombre_ya_existe=existente is not None)
        transportista = Transportista(nombre="temp", cuit=datos.cuit or None)
        aplicar_transportista_ui(transportista, datos.model_dump())
        await self._dao.guardar(transportista)
        await self._sesion.commit()
        base = transportista_a_abm(transportista)
        return TransportistaDetalleAbm(**base.model_dump(), choferes=[], camiones=[])

    async def actualizar_transportista(
        self, transportista_id: str, datos: GuardarTransportistaAbm
    ) -> TransportistaDetalleAbm:
        transportista = await self._requerir_transportista(transportista_id)
        if datos.nombre_fantasia or datos.razon_social:
            nuevo_nombre = datos.nombre_fantasia or datos.razon_social
            if nuevo_nombre != transportista.nombre:
                existente = await self._dao.buscar_transportista_por_nombre(nuevo_nombre)
                self._bo.validar_transportista_nuevo(
                    nombre_ya_existe=existente is not None and existente.id != transportista_id
                )
        aplicar_transportista_ui(transportista, datos.model_dump())
        await self._sesion.commit()
        return await self.obtener_transportista(transportista_id)

    async def cambiar_activo_transportista(
        self, transportista_id: str, datos: CambiarActivoAbm
    ) -> TransportistaDetalleAbm:
        await self._catalogos.actualizar_transportista(
            transportista_id,
            ActualizarTransportistaRequest(activo=datos.activo),
        )
        return await self.obtener_transportista(transportista_id)

    async def eliminar_transportista(self, transportista_id: str) -> None:
        await self._catalogos.eliminar_transportista(transportista_id)

    async def crear_chofer(
        self, transportista_id: str, datos: GuardarChoferAbm
    ) -> TransportistaDetalleAbm:
        transportista = await self._requerir_transportista(transportista_id)
        chofer = Chofer(
            nombre=f"{datos.nombre} {datos.apellido}".strip(),
            transportista_id=transportista_id,
            camion_id=datos.camion_id or None,
        )
        aplicar_chofer_ui(chofer, datos.model_dump())
        transportista.choferes.append(chofer)
        await self._dao.guardar(chofer)
        await self._sesion.commit()
        return await self.obtener_transportista(transportista_id)

    async def actualizar_chofer(
        self, transportista_id: str, chofer_id: str, datos: GuardarChoferAbm
    ) -> TransportistaDetalleAbm:
        chofer = await self._requerir_chofer_de_transportista(transportista_id, chofer_id)
        aplicar_chofer_ui(chofer, datos.model_dump())
        chofer.camion_id = datos.camion_id or None
        await self._sesion.commit()
        return await self.obtener_transportista(transportista_id)

    async def cambiar_activo_chofer(
        self, transportista_id: str, chofer_id: str, datos: CambiarActivoAbm
    ) -> TransportistaDetalleAbm:
        chofer = await self._requerir_chofer_de_transportista(transportista_id, chofer_id)
        chofer.activo = datos.activo
        await self._sesion.commit()
        return await self.obtener_transportista(transportista_id)

    async def eliminar_chofer(
        self, transportista_id: str, chofer_id: str
    ) -> TransportistaDetalleAbm:
        await self._requerir_chofer_de_transportista(transportista_id, chofer_id)
        await self._catalogos.eliminar_chofer(chofer_id)
        return await self.obtener_transportista(transportista_id)

    async def crear_camion(
        self, transportista_id: str, datos: GuardarCamionAbm
    ) -> TransportistaDetalleAbm:
        dominio = self._bo.validar_dominio(datos.dominio)
        await self._catalogos.agregar_camion(
            transportista_id,
            CrearCamionRequest(dominio=dominio, modelo=datos.modelo),
        )
        camion = await self._dao.buscar_camion_por_dominio(dominio)
        if camion:
            aplicar_camion_ui(camion, datos.model_dump())
            await self._sesion.commit()
        return await self.obtener_transportista(transportista_id)

    async def actualizar_camion(
        self, transportista_id: str, camion_id: str, datos: GuardarCamionAbm
    ) -> TransportistaDetalleAbm:
        await self._catalogos.actualizar_camion(
            transportista_id,
            camion_id,
            ActualizarCamionRequest(
                dominio=datos.dominio or None,
                modelo=datos.modelo or None,
            ),
        )
        camion = await self._dao.buscar_camion_de_transportista(transportista_id, camion_id)
        if camion:
            aplicar_camion_ui(camion, datos.model_dump())
            await self._sesion.commit()
        return await self.obtener_transportista(transportista_id)

    async def cambiar_activo_camion(
        self, transportista_id: str, camion_id: str, datos: CambiarActivoAbm
    ) -> TransportistaDetalleAbm:
        await self._catalogos.actualizar_camion(
            transportista_id,
            camion_id,
            ActualizarCamionRequest(activo=datos.activo),
        )
        return await self.obtener_transportista(transportista_id)

    async def eliminar_camion(
        self, transportista_id: str, camion_id: str
    ) -> TransportistaDetalleAbm:
        await self._catalogos.eliminar_camion(transportista_id, camion_id)
        return await self.obtener_transportista(transportista_id)

    # ------------------------------- Productores ------------------------------

    async def listar_productores(
        self, filtro: str = "activos", busqueda: str = ""
    ) -> list[ProductorAbm]:
        productores = await self._dao.listar_productores()
        resultado: list[ProductorAbm] = []
        q = busqueda.strip().lower()
        for p in productores:
            if filtro == "activos" and not p.activo:
                continue
            if filtro == "inactivos" and p.activo:
                continue
            if q and q not in texto_busqueda_productor(p):
                continue
            resultado.append(productor_a_abm(p))
        return resultado

    async def obtener_productor(self, productor_id: str) -> ProductorDetalleAbm:
        productor = await self._requerir_productor(productor_id)
        return productor_detalle_a_abm(productor)

    async def crear_productor(self, datos: GuardarProductorAbm) -> ProductorDetalleAbm:
        existente = await self._dao.buscar_productor_por_nombre(
            datos.nombre_fantasia or datos.razon_social
        )
        self._bo.validar_productor_nuevo(nombre_ya_existe=existente is not None)
        productor = Productor(nombre="temp", cuit=datos.cuit or None)
        aplicar_productor_ui(productor, datos.model_dump())
        await self._dao.guardar(productor)
        await self._sesion.commit()
        base = productor_a_abm(productor)
        return ProductorDetalleAbm(**base.model_dump(), responsables=[], campos=[])

    async def actualizar_productor(
        self, productor_id: str, datos: GuardarProductorAbm
    ) -> ProductorDetalleAbm:
        productor = await self._requerir_productor(productor_id)
        if datos.nombre_fantasia or datos.razon_social:
            nuevo = datos.nombre_fantasia or datos.razon_social
            if nuevo != productor.nombre:
                existente = await self._dao.buscar_productor_por_nombre(nuevo)
                self._bo.validar_productor_nuevo(
                    nombre_ya_existe=existente is not None and existente.id != productor_id
                )
        aplicar_productor_ui(productor, datos.model_dump())
        await self._sesion.commit()
        return await self.obtener_productor(productor_id)

    async def cambiar_activo_productor(
        self, productor_id: str, datos: CambiarActivoAbm
    ) -> ProductorDetalleAbm:
        productor = await self._requerir_productor(productor_id)
        productor.activo = datos.activo
        await self._sesion.commit()
        return await self.obtener_productor(productor_id)

    async def eliminar_productor(self, productor_id: str) -> None:
        productor = await self._requerir_productor(productor_id)
        productor.activo = False
        for campo in productor.campos:
            campo.activo = False
        for responsable in productor.responsables:
            responsable.activo = False
        await self._sesion.commit()

    async def crear_responsable(
        self, productor_id: str, datos: GuardarResponsableAbm
    ) -> ProductorDetalleAbm:
        productor = await self._requerir_productor(productor_id)
        responsable = ResponsableProductor(
            productor_id=productor_id,
            nombre=datos.nombre,
            apellido=datos.apellido,
            telefono=datos.telefono,
            documento=datos.documento,
        )
        productor.responsables.append(responsable)
        await self._dao.guardar(responsable)
        await self._sesion.commit()
        return await self.obtener_productor(productor_id)

    async def actualizar_responsable(
        self, productor_id: str, responsable_id: str, datos: GuardarResponsableAbm
    ) -> ProductorDetalleAbm:
        responsable = await self._requerir_responsable(productor_id, responsable_id)
        responsable.nombre = datos.nombre
        responsable.apellido = datos.apellido
        responsable.telefono = datos.telefono
        responsable.documento = datos.documento
        await self._sesion.commit()
        return await self.obtener_productor(productor_id)

    async def cambiar_activo_responsable(
        self, productor_id: str, responsable_id: str, datos: CambiarActivoAbm
    ) -> ProductorDetalleAbm:
        responsable = await self._requerir_responsable(productor_id, responsable_id)
        responsable.activo = datos.activo
        await self._sesion.commit()
        return await self.obtener_productor(productor_id)

    async def eliminar_responsable(
        self, productor_id: str, responsable_id: str
    ) -> ProductorDetalleAbm:
        responsable = await self._requerir_responsable(productor_id, responsable_id)
        responsable.activo = False
        await self._sesion.commit()
        return await self.obtener_productor(productor_id)

    async def crear_campo(
        self, productor_id: str, datos: GuardarCampoAbm
    ) -> ProductorDetalleAbm:
        productor = await self._requerir_productor(productor_id)
        campo = Campo(nombre=datos.nombre or "Campo", productor_id=productor_id)
        aplicar_campo_ui(campo, datos.model_dump())
        self._sincronizar_puntos(campo, datos.puntos_entrada)
        productor.campos.append(campo)
        await self._dao.guardar(campo)
        await self._sesion.commit()
        return await self.obtener_productor(productor_id)

    async def actualizar_campo(
        self, productor_id: str, campo_id: str, datos: GuardarCampoAbm
    ) -> ProductorDetalleAbm:
        campo = await self._requerir_campo(productor_id, campo_id)
        aplicar_campo_ui(campo, datos.model_dump())
        self._sincronizar_puntos(campo, datos.puntos_entrada)
        await self._sesion.commit()
        return await self.obtener_productor(productor_id)

    async def cambiar_activo_campo(
        self, productor_id: str, campo_id: str, datos: CambiarActivoAbm
    ) -> ProductorDetalleAbm:
        campo = await self._requerir_campo(productor_id, campo_id)
        campo.activo = datos.activo
        await self._sesion.commit()
        return await self.obtener_productor(productor_id)

    async def eliminar_campo(
        self, productor_id: str, campo_id: str
    ) -> ProductorDetalleAbm:
        campo = await self._requerir_campo(productor_id, campo_id)
        campo.activo = False
        await self._sesion.commit()
        return await self.obtener_productor(productor_id)

    async def listar_vendedores(self) -> list[VendedorOptionAbm]:
        vendedores = await self._auth.listar_por_rol("vendedor")
        return [VendedorOptionAbm(id=v.id, nombre=v.nombre) for v in vendedores]

    # -------------------------------- Helpers ---------------------------------

    async def _requerir_transportista(self, transportista_id: str) -> Transportista:
        transportista = await self._dao.buscar_transportista(transportista_id)
        if transportista is None:
            raise RecursoNoEncontrado("Transportista no encontrado")
        return transportista

    async def _requerir_chofer_de_transportista(
        self, transportista_id: str, chofer_id: str
    ) -> Chofer:
        chofer = await self._dao.buscar_chofer(chofer_id)
        if chofer is None or chofer.transportista_id != transportista_id:
            raise RecursoNoEncontrado("Chofer no encontrado")
        return chofer

    async def _requerir_productor(self, productor_id: str) -> Productor:
        productor = await self._dao.buscar_productor(productor_id)
        if productor is None:
            raise RecursoNoEncontrado("Productor no encontrado")
        return productor

    async def _requerir_responsable(
        self, productor_id: str, responsable_id: str
    ) -> ResponsableProductor:
        productor = await self._requerir_productor(productor_id)
        responsable = next((r for r in productor.responsables if r.id == responsable_id), None)
        if responsable is None:
            raise RecursoNoEncontrado("Responsable no encontrado")
        return responsable

    async def _requerir_campo(self, productor_id: str, campo_id: str) -> Campo:
        campo = await self._dao.buscar_campo(campo_id)
        if campo is None or campo.productor_id != productor_id:
            raise RecursoNoEncontrado("Campo no encontrado")
        return campo

    @staticmethod
    def _sincronizar_puntos(campo: Campo, puntos: list) -> None:
        existentes = {p.id: p for p in campo.puntos_entrada}
        ids_vistos: set[str] = set()
        for indice, punto in enumerate(puntos, start=1):
            datos = punto.model_dump() if hasattr(punto, "model_dump") else dict(punto)
            pid = datos.get("id")
            if pid and pid in existentes:
                entidad = existentes[pid]
                entidad.nombre = datos.get("nombre") or f"Entrada {indice}"
                entidad.orden = datos.get("orden") or indice
                entidad.latitud = float(datos.get("latitud") or 0)
                entidad.longitud = float(datos.get("longitud") or 0)
                entidad.observacion = datos.get("observacion") or ""
                entidad.activo = True
                ids_vistos.add(pid)
            else:
                campo.puntos_entrada.append(
                    PuntoEntrada(
                        nombre=datos.get("nombre") or f"Entrada {indice}",
                        orden=datos.get("orden") or indice,
                        latitud=float(datos.get("latitud") or 0),
                        longitud=float(datos.get("longitud") or 0),
                        observacion=datos.get("observacion") or "",
                    )
                )
        for punto in campo.puntos_entrada:
            if punto.id in existentes and punto.id not in ids_vistos:
                punto.activo = False
