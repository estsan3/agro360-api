"""Capa BO del módulo cartas de porte."""

from datetime import UTC, datetime, time, timedelta
from typing import Any

from app.core.excepciones import ReglaDeNegocioViolada
from app.modulos.cartas_porte.models import CartaPorte
from app.modulos.cartas_porte.payload import DatosParaPayloadCPE, validar_y_armar_payload
from app.modulos.catalogos.contrato import ContextoCpeCatalogos
from app.modulos.despachos.contrato import DatosCpeDespacho, ViajeResumen


class CartaPorteBO:
    """Reglas de negocio para intenciones de CPE y armado del payload AFIP."""

    def validar_creacion_intencion(
        self, viaje: ViajeResumen | DatosCpeDespacho, vigente: CartaPorte | None
    ) -> None:
        if vigente is not None:
            raise ReglaDeNegocioViolada(
                "Ya existe una intención/CPE vigente para este viaje "
                f"(estado {vigente.estado}). Reintentá o eliminá la existente."
            )
        dominio = getattr(viaje, "dominio", "")
        if dominio in ("", "-"):
            raise ReglaDeNegocioViolada(
                "El viaje no tiene chofer/dominio asignado; asignalo antes de crear la CPE"
            )
        estado = getattr(viaje, "estado", None) or getattr(viaje, "estado_viaje", "")
        if estado == "completado":
            raise ReglaDeNegocioViolada(
                "El viaje ya está completado; no corresponde crear carta de porte"
            )
        if estado == "cancelado":
            raise ReglaDeNegocioViolada("El viaje está cancelado")

    # Ya generaron CPE ante ARCA (o demo); no se reintentan ni eliminan.
    ESTADOS_PROCESADAS = frozenset({"procesada", "autorizada"})
    # Pueden tener PDF para ver/descargar (incluye anuladas históricas).
    ESTADOS_CON_DOCUMENTO = frozenset({"procesada", "autorizada", "anulada"})

    def validar_reintento(self, carta: CartaPorte) -> None:
        if carta.estado in self.ESTADOS_PROCESADAS:
            raise ReglaDeNegocioViolada(
                "La CPE ya fue procesada; no se puede reintentar"
            )
        if carta.estado == "anulada":
            raise ReglaDeNegocioViolada("La CPE está anulada")

    def validar_eliminacion(self, carta: CartaPorte) -> None:
        if carta.estado in self.ESTADOS_PROCESADAS or carta.estado == "anulada":
            raise ReglaDeNegocioViolada(
                "No se puede eliminar una CPE procesada o anulada"
            )

    def validar_anulacion(self, carta: CartaPorte) -> None:
        if carta.estado not in self.ESTADOS_PROCESADAS:
            raise ReglaDeNegocioViolada(
                f"Solo se puede anular una CPE procesada (estado actual: {carta.estado})"
            )

    def validar_documento(self, carta: CartaPorte) -> None:
        if carta.estado not in self.ESTADOS_CON_DOCUMENTO or not carta.pdf_base64:
            raise ReglaDeNegocioViolada(
                "No hay documento PDF disponible para esta intención"
            )

    def armar_payload(
        self, datos: DatosCpeDespacho, contexto: ContextoCpeCatalogos
    ) -> dict[str, Any]:
        """Compone DatosParaPayloadCPE desde despacho + catálogos y valida."""
        if not datos.cpe_habilitada:
            raise ReglaDeNegocioViolada(
                "La campaña no tiene CPE habilitada; completá la pestaña Carta de Porte"
            )
        if datos.cpe_tipo is None or datos.cpe_sucursal is None or datos.cpe_cosecha is None:
            raise ReglaDeNegocioViolada("Faltan tipo/sucursal/cosecha de CPE en la campaña")
        if (
            datos.cpe_origen_cod_provincia is None
            or datos.cpe_origen_cod_localidad is None
        ):
            raise ReglaDeNegocioViolada("Faltan provincia/localidad de origen ARCA")

        destino_cuit = datos.viaje_cpe_destino_cuit or datos.cpe_destino_cuit
        destino_es_campo = (
            datos.cpe_destino_es_campo
            if datos.viaje_cpe_destino_es_campo is None
            else datos.viaje_cpe_destino_es_campo
        )
        destino_prov = (
            datos.viaje_cpe_destino_cod_provincia or datos.cpe_destino_cod_provincia
        )
        destino_loc = (
            datos.viaje_cpe_destino_cod_localidad or datos.cpe_destino_cod_localidad
        )
        destino_planta = datos.viaje_cpe_destino_planta or datos.cpe_destino_planta
        if destino_prov is None or destino_loc is None:
            raise ReglaDeNegocioViolada("Faltan provincia/localidad de destino ARCA")

        tara = datos.viaje_cpe_peso_tara_kg
        if tara is None:
            tara = datos.cpe_peso_tara_kg_default if datos.cpe_peso_tara_kg_default is not None else 0
        if datos.viaje_cpe_peso_bruto_kg is not None:
            bruto = datos.viaje_cpe_peso_bruto_kg
        else:
            # tn → kg; si hay tara, el bruto = neto + tara.
            neto = int(round(datos.toneladas * 1000))
            bruto = neto + tara

        cuit_solicitante = datos.cpe_cuit_solicitante or contexto.productor_cuit
        if not cuit_solicitante:
            raise ReglaDeNegocioViolada(
                "Falta CUIT solicitante (campaña) o CUIT del productor en catálogos"
            )
        if contexto.codigo_grano_afip is None:
            raise ReglaDeNegocioViolada(
                f"El material '{datos.material}' no tiene codigo_grano_afip en catálogos"
            )
        if not contexto.productor_cuit:
            raise ReglaDeNegocioViolada("El productor no tiene CUIT cargado")
        if not contexto.transportista_cuit:
            raise ReglaDeNegocioViolada("El transportista del chofer no tiene CUIT cargado")
        if not contexto.chofer_cuit:
            raise ReglaDeNegocioViolada("El chofer no tiene CUIT/CUIL cargado")
        if datos.distancia_km is None:
            raise ReglaDeNegocioViolada("La campaña no tiene distancia_km (km a recorrer)")

        partida = self._resolver_fecha_partida(datos)

        return validar_y_armar_payload(
            DatosParaPayloadCPE(
                tipo_cpe=datos.cpe_tipo,
                sucursal=datos.cpe_sucursal,
                cosecha=datos.cpe_cosecha,
                cuit_solicitante=cuit_solicitante,
                origen_cod_provincia=datos.cpe_origen_cod_provincia,
                origen_cod_localidad=datos.cpe_origen_cod_localidad,
                origen_planta=datos.cpe_origen_planta,
                origen_latitud=contexto.origen_latitud,
                origen_longitud=contexto.origen_longitud,
                cuit_productor=contexto.productor_cuit,
                corresponde_retiro_productor=datos.cpe_corresponde_retiro_productor,
                es_solicitante_campo=datos.cpe_es_solicitante_campo,
                cod_grano=contexto.codigo_grano_afip,
                peso_bruto_kg=bruto,
                peso_tara_kg=tara,
                destino_cuit=destino_cuit or "",
                destino_es_campo=destino_es_campo,
                destino_cod_provincia=destino_prov,
                destino_cod_localidad=destino_loc,
                destino_planta=destino_planta,
                cuit_transportista=contexto.transportista_cuit,
                dominio=datos.dominio,
                fecha_hora_partida=partida,
                km_recorrer=int(round(datos.distancia_km)),
                cuit_chofer=contexto.chofer_cuit,
                tarifa=datos.tarifa_por_tn,
                cuit_pagador_flete=datos.cpe_cuit_pagador_flete,
                cuit_intermediario_flete=datos.cpe_cuit_intermediario_flete,
                mercaderia_fumigada=datos.cpe_mercaderia_fumigada,
                codigo_turno=None,
                cuit_remitente_comercial_venta_primaria=datos.cpe_cuit_remitente_comercial_vp,
                cuit_remitente_comercial_venta_secundaria=datos.cpe_cuit_remitente_comercial_vs,
                cuit_mercado_a_termino=datos.cpe_cuit_mercado_a_termino,
                cuit_corredor_venta_primaria=datos.cpe_cuit_corredor_vp,
                cuit_corredor_venta_secundaria=datos.cpe_cuit_corredor_vs,
                cuit_representante_entregador=datos.cpe_cuit_representante_entregador,
                cuit_representante_recibidor=datos.cpe_cuit_representante_recibidor,
                observaciones=datos.observaciones,
                material_nombre=datos.material,
                origen_descripcion=datos.origen,
                destino_descripcion=datos.destino,
                despacho_nombre=datos.despacho_nombre,
            )
        )

    @staticmethod
    def _resolver_fecha_partida(datos: DatosCpeDespacho) -> datetime:
        base = datos.fecha_inicio
        if datos.cuando == "manana":
            base = base + timedelta(days=1)
        elif datos.cuando == "fecha" and datos.cuando_fecha is not None:
            base = datos.cuando_fecha
        return datetime.combine(base, time(8, 0), tzinfo=UTC)
