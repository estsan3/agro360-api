"""DTOs del módulo catálogos."""

from pydantic import BaseModel, Field


class CampoResponse(BaseModel):
    id: str
    nombre: str

    model_config = {"from_attributes": True}


class ProductorResponse(BaseModel):
    id: str
    nombre: str
    cuit: str | None = None
    campos: list[CampoResponse] = []

    model_config = {"from_attributes": True}


class CrearProductorRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    cuit: str | None = Field(default=None, max_length=13)
    # Nombres de los campos iniciales del productor (opcional).
    campos: list[str] = []


class CrearCampoRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)


class MaterialResponse(BaseModel):
    id: str
    nombre: str
    codigo_grano_afip: int | None = None

    model_config = {"from_attributes": True}


class CrearMaterialRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=60)
    codigo_grano_afip: int | None = None


class ChoferResponse(BaseModel):
    id: str
    nombre: str
    dominio: str
    modelo: str = ""
    cuit: str | None = None
    activo: bool

    model_config = {"from_attributes": True}


class CrearChoferRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    dominio: str = Field(min_length=6, max_length=10, description="Patente, ej: AA123BB")
    modelo: str = Field(default="", max_length=80)
    cuit: str | None = Field(default=None, max_length=13)


# ----------------------- Respuesta agregada /catalogos -----------------------
# Es el contrato que consume el front: todos los maestros en una sola llamada,
# incluyendo administradores y vendedores (usuarios de auth, vía contrato).


class PersonaResumenResponse(BaseModel):
    """Par id/nombre para combos del front (administradores, vendedores)."""

    id: str
    nombre: str


class ChoferAgregadoResponse(BaseModel):
    """Forma del chofer dentro de la respuesta agregada (la que usa el front)."""

    id: str
    nombre: str
    dominio: str
    modelo: str = ""


class CatalogosAgregadosResponse(BaseModel):
    """Todos los catálogos en una sola respuesta (contrato del front)."""

    productores: list[ProductorResponse]
    administradores: list[PersonaResumenResponse]
    vendedores: list[PersonaResumenResponse]
    # El front consume los materiales como lista de nombres.
    materiales: list[str]
    choferes: list[ChoferAgregadoResponse]
