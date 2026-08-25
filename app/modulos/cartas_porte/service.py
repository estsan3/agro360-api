"""Capa SERVICE del módulo cartas de porte.

Arma y persiste la intención con el payload AFIP completo. El envío a
ARCA (homologación o producción) ocurre en `enviar`, vía el puerto CPE.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.eventos import EventoDominio, bus_eventos
from app.core.excepciones import ErrorDeNegocio, RecursoNoEncontrado, ReglaDeNegocioViolada
from app.modulos.cartas_porte.adaptadores import crear_proveedor_cpe
from app.modulos.cartas_porte.bo import CartaPorteBO
from app.modulos.cartas_porte.dao import CartaPorteDAO
from app.modulos.cartas_porte.models import CartaPorte
from app.modulos.cartas_porte.puerto import ProveedorCPE, SolicitudCPE
from app.modulos.cartas_porte.schemas import CartaPorteResponse, EmitirCartaPorteRequest
from app.modulos.catalogos.contrato import CatalogosLocal, ContratoCatalogos
from app.modulos.despachos.contrato import ContratoDespachos, DespachosLocal


class CartasPorteService:
    """Casos de uso de intenciones de CPE."""

    def __init__(
        self,
        sesion: AsyncSession,
        despachos: ContratoDespachos | None = None,
        catalogos: ContratoCatalogos | None = None,
        proveedor: ProveedorCPE | None = None,
    ) -> None:
        self._sesion = sesion
        self._dao = CartaPorteDAO(sesion)
        self._bo = CartaPorteBO()
        self._despachos = despachos or DespachosLocal(sesion)
        self._catalogos = catalogos or CatalogosLocal(sesion)
        self._proveedor = proveedor or crear_proveedor_cpe()

    async def crear_intencion(self, datos: EmitirCartaPorteRequest) -> CartaPorteResponse:
        """Arma el payload AFIP completo y lo guarda como intención pendiente."""
        cpe_datos = await self._despachos.obtener_datos_cpe(
            datos.despacho_id, datos.viaje_id
        )
        if cpe_datos is None:
            raise RecursoNoEncontrado("Viaje no encontrado en esa campaña")

        vigente = await self._dao.buscar_vigente_por_viaje(cpe_datos.viaje_id)
        self._bo.validar_creacion_intencion(cpe_datos, vigente)

        payload = await self._armar_payload(cpe_datos)
        carta = CartaPorte(
            despacho_id=cpe_datos.despacho_id,
            viaje_id=cpe_datos.viaje_id,
            tipo_cpe=int(payload["tipo_cpe"]),
            estado="pendiente",
            material=cpe_datos.material,
            origen=cpe_datos.origen,
            destino=cpe_datos.destino,
            dominio=cpe_datos.dominio,
            toneladas=cpe_datos.toneladas,
            payload_afip=payload,
            intentos=0,
            error_detalle="",
        )
        await self._dao.guardar(carta)
        await self._sesion.commit()

        await bus_eventos.publicar(
            EventoDominio(
                nombre="cartas_porte.intencion.creada",
                datos={
                    "carta_id": carta.id,
                    "viaje_id": carta.viaje_id,
                    "tipo_cpe": carta.tipo_cpe,
                },
            )
        )
        return self._a_response(carta)

    async def reintentar(self, carta_id: str) -> CartaPorteResponse:
        """Reconstruye el payload desde despacho/viaje actuales y deja pendiente."""
        carta = await self._dao.buscar_por_id(carta_id)
        if carta is None:
            raise RecursoNoEncontrado("Carta de porte no encontrada")
        self._bo.validar_reintento(carta)
        nro_orden = self._bo.nro_orden_de_payload(carta)

        cpe_datos = await self._despachos.obtener_datos_cpe(
            carta.despacho_id, carta.viaje_id
        )
        if cpe_datos is None:
            raise RecursoNoEncontrado("Viaje asociado ya no existe")

        try:
            payload = await self._armar_payload(cpe_datos)
            if nro_orden is not None:
                payload["nro_orden"] = nro_orden
            carta.payload_afip = payload
            carta.tipo_cpe = int(payload["tipo_cpe"])
            carta.material = cpe_datos.material
            carta.origen = cpe_datos.origen
            carta.destino = cpe_datos.destino
            carta.dominio = cpe_datos.dominio
            carta.toneladas = cpe_datos.toneladas
            carta.estado = "pendiente"
            carta.error_detalle = ""
        except ErrorDeNegocio as exc:
            carta.estado = "error"
            carta.error_detalle = exc.mensaje
            carta.intentos += 1
            carta.actualizada_en = datetime.now(UTC)
            await self._sesion.commit()
            raise
        carta.intentos += 1
        carta.actualizada_en = datetime.now(UTC)
        await self._sesion.commit()
        return self._a_response(carta)

    async def enviar(self, carta_id: str) -> CartaPorteResponse:
        """Impacta la intención pendiente en ARCA (o en el adaptador simulado)."""
        carta = await self._dao.buscar_por_id(carta_id)
        if carta is None:
            raise RecursoNoEncontrado("Carta de porte no encontrada")
        self._bo.validar_envio(carta)

        nro_orden = self._bo.nro_orden_de_payload(carta)
        if nro_orden is None:
            sucursal = int((carta.payload_afip or {}).get("sucursal") or 1)
            nro_orden = await self._dao.proximo_nro_orden(sucursal)
            payload = dict(carta.payload_afip or {})
            payload["nro_orden"] = nro_orden
            carta.payload_afip = payload

        resultado = await self._proveedor.autorizar_cpe_automotor(
            SolicitudCPE(payload=carta.payload_afip or {}, nro_orden=nro_orden)
        )
        carta.intentos += 1
        carta.actualizada_en = datetime.now(UTC)

        if resultado.autorizada:
            carta.estado = "procesada"
            carta.nro_carta_porte = resultado.nro_carta_porte
            carta.nro_ctg = resultado.nro_ctg
            carta.pdf_base64 = resultado.pdf_base64
            carta.error_detalle = resultado.error or ""
            await self._sesion.commit()
            await bus_eventos.publicar(
                EventoDominio(
                    nombre="cartas_porte.cpe.autorizada",
                    datos={
                        "carta_id": carta.id,
                        "viaje_id": carta.viaje_id,
                        "nro_ctg": carta.nro_ctg,
                    },
                )
            )
            return self._a_response(carta)

        carta.estado = "error"
        carta.error_detalle = resultado.error or "ARCA rechazó la autorización"
        await self._sesion.commit()
        raise ReglaDeNegocioViolada(carta.error_detalle)

    async def anular(self, carta_id: str) -> CartaPorteResponse:
        carta = await self._dao.buscar_por_id(carta_id)
        if carta is None:
            raise RecursoNoEncontrado("Carta de porte no encontrada")
        self._bo.validar_anulacion(carta)
        nro_orden = self._bo.nro_orden_de_payload(carta)
        sucursal = int((carta.payload_afip or {}).get("sucursal") or 1)
        if nro_orden is None:
            raise ReglaDeNegocioViolada(
                "La CPE no tiene nro_orden; no se puede anular en ARCA"
            )

        resultado = await self._proveedor.anular_cpe(
            tipo_cpe=carta.tipo_cpe, sucursal=sucursal, nro_orden=nro_orden
        )
        carta.intentos += 1
        carta.actualizada_en = datetime.now(UTC)
        if not resultado.autorizada:
            carta.error_detalle = resultado.error or "ARCA rechazó la anulación"
            await self._sesion.commit()
            raise ReglaDeNegocioViolada(carta.error_detalle)

        carta.estado = "anulada"
        carta.error_detalle = ""
        await self._sesion.commit()
        await bus_eventos.publicar(
            EventoDominio(
                nombre="cartas_porte.cpe.anulada",
                datos={"carta_id": carta.id, "nro_ctg": carta.nro_ctg},
            )
        )
        return self._a_response(carta)

    async def eliminar(self, carta_id: str) -> None:
        carta = await self._dao.buscar_por_id(carta_id)
        if carta is None:
            raise RecursoNoEncontrado("Carta de porte no encontrada")
        self._bo.validar_eliminacion(carta)
        await self._dao.eliminar(carta)
        await self._sesion.commit()

    async def listar(self, despacho_id: str | None = None) -> list[CartaPorteResponse]:
        cartas = await self._dao.listar(despacho_id)
        return [self._a_response(c) for c in cartas]

    async def obtener(self, carta_id: str) -> CartaPorteResponse:
        carta = await self._dao.buscar_por_id(carta_id)
        if carta is None:
            raise RecursoNoEncontrado("Carta de porte no encontrada")
        return self._a_response(carta)

    async def obtener_documento(self, carta_id: str) -> tuple[bytes, str]:
        """Devuelve (contenido_pdf, nombre_archivo) de una CPE procesada."""
        carta = await self._dao.buscar_por_id(carta_id)
        if carta is None:
            raise RecursoNoEncontrado("Carta de porte no encontrada")
        self._bo.validar_documento(carta)
        assert carta.pdf_base64 is not None
        contenido = base64.b64decode(carta.pdf_base64)
        nombre = f"cpe_{carta.nro_ctg or carta.id}.pdf"
        return contenido, nombre

    async def emitir(self, datos: EmitirCartaPorteRequest) -> CartaPorteResponse:
        return await self.crear_intencion(datos)

    async def _armar_payload(self, cpe_datos):
        contexto = await self._catalogos.obtener_contexto_cpe(
            productor_id=cpe_datos.productor_id,
            campo_id=cpe_datos.campo_id,
            material_nombre=cpe_datos.material,
            chofer_id=cpe_datos.chofer_id,
            entrada_campo=cpe_datos.entrada_campo,
        )
        return self._bo.armar_payload(cpe_datos, contexto)

    @staticmethod
    def _a_response(carta: CartaPorte) -> CartaPorteResponse:
        tiene_documento = bool(
            carta.pdf_base64 and carta.estado in CartaPorteBO.ESTADOS_CON_DOCUMENTO
        )
        return CartaPorteResponse(
            id=carta.id,
            despacho_id=carta.despacho_id,
            viaje_id=carta.viaje_id,
            tipo_cpe=carta.tipo_cpe,
            nro_carta_porte=carta.nro_carta_porte,
            nro_ctg=carta.nro_ctg,
            estado=carta.estado,  # type: ignore[arg-type]
            material=carta.material,
            origen=carta.origen,
            destino=carta.destino,
            dominio=carta.dominio,
            toneladas=carta.toneladas,
            payload_afip=carta.payload_afip or {},
            intentos=carta.intentos,
            error_detalle=carta.error_detalle or "",
            tiene_documento=tiene_documento,
            creada_en=carta.creada_en,
            actualizada_en=carta.actualizada_en,
        )
