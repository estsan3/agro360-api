"""Adaptador REAL hacia ARCA/AFIP (esqueleto documentado, a completar).

Requisitos previos para activarlo:
1. Certificado digital + clave privada emitidos por ARCA.
2. Alta del servicio `wscpe` en "Autogestión de certificados para
   Servicios Web" (homologación y luego producción).
3. Instalar la librería: `pip install pyafipws` (agregarla a pyproject).

Flujo de la integración (RG 5017/2021):
- WSAA: con el certificado se obtiene un Ticket de Acceso (token + sign),
  válido ~12 horas, para el servicio "wscpe".
- WSCPE: con ese ticket se autoriza la CPE automotor; AFIP devuelve
  nro de carta de porte, nro de CTG y el PDF de la constancia.

Endpoints WSCPE (verificar contra el manual vigente):
- Homologación: https://cpea-ws-qaext.afip.gob.ar/wscpe/services/soap?wsdl
- Producción:   https://cpea-ws.afip.gob.ar/wscpe/services/soap?wsdl
"""

from app.modulos.cartas_porte.puerto import ProveedorCPE, ResultadoCPE, SolicitudCPE


class AdaptadorAfip(ProveedorCPE):
    """Implementación real vía PyAfipWs (pendiente de certificado).

    El pseudocódigo comentado en cada método muestra la implementación
    final esperada con PyAfipWs.
    """

    def __init__(
        self,
        ruta_certificado: str,
        ruta_clave_privada: str,
        cuit_representada: str,
        homologacion: bool = True,
    ) -> None:
        self._ruta_certificado = ruta_certificado
        self._ruta_clave_privada = ruta_clave_privada
        self._cuit = cuit_representada
        self._homologacion = homologacion

    async def autorizar_cpe_automotor(self, solicitud: SolicitudCPE) -> ResultadoCPE:
        # Implementación final esperada (PyAfipWs):
        #
        #   from pyafipws.wsaa import WSAA
        #   from pyafipws.wscpe import WSCPE
        #
        #   wsaa = WSAA()
        #   ta = wsaa.Autenticar("wscpe", self._ruta_certificado, self._ruta_clave_privada)
        #
        #   wscpe = WSCPE()
        #   wscpe.Conectar()          # en producción: pasar la WSDL de prod
        #   wscpe.SetTicketAcceso(ta)
        #   wscpe.Cuit = self._cuit
        #
        #   wscpe.CrearCPE()
        #   wscpe.AgregarCabecera(tipo_cpe=74, cuit_solicitante=self._cuit, ...)
        #   wscpe.AgregarOrigen(...)      # provincia/localidad de solicitud.origen
        #   wscpe.AgregarDatosCarga(cod_grano=solicitud.codigo_grano_afip, ...)
        #   wscpe.AgregarDestino(...)     # provincia/localidad de solicitud.destino
        #   wscpe.AgregarTransporte(dominio=solicitud.dominio, ...)
        #   ok = wscpe.AutorizarCPEAutomotor("/tmp/cpe.pdf")
        #
        #   return ResultadoCPE(
        #       autorizada=bool(ok),
        #       nro_carta_porte=wscpe.NroCartaPorte,
        #       nro_ctg=wscpe.NroCTG,
        #       error=wscpe.ErrMsg or "",
        #   )
        raise NotImplementedError(
            "AdaptadorAfip requiere certificado digital de ARCA. "
            "Mientras tanto usar AdaptadorSimulado (default)."
        )

    async def anular_cpe(self, nro_carta_porte: str) -> ResultadoCPE:
        # Implementación final: wscpe.AgregarCabecera(...) + wscpe.AnularCPE()
        raise NotImplementedError("Ver autorizar_cpe_automotor para los requisitos.")
