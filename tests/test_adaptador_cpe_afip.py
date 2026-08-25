"""Parseo de tickets WSAA y respuestas WSCPE (sin red)."""

from app.modulos.cartas_porte.adaptadores.afip import _parsear_autorizacion
from app.modulos.cartas_porte.adaptadores.wsaa import parsear_ticket
from app.modulos.cartas_porte.puerto import SolicitudCPE


def test_parsear_ticket_wsaa_escapado():
    crudo = (
        "&lt;?xml version=&quot;1.0&quot; encoding=&quot;UTF-8&quot; "
        "standalone=&quot;yes&quot;?&gt;"
        "&lt;loginTicketResponse version=&quot;1.0&quot;&gt;"
        "&lt;header&gt;"
        "&lt;expirationTime&gt;2026-08-20T23:00:00-03:00&lt;/expirationTime&gt;"
        "&lt;/header&gt;"
        "&lt;credentials&gt;"
        "&lt;token&gt;TOKEN-DEMO&lt;/token&gt;"
        "&lt;sign&gt;SIGN-DEMO&lt;/sign&gt;"
        "&lt;/credentials&gt;"
        "&lt;/loginTicketResponse&gt;"
    )
    ticket = parsear_ticket(crudo)
    assert ticket.token == "TOKEN-DEMO"
    assert ticket.sign == "SIGN-DEMO"
    assert ticket.vigente()


def test_parsear_autorizacion_wscpe_ok():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                   xmlns:ns="https://serviciosjava.afip.gob.ar/wscpe/">
      <soap:Body>
        <ns:autorizarCPEAutomotorResponse>
          <respuesta>
            <cabecera>
              <sucursal>1</sucursal>
              <nroOrden>12</nroOrden>
              <nroCTG>88990011</nroCTG>
            </cabecera>
            <pdf>JVBERi0x</pdf>
          </respuesta>
        </ns:autorizarCPEAutomotorResponse>
      </soap:Body>
    </soap:Envelope>
    """
    resultado = _parsear_autorizacion(
        xml, SolicitudCPE(payload={"tipo_cpe": 74, "sucursal": 1}, nro_orden=12)
    )
    assert resultado.autorizada is True
    assert resultado.nro_ctg == "88990011"
    assert resultado.nro_carta_porte == "740000100000012"
    assert resultado.pdf_base64 == "JVBERi0x"


def test_parsear_autorizacion_con_errores():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                   xmlns:ns="https://serviciosjava.afip.gob.ar/wscpe/">
      <soap:Body>
        <ns:autorizarCPEAutomotorResponse>
          <respuesta>
            <errores>
              <error>
                <codigo>30</codigo>
                <descripcion>CUIT transportista inválido</descripcion>
              </error>
            </errores>
          </respuesta>
        </ns:autorizarCPEAutomotorResponse>
      </soap:Body>
    </soap:Envelope>
    """
    resultado = _parsear_autorizacion(xml, SolicitudCPE(payload={"tipo_cpe": 74}, nro_orden=1))
    assert resultado.autorizada is False
    assert "CUIT transportista" in resultado.error
