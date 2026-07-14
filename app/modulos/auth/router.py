"""Capa API del módulo auth: endpoints HTTP. Sin lógica de negocio."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.core.dependencias import UsuarioActual, obtener_usuario_actual, requerir_rol
from app.modulos.auth.schemas import (
    CrearUsuarioRequest,
    LoginRequest,
    LoginResponse,
    UsuarioResponse,
)
from app.modulos.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticación"])

# Alias para inyectar la sesión de base de datos en cada endpoint.
Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]


@router.post("/login", response_model=LoginResponse, operation_id="login")
async def login(datos: LoginRequest, sesion: Sesion) -> LoginResponse:
    """Inicia sesión y devuelve un token JWT junto con los datos del usuario."""
    return await AuthService(sesion).login(datos)


@router.get("/me", response_model=UsuarioResponse, operation_id="obtener_perfil")
async def perfil(
    usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)],
    sesion: Sesion,
) -> UsuarioResponse:
    """Devuelve el perfil del usuario autenticado (según el token)."""
    return await AuthService(sesion).obtener_usuario(usuario.id)


@router.get(
    "/usuarios",
    response_model=list[UsuarioResponse],
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="listar_usuarios",
)
async def listar_usuarios(sesion: Sesion) -> list[UsuarioResponse]:
    """Lista los usuarios del backoffice. Solo administradores."""
    return await AuthService(sesion).listar_usuarios()


@router.post(
    "/usuarios",
    response_model=UsuarioResponse,
    status_code=201,
    dependencies=[Depends(requerir_rol("administrador"))],
    operation_id="crear_usuario",
)
async def crear_usuario(datos: CrearUsuarioRequest, sesion: Sesion) -> UsuarioResponse:
    """Da de alta un usuario (administrador o vendedor). Solo administradores."""
    return await AuthService(sesion).crear_usuario(datos)
