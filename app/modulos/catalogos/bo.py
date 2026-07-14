"""Capa BO del módulo catálogos: reglas de negocio de los maestros."""

import re

from app.core.excepciones import ReglaDeNegocioViolada

# Patentes argentinas: formato viejo (ABC123) o nuevo (AB123CD).
_PATRON_DOMINIO = re.compile(r"^([A-Z]{3}\d{3}|[A-Z]{2}\d{3}[A-Z]{2})$")


class CatalogosBO:
    """Validaciones de negocio de productores, materiales y choferes."""

    def validar_productor_nuevo(self, nombre_ya_existe: bool) -> None:
        if nombre_ya_existe:
            raise ReglaDeNegocioViolada("Ya existe un productor con ese nombre")

    def validar_material_nuevo(self, nombre_ya_existe: bool) -> None:
        if nombre_ya_existe:
            raise ReglaDeNegocioViolada("Ya existe un material con ese nombre")

    def validar_dominio(self, dominio: str) -> str:
        """Normaliza y valida la patente del camión."""
        normalizado = dominio.strip().upper().replace(" ", "")
        if not _PATRON_DOMINIO.match(normalizado):
            raise ReglaDeNegocioViolada(
                f"Dominio inválido: {dominio}. Formatos válidos: ABC123 o AB123CD"
            )
        return normalizado
