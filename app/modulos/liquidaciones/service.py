"""Casos de uso de liquidaciones / cuenta corriente."""

from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excepciones import RecursoNoEncontrado, ReglaDeNegocioViolada
from app.modulos.catalogos.contrato import CatalogosLocal, ContratoCatalogos
from app.modulos.despachos.contrato import ContratoDespachos, DespachosLocal
from app.modulos.liquidaciones.bo import LiquidacionesBO
from app.modulos.liquidaciones.dao import LiquidacionesDAO
from app.modulos.liquidaciones.models import MovimientoCtacte
from app.modulos.liquidaciones.schemas import (
    ActualizarMovimientoRequest,
    CrearFleteRequest,
    CrearMovimientoManualRequest,
    CuentaResumenItem,
    MovimientoResponse,
    ParametrosLiquidacion,
    ResumenCuentaResponse,
)

_DEFAULTS = ParametrosLiquidacion(
    tarifa_flete_por_tn=15000.0,
    comision_porcentaje=8.0,
    iva_alicuota=21.0,
    # Ley 25.413: alícuota general 6‰ (= 0,6 %). Parametrizable si el negocio usa otra.
    ley_25413_porcentaje=0.6,
    nombre_transportadora="Transportadora",
)

_DETALLE_CONCEPTO = {
    "flete": "Flete",
    "iva_flete": "IVA Flete",
    "comision": "Comisión",
    "iva_comision": "IVA Comisión",
    "ley_25413": "Imp. Ley 25413",
    "gasoil": "Factura de gasoil",
    "transferencia": "Transferencia",
    "cheque": "Cheque",
    "anticipo": "Anticipo",
    "ajuste": "Ajuste",
}

_PREF_COMPROBANTE = {
    "flete": "FL",
    "iva_flete": "IV",
    "comision": "CO",
    "iva_comision": "IC",
    "ley_25413": "IL",
    "gasoil": "AN",
    "transferencia": "EF",
    "cheque": "CH",
    "anticipo": "AD",
    "ajuste": "AJ",
}


class LiquidacionesService:
    def __init__(
        self,
        sesion: AsyncSession,
        catalogos: ContratoCatalogos | None = None,
        despachos: ContratoDespachos | None = None,
    ) -> None:
        self._sesion = sesion
        self._dao = LiquidacionesDAO(sesion)
        self._bo = LiquidacionesBO()
        self._catalogos = catalogos or CatalogosLocal(sesion)
        self._despachos = despachos or DespachosLocal(sesion)

    async def obtener_parametros(self) -> ParametrosLiquidacion:
        valores = await self._dao.obtener_parametros()
        return ParametrosLiquidacion(
            tarifa_flete_por_tn=float(
                valores.get("tarifa_flete_por_tn", _DEFAULTS.tarifa_flete_por_tn)
            ),
            comision_porcentaje=float(
                valores.get("comision_porcentaje", _DEFAULTS.comision_porcentaje)
            ),
            iva_alicuota=float(valores.get("iva_alicuota", _DEFAULTS.iva_alicuota)),
            ley_25413_porcentaje=float(
                valores.get("ley_25413_porcentaje", _DEFAULTS.ley_25413_porcentaje)
            ),
            nombre_transportadora=valores.get(
                "nombre_transportadora", _DEFAULTS.nombre_transportadora
            ),
        )

    async def guardar_parametros(self, datos: ParametrosLiquidacion) -> ParametrosLiquidacion:
        await self._dao.guardar_parametros(
            {
                "tarifa_flete_por_tn": str(datos.tarifa_flete_por_tn),
                "comision_porcentaje": str(datos.comision_porcentaje),
                "iva_alicuota": str(datos.iva_alicuota),
                "ley_25413_porcentaje": str(datos.ley_25413_porcentaje),
                "nombre_transportadora": datos.nombre_transportadora,
            }
        )
        await self._sesion.commit()
        return datos

    async def registrar_viaje_completado(self, despacho_id: str, viaje_id: str) -> int:
        """Genera movimientos de flete. Idempotente. Devuelve cantidad insertada."""
        if await self._dao.existe_flete_para_viaje(viaje_id):
            return 0

        viaje = await self._despachos.obtener_viaje(despacho_id, viaje_id)
        if viaje is None or not viaje.chofer_id:
            return 0

        chofer = await self._catalogos.obtener_chofer(viaje.chofer_id)
        if chofer is None or not chofer.transportista_id:
            return 0

        params = await self.obtener_parametros()
        movimientos = self._armar_movimientos_flete(
            transportista_id=chofer.transportista_id,
            toneladas=viaje.toneladas,
            tarifa=params.tarifa_flete_por_tn,
            detalle_flete=f"Flete: {viaje.destino}",
            dador_viaje=viaje.origen or viaje.material,
            fecha=date.today(),
            viaje_id=viaje_id,
            despacho_id=despacho_id,
            params=params,
            sufijo_comprobante=viaje_id.replace("-", "")[:8].upper(),
        )
        await self._dao.guardar_movimientos(movimientos)
        await self._sesion.commit()
        return len(movimientos)

    async def registrar_flete(self, datos: CrearFleteRequest) -> list[MovimientoResponse]:
        """
        Alta de flete con generación automática:
        - HABER (a favor del transportista): flete + IVA flete
        - DEBE (cargo de la transportadora): comisión + IVA comisión + Imp. Ley 25.413
        """
        nombre = await self._catalogos.obtener_nombre_transportista(datos.transportista_id)
        if nombre is None:
            raise RecursoNoEncontrado("Transportista no encontrado")
        if datos.viaje_id and await self._dao.existe_flete_para_viaje(datos.viaje_id):
            raise ReglaDeNegocioViolada("Ya existe un flete liquidado para ese viaje")

        params = await self.obtener_parametros()
        tarifa = datos.tarifa if datos.tarifa is not None else params.tarifa_flete_por_tn
        fecha = datos.fecha or date.today()
        sufijo = (datos.viaje_id or datetime.utcnow().strftime("%y%m%d%H%M")).replace("-", "")[
            :8
        ].upper()
        movimientos = self._armar_movimientos_flete(
            transportista_id=datos.transportista_id,
            toneladas=datos.toneladas,
            tarifa=tarifa,
            detalle_flete=datos.detalle,
            dador_viaje=datos.dador_viaje,
            fecha=fecha,
            viaje_id=datos.viaje_id,
            despacho_id=datos.despacho_id,
            params=params,
            sufijo_comprobante=sufijo,
        )
        await self._dao.guardar_movimientos(movimientos)
        await self._sesion.commit()
        saldo = await self._dao.saldo_actual(datos.transportista_id)
        return [
            MovimientoResponse(
                id=m.id,
                transportista_id=m.transportista_id,
                fecha=m.fecha,
                concepto=m.concepto,
                comprobante=m.comprobante,
                detalle=m.detalle,
                dador_viaje=m.dador_viaje,
                toneladas=m.toneladas,
                tarifa=m.tarifa,
                debe=m.debe,
                haber=m.haber,
                saldo=saldo,
                viaje_id=m.viaje_id,
                despacho_id=m.despacho_id,
                creado_en=m.creado_en,
            )
            for m in movimientos
        ]

    def _armar_movimientos_flete(
        self,
        *,
        transportista_id: str,
        toneladas: float,
        tarifa: float,
        detalle_flete: str,
        dador_viaje: str,
        fecha: date,
        viaje_id: str | None,
        despacho_id: str | None,
        params: ParametrosLiquidacion,
        sufijo_comprobante: str,
    ) -> list[MovimientoCtacte]:
        lineas = self._bo.calcular_movimientos_flete(
            toneladas=toneladas,
            tarifa=tarifa,
            comision_pct=params.comision_porcentaje,
            iva_pct=params.iva_alicuota,
            ley_pct=params.ley_25413_porcentaje,
        )
        movimientos: list[MovimientoCtacte] = []
        for concepto, debe, haber in lineas:
            pref = _PREF_COMPROBANTE[concepto]
            base = _DETALLE_CONCEPTO[concepto]
            detalle = detalle_flete if concepto == "flete" else base
            movimientos.append(
                MovimientoCtacte(
                    transportista_id=transportista_id,
                    fecha=fecha,
                    concepto=concepto,
                    comprobante=f"{pref}-{sufijo_comprobante}",
                    detalle=detalle,
                    dador_viaje=dador_viaje,
                    toneladas=toneladas if concepto == "flete" else None,
                    tarifa=tarifa if concepto == "flete" else None,
                    debe=debe,
                    haber=haber,
                    viaje_id=viaje_id,
                    despacho_id=despacho_id,
                )
            )
        return movimientos

    async def listar_resumen(
        self,
        transportista_id: str,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> ResumenCuentaResponse:
        nombre = await self._catalogos.obtener_nombre_transportista(transportista_id)
        if nombre is None:
            raise RecursoNoEncontrado("Transportista no encontrado")

        saldo_inicial = 0.0
        if desde is not None:
            saldo_inicial = await self._dao.saldo_antes_de(transportista_id, desde)

        filas = await self._dao.listar_por_transportista(transportista_id, desde, hasta)
        saldos = self._bo.calcular_saldo_corrido(
            saldo_inicial, [(m.debe, m.haber) for m in filas]
        )
        movimientos = [
            MovimientoResponse(
                id=m.id,
                transportista_id=m.transportista_id,
                fecha=m.fecha,
                concepto=m.concepto,
                comprobante=m.comprobante,
                detalle=m.detalle,
                dador_viaje=m.dador_viaje,
                toneladas=m.toneladas,
                tarifa=m.tarifa,
                debe=m.debe,
                haber=m.haber,
                saldo=saldos[i] if i < len(saldos) else saldo_inicial,
                viaje_id=m.viaje_id,
                despacho_id=m.despacho_id,
                creado_en=m.creado_en,
            )
            for i, m in enumerate(filas)
        ]
        totales_debe = round(sum(m.debe for m in filas), 2)
        totales_haber = round(sum(m.haber for m in filas), 2)
        saldo_final = saldos[-1] if saldos else saldo_inicial
        return ResumenCuentaResponse(
            transportista_id=transportista_id,
            transportista_nombre=nombre,
            desde=desde,
            hasta=hasta,
            saldo_inicial=round(saldo_inicial, 2),
            saldo_final=round(saldo_final, 2),
            totales_debe=totales_debe,
            totales_haber=totales_haber,
            movimientos=movimientos,
        )

    async def crear_movimiento_manual(
        self, datos: CrearMovimientoManualRequest
    ) -> MovimientoResponse:
        self._bo.validar_movimiento_manual(datos.concepto, datos.debe, datos.haber)
        nombre = await self._catalogos.obtener_nombre_transportista(datos.transportista_id)
        if nombre is None:
            raise RecursoNoEncontrado("Transportista no encontrado")

        fecha = datos.fecha or date.today()
        pref = _PREF_COMPROBANTE[datos.concepto]
        movimiento = MovimientoCtacte(
            transportista_id=datos.transportista_id,
            fecha=fecha,
            concepto=datos.concepto,
            comprobante=f"{pref}-{datetime.utcnow().strftime('%y%m%d%H%M')}",
            detalle=datos.detalle or _DETALLE_CONCEPTO[datos.concepto],
            dador_viaje=datos.dador_viaje,
            toneladas=datos.toneladas,
            debe=datos.debe,
            haber=datos.haber,
        )
        await self._dao.guardar_movimiento(movimiento)
        await self._sesion.commit()
        return await self._a_response(movimiento)

    async def actualizar_movimiento(
        self, movimiento_id: str, datos: ActualizarMovimientoRequest
    ) -> MovimientoResponse:
        movimiento = await self._dao.obtener_por_id(movimiento_id)
        if movimiento is None:
            raise RecursoNoEncontrado("Movimiento no encontrado")
        if (datos.debe > 0) == (datos.haber > 0):
            raise ReglaDeNegocioViolada(
                "El movimiento debe tener importe en debe o en haber, no en ambos"
            )

        movimiento.fecha = datos.fecha
        movimiento.detalle = datos.detalle
        movimiento.dador_viaje = datos.dador_viaje
        movimiento.comprobante = datos.comprobante
        movimiento.toneladas = datos.toneladas
        movimiento.tarifa = datos.tarifa
        movimiento.debe = datos.debe
        movimiento.haber = datos.haber
        await self._sesion.flush()
        await self._sesion.commit()
        return await self._a_response(movimiento)

    async def eliminar_movimiento(self, movimiento_id: str) -> None:
        movimiento = await self._dao.obtener_por_id(movimiento_id)
        if movimiento is None:
            raise RecursoNoEncontrado("Movimiento no encontrado")
        await self._dao.eliminar(movimiento)
        await self._sesion.commit()

    async def _a_response(self, movimiento: MovimientoCtacte) -> MovimientoResponse:
        saldo = await self._dao.saldo_actual(movimiento.transportista_id)
        return MovimientoResponse(
            id=movimiento.id,
            transportista_id=movimiento.transportista_id,
            fecha=movimiento.fecha,
            concepto=movimiento.concepto,
            comprobante=movimiento.comprobante,
            detalle=movimiento.detalle,
            dador_viaje=movimiento.dador_viaje,
            toneladas=movimiento.toneladas,
            tarifa=movimiento.tarifa,
            debe=movimiento.debe,
            haber=movimiento.haber,
            saldo=saldo,
            viaje_id=movimiento.viaje_id,
            despacho_id=movimiento.despacho_id,
            creado_en=movimiento.creado_en,
        )

    async def listar_cuentas(self) -> list[CuentaResumenItem]:
        ids = await self._dao.listar_transportista_ids()
        cuentas: list[CuentaResumenItem] = []
        for tid in ids:
            nombre = await self._catalogos.obtener_nombre_transportista(tid)
            cuentas.append(
                CuentaResumenItem(
                    transportista_id=tid,
                    transportista_nombre=nombre or tid,
                    saldo_actual=round(await self._dao.saldo_actual(tid), 2),
                    cantidad_movimientos=await self._dao.contar_movimientos(tid),
                )
            )
        return sorted(cuentas, key=lambda c: c.transportista_nombre.lower())
