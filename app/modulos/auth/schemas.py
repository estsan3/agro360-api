"""DTOs (Pydantic) del módulo auth: contratos de entrada/salida de la API."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Credenciales para iniciar sesión."""

    email: EmailStr
    password: str = Field(min_length=8, description="Mínimo 8 caracteres")


class UsuarioResponse(BaseModel):
    """Representación pública de un usuario (sin datos sensibles)."""

    id: str
    nombre: str
    dni: str
    email: str
    rol: str

    # Permite construir el DTO directamente desde el modelo ORM.
    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    """Respuesta del login: token de acceso + datos del usuario."""

    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse


class CrearUsuarioRequest(BaseModel):
    """Alta de un usuario del backoffice.

    La contraseña es opcional: si no se envía (caso del front admin),
    se asigna la contraseña inicial de demo y el usuario deberá
    cambiarla en su primer ingreso (pendiente de implementar).
    """

    nombre: str = Field(min_length=2, max_length=120)
    dni: str = Field(min_length=6, max_length=20)
    email: EmailStr
    password: str | None = Field(default=None, min_length=8)
    rol: str = Field(pattern="^(administrador|vendedor)$")


class CrearVendedorRequest(BaseModel):
    """Alta rápida de vendedor desde la pantalla de catálogos del front.

    Solo pide el nombre: email y DNI se generan como provisorios hasta
    que el vendedor se complete como usuario pleno.
    """

    nombre: str = Field(min_length=2, max_length=120)
