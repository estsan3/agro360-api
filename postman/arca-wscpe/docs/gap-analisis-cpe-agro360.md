# Gap analysis: CPE PDF → Agro360

Casuísticas sembradas: `d-cpe-maiz-cofco`, `d-cpe-soja-ldc`.
Prefijo `sim-` en nombres = dato ilegible/tachado en el PDF (CUIT sintético aparte).

| Campo CPE | Ejemplo | En Agro360 | Estado |
|---|---|---|---|
| codigoTurno | COSM6752… / LAG-SOJ-… | No hay campo en Despacho/Viaje; BO manda codigo_turno=None | **FALTA** |
| dominio acoplado (2°) | AF495WZ / AF232IV | Viaje.dominio / Camion.dominio solo 1 patente | **FALTA** |
| fechaHoraPartida (hora) | 20:00 / 14:30 | Solo fecha (cuando/fecha_inicio) + hora fija 08:00 UTC en BO | **PARCIAL** |
| cuitRemitenteComercialProductor | retiroProductor (tachado en Maíz) | No existe en Despacho; solo flag corresponde_retiro_productor | **FALTA** |
| nroRenspa | origen productor | No modelado en Campo/Despacho | **FALTA** |
| cuitRemitenteComercialVentaSecundaria2 | opcional WSCPE | No hay campo (solo VP y VS) | **FALTA** |
| intervinientes VP/VS/MAT/corredor/entregador | CUITs en pestaña CPE | Campos cpe_cuit_* en Despacho | **OK** |
| destino planta/prov/loc/cuit | 512428 / 21030 | cpe_destino_* + override en Viaje | **OK** |
| pesos bruto/tara | 45000/15000 | Viaje.cpe_peso_* + default tara campaña | **OK** |
| codGrano / cosecha | 19 Maíz / 23 Soja | Material.codigo_grano_afip + cpe_cosecha | **OK** |
| GPS origen | lat/long campo | PuntoEntrada lat/lng → contexto CPE | **OK** |
| CTG / N° CPE / vencimiento / QR | respuesta ARCA | CartaPorte.nro_ctg / nro_carta_porte / pdf (post-autorizar) | **OK (respuesta)** |

## IDs útiles en la app

| Entidad | ID |
|---|---|
| Despacho Maíz→COFCO | `d-cpe-maiz-cofco` |
| Viaje Maíz | `viaje-cpe-maiz-1` |
| Intención Maíz | `cpe-casuistica-maiz-cofco` |
| Despacho Soja→LDC | `d-cpe-soja-ldc` |
| Viaje Soja | `viaje-cpe-soja-1` |
| Intención Soja | `cpe-casuistica-soja-ldc` |
| Productor Maíz (sim) | `p-cpe-maiz` |
| Productor Soja (sim) | `p-cpe-soja` |
| Transportista Barbesini | `t-cpe-barbesini` |
| Transportista Braidotti | `t-cpe-braidotti` |

## Nota CUITs simulados

AFIP/Agro360 exigen 11 dígitos. Por eso `sim-` va en el **nombre**, no en el CUIT.
- Titular/productor Maíz: `30999000001`
- Flete pagador Maíz: `30999000002`
- Rep. entregador Soja: `30999000003`
- Rte. Com. Productor Maíz (gap): `30999000004`
