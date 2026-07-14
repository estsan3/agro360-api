"""Capa SERVICE del módulo cartas de porte.

Orquesta: contrato de despachos (datos del viaje) + BO (reglas) +
puerto ProveedorCPE (ARCA/AFIP o simulado) + DAO (registro local).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.eventos import EventoDominio, bus_eventos
from app.core.excepciones import RecursoNoEncontrado
from app.modulos.cartas_porte.adaptadores.simulado import AdaptadorSimulado
from app.modulos.cartas_porte.bo import CartaPorteBO
from app.modulos.cartas_porte.dao import CartaPorteDAO
from app.modulos.cartas_porte.models import CartaPorte
from app.modulos.cartas_porte.puerto import ProveedorCPE, SolicitudCPE
from app.modulos.cartas_porte.schemas import CartaPorteResponse, EmitirCartaPorteRequest
from app.modulos.despachos.contrato import ContratoDespachos, DespachosLocal


class CartasPorteService:
    """Casos de uso de emisión y gestión de CPE."""

    def __init__(
        self,
        sesion: AsyncSession,
        proveedor: ProveedorCPE | None = None,
        despachos: ContratoDespachos | None = None,
    ) -> None:
        self._sesion = sesion
        self._dao = CartaPorteDAO(sesion)
        self._bo = CartaPorteBO()
        # Default: adaptador simulado. Cuando haya certificado de ARCA se
        # inyecta AdaptadorAfip desde la configuración, sin tocar este código.
        self._proveedor = proveedor or AdaptadorSimulado()
        self._despachos = despachos or DespachosLocal(sesion)

    async def emitir(self, datos: EmitirCartaPorteRequest) -> CartaPorteResponse:
        """Emite una CPE para un viaje: valida, llama al proveedor y registra."""
        viaje = await self._despachos.obtener_viaje(datos.despacho_id, datos.viaje_id)
        if viaje is None:
            raise RecursoNoEncontrado("Viaje no encontrado en esa campaña")

        cpe_vigente = await self._dao.buscar_autorizada_por_viaje(viaje.id)
        self._bo.validar_emision(viaje, cpe_vigente)

        # Llamada al proveedor (ARCA/AFIP real o simulado según inyección).
        resultado = await self._proveedor.autorizar_cpe_automotor(
            SolicitudCPE(
                material=viaje.material,
                origen=viaje.origen,
                destino=viaje.destino,
                dominio=viaje.dominio,
                toneladas=viaje.toneladas,
            )
        )

        # Registramos el intento (autorizado o rechazado) para auditoría.
        carta = CartaPorte(
            despacho_id=viaje.despacho_id,
            viaje_id=viaje.id,
            nro_carta_porte=resultado.nro_carta_porte,
            nro_ctg=resultado.nro_ctg,
            estado="autorizada" if resultado.autorizada else "rechazada",
            material=viaje.material,
            origen=viaje.origen,
            destino=viaje.destino,
            dominio=viaje.dominio,
            toneladas=viaje.toneladas,
            error_detalle=resultado.error,
        )
        await self._dao.guardar(carta)
        await self._sesion.commit()

        if resultado.autorizada:
            await bus_eventos.publicar(
                EventoDominio(
                    nombre="cartas_porte.cpe.autorizada",
                    datos={
                        "carta_id": carta.id,
                        "viaje_id": viaje.id,
                        "nro_ctg": carta.nro_ctg,
                    },
                )
            )
        return CartaPorteResponse.model_validate(carta)

    async def anular(self, carta_id: str) -> CartaPorteResponse:
        """Anula una CPE autorizada ante el proveedor y en el registro local."""
        carta = await self._dao.buscar_por_id(carta_id)
        if carta is None:
            raise RecursoNoEncontrado("Carta de porte no encontrada")
        self._bo.validar_anulacion(carta)

        assert carta.nro_carta_porte is not None  # Garantizado por validar_anulacion.
        resultado = await self._proveedor.anular_cpe(carta.nro_carta_porte)
        if resultado.autorizada:
            carta.estado = "anulada"
        else:
            carta.error_detalle = resultado.error
        await self._sesion.commit()
        return CartaPorteResponse.model_validate(carta)

    async def listar(self, despacho_id: str | None = None) -> list[CartaPorteResponse]:
        cartas = await self._dao.listar(despacho_id)
        return [CartaPorteResponse.model_validate(c) for c in cartas]

    async def obtener(self, carta_id: str) -> CartaPorteResponse:
        carta = await self._dao.buscar_por_id(carta_id)
        if carta is None:
            raise RecursoNoEncontrado("Carta de porte no encontrada")
        return CartaPorteResponse.model_validate(carta)
