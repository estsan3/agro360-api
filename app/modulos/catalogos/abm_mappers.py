"""Mapeo ORM ↔ DTOs ABM del front."""

from typing import Any

from app.modulos.catalogos.models import (
    Camion,
    Campo,
    Chofer,
    Productor,
    PuntoEntrada,
    ResponsableProductor,
    Transportista,
)
from app.modulos.catalogos.schemas_abm import (
    ArchivoAdjuntoAbm,
    CamionTransportistaAbm,
    CampoProductorAbm,
    ChoferTransportistaAbm,
    ProductorAbm,
    ProductorDetalleAbm,
    PuntoEntradaAbm,
    ResponsableProductorAbm,
    TransportistaAbm,
    TransportistaDetalleAbm,
)


def _ui(entidad: object) -> dict[str, Any]:
    datos = getattr(entidad, "datos_ui", None)
    return dict(datos) if datos else {}


def _archivo(datos: dict[str, Any], clave: str) -> ArchivoAdjuntoAbm | None:
    raw = datos.get(clave)
    if not raw or not isinstance(raw, dict):
        return None
    return ArchivoAdjuntoAbm(
        nombre=str(raw.get("nombre", "")),
        tipo=str(raw.get("tipo", "")),
        data_url=str(raw.get("data_url", "")),
    )


def _archivo_a_dict(archivo: ArchivoAdjuntoAbm | dict[str, str] | None) -> dict[str, str] | None:
    if archivo is None:
        return None
    if hasattr(archivo, "model_dump"):
        archivo = archivo.model_dump()
    if not isinstance(archivo, dict):
        return None
    if not archivo.get("data_url"):
        return None
    return {
        "nombre": str(archivo.get("nombre", "")),
        "tipo": str(archivo.get("tipo", "")),
        "data_url": str(archivo.get("data_url", "")),
    }


def _nombre_canonico(fantasia: str, razon: str) -> str:
    return (fantasia or razon or "Sin nombre").strip()


def transportista_a_abm(t: Transportista) -> TransportistaAbm:
    ui = _ui(t)
    fantasia = str(ui.get("nombre_fantasia") or t.nombre)
    razon = str(ui.get("razon_social") or t.nombre)
    return TransportistaAbm(
        id=t.id,
        activo=t.activo,
        eliminado=not t.activo,
        nombre_fantasia=fantasia,
        razon_social=razon,
        cuit=t.cuit or "",
        direccion=str(ui.get("direccion", "")),
        email=str(ui.get("email", "")),
        telefono=str(ui.get("telefono", "")),
        pagina_web=str(ui.get("pagina_web", "")),
    )


def camion_a_abm(c: Camion) -> CamionTransportistaAbm:
    ui = _ui(c)
    return CamionTransportistaAbm(
        id=c.id,
        transportista_id=c.transportista_id,
        activo=c.activo,
        eliminado=not c.activo,
        dominio=c.dominio,
        marca=str(ui.get("marca", "")),
        modelo=c.modelo or str(ui.get("modelo", "")),
        tipo=str(ui.get("tipo", "")),
        nro_chasis=str(ui.get("nro_chasis", "")),
        nro_motor=str(ui.get("nro_motor", "")),
        foto_tarjeta_verde=_archivo(ui, "foto_tarjeta_verde"),
    )


def chofer_a_abm(c: Chofer) -> ChoferTransportistaAbm:
    ui = _ui(c)
    partes = (c.nombre or "").split(" ", 1)
    nombre = str(ui.get("nombre") or partes[0])
    apellido = str(ui.get("apellido") or (partes[1] if len(partes) > 1 else ""))
    return ChoferTransportistaAbm(
        id=c.id,
        transportista_id=c.transportista_id or "",
        activo=c.activo,
        eliminado=not c.activo,
        nombre=nombre,
        apellido=apellido,
        documento=str(ui.get("documento", "")),
        direccion=str(ui.get("direccion", "")),
        telefono=str(ui.get("telefono", "")),
        edad=int(ui.get("edad", 0) or 0),
        fecha_nacimiento=str(ui.get("fecha_nacimiento", "")),
        licencia_tipo=str(ui.get("licencia_tipo", "")),
        licencia_vencimiento=str(ui.get("licencia_vencimiento", "")),
        camion_id=c.camion_id,
        foto_licencia=_archivo(ui, "foto_licencia"),
        foto_dni_frente=_archivo(ui, "foto_dni_frente"),
        foto_dni_dorso=_archivo(ui, "foto_dni_dorso"),
    )


def transportista_detalle_a_abm(t: Transportista) -> TransportistaDetalleAbm:
    base = transportista_a_abm(t)
    return TransportistaDetalleAbm(
        **base.model_dump(),
        choferes=[chofer_a_abm(c) for c in t.choferes],
        camiones=[camion_a_abm(c) for c in t.camiones],
    )


def aplicar_transportista_ui(t: Transportista, datos: dict[str, Any]) -> None:
    fantasia = str(datos.get("nombre_fantasia", "")).strip()
    razon = str(datos.get("razon_social", "")).strip()
    t.nombre = _nombre_canonico(fantasia, razon)
    t.cuit = datos.get("cuit") or None
    t.datos_ui = {
        "nombre_fantasia": fantasia or t.nombre,
        "razon_social": razon or t.nombre,
        "direccion": datos.get("direccion", ""),
        "email": datos.get("email", ""),
        "telefono": datos.get("telefono", ""),
        "pagina_web": datos.get("pagina_web", ""),
    }


def aplicar_camion_ui(c: Camion, datos: dict[str, Any]) -> None:
    c.modelo = str(datos.get("modelo", c.modelo or ""))
    c.datos_ui = {
        "marca": datos.get("marca", ""),
        "tipo": datos.get("tipo", ""),
        "nro_chasis": datos.get("nro_chasis", ""),
        "nro_motor": datos.get("nro_motor", ""),
        "foto_tarjeta_verde": _archivo_a_dict(datos.get("foto_tarjeta_verde")),
    }


def aplicar_chofer_ui(c: Chofer, datos: dict[str, Any]) -> None:
    nombre = str(datos.get("nombre", "")).strip()
    apellido = str(datos.get("apellido", "")).strip()
    c.nombre = f"{nombre} {apellido}".strip() or c.nombre
    camion_id = datos.get("camion_id")
    c.camion_id = camion_id if camion_id else None
    c.datos_ui = {
        "nombre": nombre,
        "apellido": apellido,
        "documento": datos.get("documento", ""),
        "direccion": datos.get("direccion", ""),
        "telefono": datos.get("telefono", ""),
        "edad": datos.get("edad", 0),
        "fecha_nacimiento": datos.get("fecha_nacimiento", ""),
        "licencia_tipo": datos.get("licencia_tipo", ""),
        "licencia_vencimiento": datos.get("licencia_vencimiento", ""),
        "foto_licencia": _archivo_a_dict(datos.get("foto_licencia")),
        "foto_dni_frente": _archivo_a_dict(datos.get("foto_dni_frente")),
        "foto_dni_dorso": _archivo_a_dict(datos.get("foto_dni_dorso")),
    }


def productor_a_abm(p: Productor) -> ProductorAbm:
    ui = _ui(p)
    fantasia = str(ui.get("nombre_fantasia") or p.nombre)
    razon = str(ui.get("razon_social") or p.nombre)
    return ProductorAbm(
        id=p.id,
        activo=p.activo,
        eliminado=not p.activo,
        nombre_fantasia=fantasia,
        razon_social=razon,
        cuit=p.cuit or "",
        direccion_fiscal=str(ui.get("direccion_fiscal", "")),
        email=str(ui.get("email", "")),
        telefono=str(ui.get("telefono", "")),
        vendedor_id=str(ui.get("vendedor_id", "")),
        notas=str(ui.get("notas", "")),
    )


def punto_entrada_a_abm(p: PuntoEntrada) -> PuntoEntradaAbm:
    return PuntoEntradaAbm(
        id=p.id,
        campo_id=p.campo_id,
        activo=p.activo,
        eliminado=not p.activo,
        nombre=p.nombre,
        orden=p.orden,
        latitud=p.latitud,
        longitud=p.longitud,
        observacion=p.observacion or "",
    )


def campo_a_abm(c: Campo) -> CampoProductorAbm:
    ui = _ui(c)
    return CampoProductorAbm(
        id=c.id,
        productor_id=c.productor_id,
        activo=c.activo,
        eliminado=not c.activo,
        nombre=c.nombre,
        codigo=str(ui.get("codigo", "")),
        superficie_ha=float(ui.get("superficie_ha", 0) or 0),
        localidad=str(ui.get("localidad", "")),
        provincia=str(ui.get("provincia", "")),
        partido=str(ui.get("partido", "")),
        direccion=str(ui.get("direccion", "")),
        latitud=float(ui.get("latitud", 0) or 0),
        longitud=float(ui.get("longitud", 0) or 0),
        contacto_nombre=str(ui.get("contacto_nombre", "")),
        contacto_telefono=str(ui.get("contacto_telefono", "")),
        puntos_entrada=[
            punto_entrada_a_abm(p) for p in sorted(c.puntos_entrada, key=lambda x: x.orden)
            if p.activo
        ],
    )


def responsable_a_abm(r: ResponsableProductor) -> ResponsableProductorAbm:
    return ResponsableProductorAbm(
        id=r.id,
        productor_id=r.productor_id,
        activo=r.activo,
        eliminado=not r.activo,
        nombre=r.nombre,
        apellido=r.apellido,
        telefono=r.telefono,
        documento=r.documento,
    )


def productor_detalle_a_abm(p: Productor) -> ProductorDetalleAbm:
    base = productor_a_abm(p)
    return ProductorDetalleAbm(
        **base.model_dump(),
        responsables=[responsable_a_abm(r) for r in p.responsables],
        campos=[campo_a_abm(c) for c in p.campos],
    )


def aplicar_productor_ui(p: Productor, datos: dict[str, Any]) -> None:
    fantasia = str(datos.get("nombre_fantasia", "")).strip()
    razon = str(datos.get("razon_social", "")).strip()
    p.nombre = _nombre_canonico(fantasia, razon)
    p.cuit = datos.get("cuit") or None
    p.datos_ui = {
        "nombre_fantasia": fantasia or p.nombre,
        "razon_social": razon or p.nombre,
        "direccion_fiscal": datos.get("direccion_fiscal", ""),
        "email": datos.get("email", ""),
        "telefono": datos.get("telefono", ""),
        "vendedor_id": datos.get("vendedor_id", ""),
        "notas": datos.get("notas", ""),
    }


def aplicar_campo_ui(c: Campo, datos: dict[str, Any]) -> None:
    c.nombre = str(datos.get("nombre", c.nombre)).strip() or c.nombre
    c.datos_ui = {
        "codigo": datos.get("codigo", ""),
        "superficie_ha": datos.get("superficie_ha", 0),
        "localidad": datos.get("localidad", ""),
        "provincia": datos.get("provincia", ""),
        "partido": datos.get("partido", ""),
        "direccion": datos.get("direccion", ""),
        "latitud": datos.get("latitud", 0),
        "longitud": datos.get("longitud", 0),
        "contacto_nombre": datos.get("contacto_nombre", ""),
        "contacto_telefono": datos.get("contacto_telefono", ""),
    }


def texto_busqueda_transportista(t: Transportista) -> str:
    abm = transportista_a_abm(t)
    return " ".join(
        [
            abm.nombre_fantasia,
            abm.razon_social,
            abm.cuit,
            abm.email,
            abm.telefono,
        ]
    ).lower()


def texto_busqueda_productor(p: Productor) -> str:
    abm = productor_a_abm(p)
    return " ".join(
        [abm.nombre_fantasia, abm.razon_social, abm.cuit, abm.email, abm.telefono]
    ).lower()
