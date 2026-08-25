"""Contrato público del módulo despachos.

Lo consumen reportería (métricas) y cartas de porte (datos del viaje).
Al extraer despachos como microservicio, se implementa este mismo
Protocol con un cliente HTTP.
"""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.modulos.despachos.dao import DespachoDAO


@dataclass(frozen=True)
class ViajeResumen:
    """Datos de un viaje que otros módulos necesitan (ej: para la carta de porte)."""

    id: str
    despacho_id: str
    chofer_id: str | None
    chofer_nombre: str
    dominio: str
    destino: str
    toneladas: float
    estado: str
    material: str
    origen: str


@dataclass(frozen=True)
class DatosCpeDespacho:
    """Todo lo que cartas_porte necesita de la campaña + viaje para armar el payload."""

    viaje_id: str
    despacho_id: str
    despacho_nombre: str
    estado_viaje: str
    chofer_id: str | None
    chofer_nombre: str
    dominio: str
    destino: str
    toneladas: float
    observaciones: str
    material: str
    origen: str
    productor_id: str
    campo_id: str
    entrada_campo: str
    distancia_km: float | None
    tarifa_por_tn: float | None
    fecha_inicio: date
    cuando: str
    cuando_fecha: date | None

    cpe_habilitada: bool
    cpe_tipo: int | None
    cpe_sucursal: int | None
    cpe_cosecha: int | None
    cpe_cuit_solicitante: str | None
    cpe_origen_cod_provincia: int | None
    cpe_origen_cod_localidad: int | None
    cpe_origen_planta: int | None
    cpe_nro_renspa: str | None
    cpe_codigo_turno: str | None
    cpe_hora_partida: str | None
    cpe_corresponde_retiro_productor: bool
    cpe_es_solicitante_campo: bool
    cpe_destino_cuit: str | None
    cpe_destino_es_campo: bool
    cpe_destino_cod_provincia: int | None
    cpe_destino_cod_localidad: int | None
    cpe_destino_planta: int | None
    cpe_peso_tara_kg_default: int | None
    cpe_mercaderia_fumigada: bool
    cpe_cuit_pagador_flete: str | None
    cpe_cuit_intermediario_flete: str | None
    cpe_cuit_remitente_comercial_vp: str | None
    cpe_cuit_remitente_comercial_vs: str | None
    cpe_cuit_mercado_a_termino: str | None
    cpe_cuit_corredor_vp: str | None
    cpe_cuit_corredor_vs: str | None
    cpe_cuit_representante_entregador: str | None
    cpe_cuit_representante_recibidor: str | None
    cpe_cuit_remitente_comercial_vs2: str | None
    cpe_cuit_remitente_comercial_productor: str | None

    viaje_cpe_destino_cuit: str | None
    viaje_cpe_destino_es_campo: bool | None
    viaje_cpe_destino_cod_provincia: int | None
    viaje_cpe_destino_cod_localidad: int | None
    viaje_cpe_destino_planta: int | None
    viaje_cpe_peso_bruto_kg: int | None
    viaje_cpe_peso_tara_kg: int | None
    viaje_cpe_codigo_turno: str | None
    viaje_cpe_dominio_acoplado: str | None


@dataclass(frozen=True)
class MetricasDespachos:
    """Números agregados para reportería / dashboard."""

    campanias_activas: int
    viajes_totales: int
    viajes_completados: int
    viajes_en_curso: int
    viajes_retrasados: int
    toneladas_totales: float
    toneladas_completadas: float


class ContratoDespachos(Protocol):
    """Interfaz que despachos garantiza al resto del sistema."""

    async def obtener_viaje(self, despacho_id: str, viaje_id: str) -> ViajeResumen | None: ...

    async def obtener_datos_cpe(
        self, despacho_id: str, viaje_id: str
    ) -> DatosCpeDespacho | None: ...

    async def calcular_metricas(self) -> MetricasDespachos: ...


class DespachosLocal:
    """Implementación local del contrato (mismo proceso, misma base)."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._dao = DespachoDAO(sesion)

    async def obtener_viaje(self, despacho_id: str, viaje_id: str) -> ViajeResumen | None:
        viaje = await self._dao.buscar_viaje(despacho_id, viaje_id)
        if viaje is None:
            return None
        despacho = await self._dao.buscar_por_id(despacho_id)
        assert despacho is not None  # El viaje pertenece a la campaña.
        return ViajeResumen(
            id=viaje.id,
            despacho_id=despacho.id,
            chofer_id=viaje.chofer_id,
            chofer_nombre=viaje.chofer_nombre,
            dominio=viaje.dominio,
            destino=viaje.destino,
            toneladas=viaje.toneladas,
            estado=viaje.estado,
            material=despacho.material,
            origen=despacho.origen,
        )

    async def obtener_datos_cpe(
        self, despacho_id: str, viaje_id: str
    ) -> DatosCpeDespacho | None:
        viaje = await self._dao.buscar_viaje(despacho_id, viaje_id)
        if viaje is None:
            return None
        despacho = await self._dao.buscar_por_id(despacho_id)
        if despacho is None:
            return None
        return DatosCpeDespacho(
            viaje_id=viaje.id,
            despacho_id=despacho.id,
            despacho_nombre=despacho.nombre,
            estado_viaje=viaje.estado,
            chofer_id=viaje.chofer_id,
            chofer_nombre=viaje.chofer_nombre,
            dominio=viaje.dominio,
            destino=viaje.destino,
            toneladas=viaje.toneladas,
            observaciones=viaje.observaciones or "",
            material=despacho.material,
            origen=despacho.origen,
            productor_id=despacho.productor_id,
            campo_id=despacho.campo_id,
            entrada_campo=despacho.entrada_campo,
            distancia_km=despacho.distancia_km,
            tarifa_por_tn=despacho.tarifa_por_tn,
            fecha_inicio=despacho.fecha_inicio,
            cuando=despacho.cuando,
            cuando_fecha=despacho.cuando_fecha,
            cpe_habilitada=bool(despacho.cpe_habilitada),
            cpe_tipo=despacho.cpe_tipo,
            cpe_sucursal=despacho.cpe_sucursal,
            cpe_cosecha=despacho.cpe_cosecha,
            cpe_cuit_solicitante=despacho.cpe_cuit_solicitante,
            cpe_origen_cod_provincia=despacho.cpe_origen_cod_provincia,
            cpe_origen_cod_localidad=despacho.cpe_origen_cod_localidad,
            cpe_origen_planta=despacho.cpe_origen_planta,
            cpe_nro_renspa=despacho.cpe_nro_renspa,
            cpe_codigo_turno=despacho.cpe_codigo_turno,
            cpe_hora_partida=despacho.cpe_hora_partida,
            cpe_corresponde_retiro_productor=bool(despacho.cpe_corresponde_retiro_productor),
            cpe_es_solicitante_campo=bool(despacho.cpe_es_solicitante_campo),
            cpe_destino_cuit=despacho.cpe_destino_cuit,
            cpe_destino_es_campo=bool(despacho.cpe_destino_es_campo),
            cpe_destino_cod_provincia=despacho.cpe_destino_cod_provincia,
            cpe_destino_cod_localidad=despacho.cpe_destino_cod_localidad,
            cpe_destino_planta=despacho.cpe_destino_planta,
            cpe_peso_tara_kg_default=despacho.cpe_peso_tara_kg_default,
            cpe_mercaderia_fumigada=bool(despacho.cpe_mercaderia_fumigada),
            cpe_cuit_pagador_flete=despacho.cpe_cuit_pagador_flete,
            cpe_cuit_intermediario_flete=despacho.cpe_cuit_intermediario_flete,
            cpe_cuit_remitente_comercial_vp=despacho.cpe_cuit_remitente_comercial_vp,
            cpe_cuit_remitente_comercial_vs=despacho.cpe_cuit_remitente_comercial_vs,
            cpe_cuit_mercado_a_termino=despacho.cpe_cuit_mercado_a_termino,
            cpe_cuit_corredor_vp=despacho.cpe_cuit_corredor_vp,
            cpe_cuit_corredor_vs=despacho.cpe_cuit_corredor_vs,
            cpe_cuit_representante_entregador=despacho.cpe_cuit_representante_entregador,
            cpe_cuit_representante_recibidor=despacho.cpe_cuit_representante_recibidor,
            cpe_cuit_remitente_comercial_vs2=despacho.cpe_cuit_remitente_comercial_vs2,
            cpe_cuit_remitente_comercial_productor=despacho.cpe_cuit_remitente_comercial_productor,
            viaje_cpe_destino_cuit=viaje.cpe_destino_cuit,
            viaje_cpe_destino_es_campo=viaje.cpe_destino_es_campo,
            viaje_cpe_destino_cod_provincia=viaje.cpe_destino_cod_provincia,
            viaje_cpe_destino_cod_localidad=viaje.cpe_destino_cod_localidad,
            viaje_cpe_destino_planta=viaje.cpe_destino_planta,
            viaje_cpe_peso_bruto_kg=viaje.cpe_peso_bruto_kg,
            viaje_cpe_peso_tara_kg=viaje.cpe_peso_tara_kg,
            viaje_cpe_codigo_turno=viaje.cpe_codigo_turno,
            viaje_cpe_dominio_acoplado=viaje.cpe_dominio_acoplado,
        )

    async def calcular_metricas(self) -> MetricasDespachos:
        """Agrega métricas recorriendo las campañas activas."""
        despachos = await self._dao.listar(estado="activo")
        viajes = [v for d in despachos for v in d.viajes]
        completados = [v for v in viajes if v.estado == "completado"]
        return MetricasDespachos(
            campanias_activas=len(despachos),
            viajes_totales=len(viajes),
            viajes_completados=len(completados),
            viajes_en_curso=sum(1 for v in viajes if v.estado == "en_viaje"),
            viajes_retrasados=sum(1 for v in viajes if v.estado == "retrasado"),
            toneladas_totales=sum(v.toneladas for v in viajes),
            toneladas_completadas=sum(v.toneladas for v in completados),
        )
