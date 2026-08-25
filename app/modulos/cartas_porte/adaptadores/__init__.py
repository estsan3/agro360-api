"""Adaptadores concretos del puerto ProveedorCPE."""

from app.core.config import obtener_configuracion
from app.modulos.cartas_porte.adaptadores.afip import AdaptadorAfip
from app.modulos.cartas_porte.adaptadores.simulado import AdaptadorSimulado
from app.modulos.cartas_porte.puerto import ProveedorCPE


def crear_proveedor_cpe() -> ProveedorCPE:
    """Elige el adaptador según `AGRO360_CPE_PROVEEDOR` (simulado | afip)."""
    cfg = obtener_configuracion()
    if cfg.cpe_proveedor.strip().lower() == "afip":
        return AdaptadorAfip.desde_config(cfg)
    return AdaptadorSimulado()
