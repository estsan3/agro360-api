"""Capa API del módulo catálogos."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.core.dependencias import obtener_usuario_actual, requerir_rol
from app.modulos.catalogos.schemas import (
    ChoferResponse,
    CrearCampoRequest,
    CrearChoferRequest,
    CrearMaterialRequest,
    CrearProductorRequest,
    MaterialResponse,
    ProductorResponse,
)
from app.modulos.catalogos.service import CatalogosService

# Todos los endpoints del módulo requieren usuario autenticado.
router = APIRouter(
    prefix="/catalogos",
    tags=["Catálogos"],
    dependencies=[Depends(obtener_usuario_actual)],
)

Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]


@router.get(
    "/productores", response_model=list[ProductorResponse], operation_id="listar_productores"
)
async def listar_productores(sesion: Sesion) -> list[ProductorResponse]:
    """Lista los productores con sus campos."""
    return await CatalogosService(sesion).listar_productores()


@router.post(
    "/productores",
    response_model=ProductorResponse,
    status_code=201,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="crear_productor",
)
async def crear_productor(datos: CrearProductorRequest, sesion: Sesion) -> ProductorResponse:
    """Da de alta un productor con sus campos iniciales. Solo administradores."""
    return await CatalogosService(sesion).crear_productor(datos)


@router.post(
    "/productores/{productor_id}/campos",
    response_model=ProductorResponse,
    status_code=201,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="agregar_campo",
)
async def agregar_campo(
    productor_id: str, datos: CrearCampoRequest, sesion: Sesion
) -> ProductorResponse:
    """Agrega un campo a un productor existente. Solo administradores."""
    return await CatalogosService(sesion).agregar_campo(productor_id, datos)


@router.get(
    "/materiales", response_model=list[MaterialResponse], operation_id="listar_materiales"
)
async def listar_materiales(sesion: Sesion) -> list[MaterialResponse]:
    """Lista los materiales (granos) disponibles."""
    return await CatalogosService(sesion).listar_materiales()


@router.post(
    "/materiales",
    response_model=MaterialResponse,
    status_code=201,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="crear_material",
)
async def crear_material(datos: CrearMaterialRequest, sesion: Sesion) -> MaterialResponse:
    """Da de alta un material. Solo administradores."""
    return await CatalogosService(sesion).crear_material(datos)


@router.get("/choferes", response_model=list[ChoferResponse], operation_id="listar_choferes")
async def listar_choferes(sesion: Sesion) -> list[ChoferResponse]:
    """Lista los choferes activos con su dominio (patente)."""
    return await CatalogosService(sesion).listar_choferes()


@router.post(
    "/choferes",
    response_model=ChoferResponse,
    status_code=201,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="crear_chofer",
)
async def crear_chofer(datos: CrearChoferRequest, sesion: Sesion) -> ChoferResponse:
    """Da de alta un chofer. Solo administradores."""
    return await CatalogosService(sesion).crear_chofer(datos)
