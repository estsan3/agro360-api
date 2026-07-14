"""Capa API del módulo reportería."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.core.dependencias import obtener_usuario_actual
from app.modulos.reporteria.schemas import KpisResponse
from app.modulos.reporteria.service import ReporteriaService

router = APIRouter(
    prefix="/reporteria",
    tags=["Reportería"],
    dependencies=[Depends(obtener_usuario_actual)],
)

Sesion = Annotated[AsyncSession, Depends(obtener_sesion)]


@router.get("/kpis", response_model=KpisResponse, operation_id="obtener_kpis")
async def obtener_kpis(sesion: Sesion) -> KpisResponse:
    """KPIs del dashboard: campañas activas, viajes, toneladas y valorización."""
    return await ReporteriaService(sesion).obtener_kpis()
