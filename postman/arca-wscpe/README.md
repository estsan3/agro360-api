# Postman — ARCA WSCPE + WSAA (homologación)

Colección basada en el **manual WSCPE v2.0.5** y el WSDL de homologación.

## Archivos

| Archivo | Uso |
|---|---|
| `ARCA-WSCPE.postman_collection.json` | Colección Postman (74 ops + dummy + LoginCms) |
| `Homologacion.postman_environment.json` | Environment de testing |
| `scripts/generar_cms_wsaa.py` | Genera CMS Base64 para LoginCms |
| `scripts/smoke_homologacion.py` | Smoke sin certificado (dummy + WSAA vivo + Auth) |
| `docs/WSCPE-mapeo-cpe-automotor-ejemplo.pdf` | Doc #1: Maíz → COFCO (Puerto Gral. San Martín) |
| `docs/carta-porte-ejemplo.png` | Imagen CPE ejemplo #1 |
| `docs/WSCPE-mapeo-cpe-automotor-ejemplo-soja-ldc.pdf` | Doc #2: Soja → LDC (General Lagos) |
| `docs/carta-porte-ejemplo-soja-ldc.png` | Imagen CPE ejemplo #2 |
| `scripts/generar_doc_mapeo_cpe.py` | Regenera PDF ejemplo #1 |
| `scripts/generar_doc_mapeo_cpe_soja_ldc.py` | Regenera PDF ejemplo #2 |
| `scripts/generar_diagramas_flujo_cpe.py` | Genera PNGs de diagrama de flujo (incluidos en los PDFs) |
| `docs/flujo-cpe-maiz-cofco.png` | Diagrama flujo ejemplo #1 |
| `docs/flujo-cpe-soja-ldc.png` | Diagrama flujo ejemplo #2 |

## Importar en Postman

1. Import → `ARCA-WSCPE.postman_collection.json`
2. Import → `Homologacion.postman_environment.json`
3. Seleccioná el environment **ARCA Homologación WSCPE**

## Endpoints (homologación)

- **WSAA:** `https://wsaahomo.afip.gov.ar/ws/services/LoginCms`
- **WSCPE:** `https://cpea-ws-qaext.afip.gob.ar/wscpe/services/soap`
- **WSDL:** `https://cpea-ws-qaext.afip.gob.ar/wscpe/services/soap?wsdl`
- **Manual:** https://www.arca.gob.ar/ws/documentos/manual_wscpe_v2-0-5.pdf

> Nota: los hosts `*.arca.gob.ar` a veces no resuelven/responden desde algunas redes; los de `*.afip.gob.ar` son los que validamos.

## Flujo de autenticación

1. Obtener certificado de testing en **WSASS** y asociar servicio **`wscpe`**.
2. Generar CMS:

```bash
# Usá las rutas REALES de tu certificado WSASS (no copies /ruta/... tal cual)
cd postman/arca-wscpe/scripts
python3 generar_cms_wsaa.py \
  --cert ~/certs/afip-homo.crt \
  --key ~/certs/afip-homo.key \
  --service wscpe \
  --out cms.b64
```

3. Pegar el contenido de `cms.b64` en la variable `cmsBase64` del environment.
4. Completar `cuitRepresentada` con el CUIT de la empresa representada.
5. Ejecutar carpeta **00 - Smoke Homologación** en este orden:
   - `dummy (sin Auth)` → debe devolver `appserver/authserver/dbserver = Ok`
   - `LoginCms` → guarda `token` y `sign` en el environment
   - `ConsultarProvinciasReq` → con TA real lista provincias

## SOAPAction (importante)

WSCPE exige el header `SOAPAction` con la operación. Si va vacío (`""`), responde *"Error en la autenticacion"* aunque el TA sea válido.

Ejemplo para provincias:

```
SOAPAction: "https://serviciosjava.afip.gob.ar/wscpe/consultarProvincias"
```

La colección ya lo trae en cada request (`…/wscpe/<operacion>`).

## Auth en WSCPE

Todos los métodos (excepto `dummy`) llevan:

```xml
<auth>
  <token>{{token}}</token>
  <sign>{{sign}}</sign>
  <cuitRepresentada>{{cuitRepresentada}}</cuitRepresentada>
</auth>
```

Los body de operaciones con `<solicitud>` quedan con `TODO`: completar según el manual / WSDL.

## Smoke local (sin certificado)

```bash
python3 postman/arca-wscpe/scripts/smoke_homologacion.py
```

Valida:

1. `dummy` responde OK  
2. WSAA responde (Fault CMS con payload inválido = servicio vivo)  
3. `ConsultarProvincias` con Auth inválida falla autenticación (schema Auth OK)

## Carpetas de la colección

- `00 - Smoke Homologación`
- `01 - WSAA Autenticación`
- `02 - WSCPE Disponibilidad`
- `03 - Consultas (solo Auth)`
- `04 - Consultas (con parámetros)`
- `05 - Automotor (74 / 274)` — incluye `autorizarCPEAutomotor`
- `06 - Ferroviaria`
- `07 - Derivados / DG / Ductos / Semillas`
- `08 - Otras operaciones`
