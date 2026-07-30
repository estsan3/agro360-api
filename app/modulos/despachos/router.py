"""Capa API del módulo despachos."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.core.dependencias import obtener_usuario_actual, requerir_rol
from app.modulos.despachos.schemas import (
    ActualizarMetadatosDespachoRequest,
    ActualizarViajeRequest,
    AsignarPorListaRequest,
    BuscarTransportistasRequest,
    CrearDespachoRequest,
    CrearViajeRequest,
    DespachoResponse,
    DuplicarDespachoRequest,
    ResolverTarifaRequest,
    ResolverTarifaResponse,
    TarifaNacionalResponse,
    TarifasNacionalesRequest,
)
from app.modulos.despachos.service import DespachosService

router = APIRouter(
    prefix="/despachos",
    tags=["Despachos"],
    dependencies=[Depends(obtener_usuario_actual)],
)

Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]


@router.get("", response_model=list[DespachoResponse], operation_id="listar_despachos")
async def listar(
    sesion: Sesion,
    estado: Annotated[str | None, Query(pattern="^(borrador|activo|cerrado)$")] = None,
) -> list[DespachoResponse]:
    """Lista las campañas de despacho, opcionalmente filtradas por estado."""
    return await DespachosService(sesion).listar(estado)


@router.get(
    "/tarifas-nacionales",
    response_model=list[TarifaNacionalResponse],
    operation_id="listar_tarifas_nacionales",
)
async def listar_tarifas_nacionales(sesion: Sesion) -> list[TarifaNacionalResponse]:
    """Tabla FADEEAC orientativa ($/tn por tramo de km)."""
    return await DespachosService(sesion).listar_tarifas_nacionales()


@router.put(
    "/tarifas-nacionales",
    response_model=list[TarifaNacionalResponse],
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="guardar_tarifas_nacionales",
)
async def guardar_tarifas_nacionales(
    datos: TarifasNacionalesRequest, sesion: Sesion
) -> list[TarifaNacionalResponse]:
    return await DespachosService(sesion).guardar_tarifas_nacionales(datos.tramos)


@router.post(
    "/tarifas-nacionales/resolver",
    response_model=ResolverTarifaResponse,
    operation_id="resolver_tarifa_nacional",
)
async def resolver_tarifa(
    datos: ResolverTarifaRequest, sesion: Sesion
) -> ResolverTarifaResponse:
    return await DespachosService(sesion).resolver_tarifa(datos.distancia_km)


@router.get("/{despacho_id}", response_model=DespachoResponse, operation_id="obtener_despacho")
async def obtener(despacho_id: str, sesion: Sesion) -> DespachoResponse:
    """Devuelve una campaña con todos sus viajes."""
    return await DespachosService(sesion).obtener(despacho_id)


@router.post("", response_model=DespachoResponse, status_code=201, operation_id="crear_despacho")
async def crear(datos: CrearDespachoRequest, sesion: Sesion) -> DespachoResponse:
    """Crea una campaña. Con `estado="activo"` queda operativa en un solo paso."""
    return await DespachosService(sesion).crear(datos)


@router.put(
    "/{despacho_id}", response_model=DespachoResponse, operation_id="actualizar_despacho"
)
async def actualizar(
    despacho_id: str, datos: CrearDespachoRequest, sesion: Sesion
) -> DespachoResponse:
    """Edita una campaña en borrador (reemplaza datos y viajes)."""
    return await DespachosService(sesion).actualizar(despacho_id, datos)


@router.post(
    "/{despacho_id}/activar", response_model=DespachoResponse, operation_id="activar_despacho"
)
async def activar(despacho_id: str, sesion: Sesion) -> DespachoResponse:
    """Activa una campaña en borrador (requiere al menos un viaje)."""
    return await DespachosService(sesion).activar(despacho_id)


@router.post(
    "/{despacho_id}/buscar-transportistas",
    response_model=DespachoResponse,
    operation_id="buscar_transportistas_despacho",
)
async def buscar_transportistas(
    despacho_id: str,
    sesion: Sesion,
    datos: BuscarTransportistasRequest = BuscarTransportistasRequest(),
) -> DespachoResponse:
    """Crea el viaje en búsqueda (si no hay) y notifica a transportistas."""
    return await DespachosService(sesion).buscar_transportistas(despacho_id, datos)


@router.delete("/{despacho_id}", status_code=204, operation_id="eliminar_despacho")
async def eliminar(despacho_id: str, sesion: Sesion) -> None:
    """Elimina una campaña en borrador. Las activas no se pueden eliminar."""
    await DespachosService(sesion).eliminar(despacho_id)


@router.post(
    "/{despacho_id}/cerrar", response_model=DespachoResponse, operation_id="cerrar_despacho"
)
async def cerrar(despacho_id: str, sesion: Sesion) -> DespachoResponse:
    """Cierra una campaña activa cuando todos sus viajes están completados."""
    return await DespachosService(sesion).cerrar(despacho_id)


@router.patch(
    "/{despacho_id}/metadatos",
    response_model=DespachoResponse,
    operation_id="actualizar_metadatos_despacho",
)
async def actualizar_metadatos(
    despacho_id: str, datos: ActualizarMetadatosDespachoRequest, sesion: Sesion
) -> DespachoResponse:
    """Ajusta fecha de llegada estimada y observaciones de una campaña activa."""
    return await DespachosService(sesion).actualizar_metadatos(despacho_id, datos)


@router.post(
    "/{despacho_id}/duplicar",
    response_model=DespachoResponse,
    status_code=201,
    operation_id="duplicar_despacho",
)
async def duplicar(
    despacho_id: str,
    sesion: Sesion,
    datos: DuplicarDespachoRequest | None = None,
) -> DespachoResponse:
    """Crea un borrador copia de la campaña indicada."""
    return await DespachosService(sesion).duplicar(despacho_id, datos)


@router.post(
    "/{despacho_id}/viajes",
    response_model=DespachoResponse,
    status_code=201,
    operation_id="agregar_viaje",
)
async def agregar_viaje(
    despacho_id: str, datos: CrearViajeRequest, sesion: Sesion
) -> DespachoResponse:
    """Agrega un viaje a una campaña existente."""
    return await DespachosService(sesion).agregar_viaje(despacho_id, datos)


@router.patch(
    "/{despacho_id}/viajes/{viaje_id}",
    response_model=DespachoResponse,
    operation_id="actualizar_viaje",
)
async def actualizar_viaje(
    despacho_id: str, viaje_id: str, datos: ActualizarViajeRequest, sesion: Sesion
) -> DespachoResponse:
    """Actualiza un viaje: asignar chofer, cambiar estado, progreso u observaciones."""
    return await DespachosService(sesion).actualizar_viaje(despacho_id, viaje_id, datos)


@router.post(
    "/{despacho_id}/viajes/{viaje_id}/iniciar",
    response_model=DespachoResponse,
    operation_id="iniciar_viaje",
)
async def iniciar_viaje(despacho_id: str, viaje_id: str, sesion: Sesion) -> DespachoResponse:
    """El viaje sale a la ruta (pasa a en_viaje). Requiere chofer asignado."""
    return await DespachosService(sesion).iniciar_viaje(despacho_id, viaje_id)


@router.post(
    "/{despacho_id}/viajes/{viaje_id}/asignar-por-lista",
    response_model=DespachoResponse,
    operation_id="asignar_viaje_por_lista",
)
async def asignar_por_lista(
    despacho_id: str,
    viaje_id: str,
    sesion: Sesion,
    datos: AsignarPorListaRequest = AsignarPorListaRequest(),
) -> DespachoResponse:
    """Asigna flota propia si hay; si no, ofrece al siguiente de la lista FIFO."""
    return await DespachosService(sesion).asignar_por_lista(despacho_id, viaje_id, datos)


@router.post(
    "/{despacho_id}/viajes/{viaje_id}/aceptar-oferta-lista",
    response_model=DespachoResponse,
    operation_id="aceptar_oferta_lista_viaje",
)
async def aceptar_oferta_lista(
    despacho_id: str,
    viaje_id: str,
    sesion: Sesion,
    entrada_id: Annotated[str, Query()],
    empresa_id: Annotated[str, Query()] = "default",
) -> DespachoResponse:
    """Acepta la oferta de lista de espera y asigna el chofer al viaje."""
    return await DespachosService(sesion).aceptar_oferta_lista(
        despacho_id, viaje_id, entrada_id, empresa_id=empresa_id
    )


@router.post(
    "/{despacho_id}/viajes/{viaje_id}/rechazar-oferta-lista",
    response_model=DespachoResponse,
    operation_id="rechazar_oferta_lista_viaje",
)
async def rechazar_oferta_lista(
    despacho_id: str,
    viaje_id: str,
    sesion: Sesion,
    empresa_id: Annotated[str, Query()] = "default",
    tipo_unidad: Annotated[str | None, Query()] = None,
) -> DespachoResponse:
    """Rechaza la oferta (unidad al fondo) y ofrece al siguiente apto."""
    return await DespachosService(sesion).rechazar_oferta_lista(
        despacho_id, viaje_id, empresa_id=empresa_id, tipo_unidad=tipo_unidad
    )


@router.post(
    "/{despacho_id}/viajes/{viaje_id}/duplicar",
    response_model=DespachoResponse,
    status_code=201,
    operation_id="duplicar_viaje",
)
async def duplicar_viaje(despacho_id: str, viaje_id: str, sesion: Sesion) -> DespachoResponse:
    """Duplica un viaje (mismo chofer, destino y toneladas)."""
    return await DespachosService(sesion).duplicar_viaje(despacho_id, viaje_id)


@router.delete(
    "/{despacho_id}/viajes/{viaje_id}",
    response_model=DespachoResponse,
    operation_id="eliminar_viaje",
)
async def eliminar_viaje(despacho_id: str, viaje_id: str, sesion: Sesion) -> DespachoResponse:
    """Elimina un viaje que todavía no salió a la ruta."""
    return await DespachosService(sesion).eliminar_viaje(despacho_id, viaje_id)
