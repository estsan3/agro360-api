"""Capa SERVICE del módulo parámetros.

Módulo sin BO: los parámetros no tienen reglas de negocio más allá de la
validación de tipos, que ya la hacen los schemas Pydantic.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modulos.parametros.dao import ParametrosDAO
from app.modulos.parametros.schemas import ParametrosNegocio, PreferenciasNotificacion

# Valores por defecto si la base todavía no tiene nada guardado.
_DEFAULTS_NEGOCIO = ParametrosNegocio(precio_por_tonelada=50000.0, moneda="ARS")
_DEFAULTS_PREFERENCIAS = PreferenciasNotificacion(
    viaje_retrasado=True, viaje_completado=True, mensaje_chofer=True
)


class ParametrosService:
    """Casos de uso de configuración global."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion
        self._dao = ParametrosDAO(sesion)

    async def obtener_negocio(self) -> ParametrosNegocio:
        valores = await self._dao.obtener_todos()
        return ParametrosNegocio(
            precio_por_tonelada=float(
                valores.get("precio_por_tonelada", _DEFAULTS_NEGOCIO.precio_por_tonelada)
            ),
            moneda=valores.get("moneda", _DEFAULTS_NEGOCIO.moneda),  # type: ignore[arg-type]
        )

    async def guardar_negocio(self, datos: ParametrosNegocio) -> ParametrosNegocio:
        await self._dao.guardar_varios(
            {
                "precio_por_tonelada": str(datos.precio_por_tonelada),
                "moneda": datos.moneda,
            }
        )
        await self._sesion.commit()
        return datos

    async def obtener_preferencias(self) -> PreferenciasNotificacion:
        valores = await self._dao.obtener_todos()

        def _leer_bool(clave: str, default: bool) -> bool:
            return valores.get(clave, str(default)).lower() == "true"

        return PreferenciasNotificacion(
            viaje_retrasado=_leer_bool("notif_viaje_retrasado", True),
            viaje_completado=_leer_bool("notif_viaje_completado", True),
            mensaje_chofer=_leer_bool("notif_mensaje_chofer", True),
        )

    async def guardar_preferencias(
        self, datos: PreferenciasNotificacion
    ) -> PreferenciasNotificacion:
        await self._dao.guardar_varios(
            {
                "notif_viaje_retrasado": str(datos.viaje_retrasado),
                "notif_viaje_completado": str(datos.viaje_completado),
                "notif_mensaje_chofer": str(datos.mensaje_chofer),
            }
        )
        await self._sesion.commit()
        return datos
