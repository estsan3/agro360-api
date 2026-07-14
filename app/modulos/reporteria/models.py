"""Reportería no tiene tablas propias: consume datos vía contratos.

El archivo existe para mantener la estructura homogénea entre módulos
(el import en `core.database.crear_tablas` no falla). Si en el futuro
se materializan reportes (snapshots), sus tablas van acá con prefijo
`reporteria_`.
"""
