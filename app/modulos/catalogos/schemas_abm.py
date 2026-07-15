"""DTOs ABM alineados al contrato del front (/transportistas, /productores)."""

from pydantic import BaseModel, Field


class ArchivoAdjuntoAbm(BaseModel):
    nombre: str = ""
    tipo: str = ""
    data_url: str = ""


class CamionTransportistaAbm(BaseModel):
    id: str
    transportista_id: str
    activo: bool
    eliminado: bool
    dominio: str
    marca: str = ""
    modelo: str = ""
    tipo: str = ""
    nro_chasis: str = ""
    nro_motor: str = ""
    foto_tarjeta_verde: ArchivoAdjuntoAbm | None = None


class ChoferTransportistaAbm(BaseModel):
    id: str
    transportista_id: str
    activo: bool
    eliminado: bool
    nombre: str
    apellido: str = ""
    documento: str = ""
    direccion: str = ""
    telefono: str = ""
    edad: int = 0
    fecha_nacimiento: str = ""
    licencia_tipo: str = ""
    licencia_vencimiento: str = ""
    camion_id: str | None = None
    foto_licencia: ArchivoAdjuntoAbm | None = None
    foto_dni_frente: ArchivoAdjuntoAbm | None = None
    foto_dni_dorso: ArchivoAdjuntoAbm | None = None


class TransportistaAbm(BaseModel):
    id: str
    activo: bool
    eliminado: bool
    nombre_fantasia: str
    razon_social: str
    cuit: str = ""
    direccion: str = ""
    email: str = ""
    telefono: str = ""
    pagina_web: str = ""


class TransportistaDetalleAbm(TransportistaAbm):
    choferes: list[ChoferTransportistaAbm] = []
    camiones: list[CamionTransportistaAbm] = []


class GuardarTransportistaAbm(BaseModel):
    nombre_fantasia: str = Field(default="", max_length=120)
    razon_social: str = Field(default="", max_length=120)
    cuit: str = Field(default="", max_length=13)
    direccion: str = Field(default="", max_length=255)
    email: str = Field(default="", max_length=120)
    telefono: str = Field(default="", max_length=40)
    pagina_web: str = Field(default="", max_length=255)


class GuardarChoferAbm(BaseModel):
    nombre: str = Field(default="", max_length=80)
    apellido: str = Field(default="", max_length=80)
    documento: str = Field(default="", max_length=20)
    direccion: str = Field(default="", max_length=255)
    telefono: str = Field(default="", max_length=40)
    edad: int = 0
    fecha_nacimiento: str = ""
    licencia_tipo: str = ""
    licencia_vencimiento: str = ""
    camion_id: str | None = None
    foto_licencia: ArchivoAdjuntoAbm | None = None
    foto_dni_frente: ArchivoAdjuntoAbm | None = None
    foto_dni_dorso: ArchivoAdjuntoAbm | None = None


class GuardarCamionAbm(BaseModel):
    dominio: str = Field(default="", max_length=10)
    marca: str = Field(default="", max_length=80)
    modelo: str = Field(default="", max_length=80)
    tipo: str = Field(default="", max_length=40)
    nro_chasis: str = Field(default="", max_length=40)
    nro_motor: str = Field(default="", max_length=40)
    foto_tarjeta_verde: ArchivoAdjuntoAbm | None = None


class CambiarActivoAbm(BaseModel):
    activo: bool


class PuntoEntradaAbm(BaseModel):
    id: str
    campo_id: str
    activo: bool
    eliminado: bool
    nombre: str
    orden: int
    latitud: float
    longitud: float
    observacion: str = ""


class CampoProductorAbm(BaseModel):
    id: str
    productor_id: str
    activo: bool
    eliminado: bool
    nombre: str
    codigo: str = ""
    superficie_ha: float = 0
    localidad: str = ""
    provincia: str = ""
    partido: str = ""
    direccion: str = ""
    latitud: float = 0
    longitud: float = 0
    contacto_nombre: str = ""
    contacto_telefono: str = ""
    puntos_entrada: list[PuntoEntradaAbm] = []


class ResponsableProductorAbm(BaseModel):
    id: str
    productor_id: str
    activo: bool
    eliminado: bool
    nombre: str
    apellido: str = ""
    telefono: str = ""
    documento: str = ""


class ProductorAbm(BaseModel):
    id: str
    activo: bool
    eliminado: bool
    nombre_fantasia: str
    razon_social: str
    cuit: str = ""
    direccion_fiscal: str = ""
    email: str = ""
    telefono: str = ""
    vendedor_id: str = ""
    notas: str = ""


class ProductorDetalleAbm(ProductorAbm):
    responsables: list[ResponsableProductorAbm] = []
    campos: list[CampoProductorAbm] = []


class GuardarProductorAbm(BaseModel):
    nombre_fantasia: str = Field(default="", max_length=120)
    razon_social: str = Field(default="", max_length=120)
    cuit: str = Field(default="", max_length=13)
    direccion_fiscal: str = Field(default="", max_length=255)
    email: str = Field(default="", max_length=120)
    telefono: str = Field(default="", max_length=40)
    vendedor_id: str = ""
    notas: str = ""


class GuardarResponsableAbm(BaseModel):
    nombre: str = Field(default="", max_length=80)
    apellido: str = Field(default="", max_length=80)
    telefono: str = Field(default="", max_length=40)
    documento: str = Field(default="", max_length=20)


class PuntoEntradaInputAbm(BaseModel):
    id: str | None = None
    nombre: str = "Entrada"
    orden: int = 1
    latitud: float = 0
    longitud: float = 0
    observacion: str = ""


class GuardarCampoAbm(BaseModel):
    nombre: str = Field(default="", max_length=120)
    codigo: str = ""
    superficie_ha: float = 0
    localidad: str = ""
    provincia: str = ""
    partido: str = ""
    direccion: str = ""
    latitud: float = 0
    longitud: float = 0
    contacto_nombre: str = ""
    contacto_telefono: str = ""
    puntos_entrada: list[PuntoEntradaInputAbm] = []


class VendedorOptionAbm(BaseModel):
    id: str
    nombre: str
