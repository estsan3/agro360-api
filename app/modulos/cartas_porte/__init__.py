"""Módulo CARTAS DE PORTE: emisión de CPE (Carta de Porte Electrónica).

Integra con los web services de ARCA/AFIP (WSCPE, RG 5017/2021) a través
de un "puerto" (interfaz) con dos adaptadores:

- `AdaptadorSimulado`: genera CPE ficticias para desarrollo y tests.
- `AdaptadorAfip`: WSAA + WSCPE SOAP real (homologación o producción).
"""
