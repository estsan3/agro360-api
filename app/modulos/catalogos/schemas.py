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
    cuit: str | None = None
    activo: bool

    model_config = {"from_attributes": True}


class CrearChoferRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    dominio: str = Field(min_length=6, max_length=10, description="Patente, ej: AA123BB")
    cuit: str | None = Field(default=None, max_length=13)
