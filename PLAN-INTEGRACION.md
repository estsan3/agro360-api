# Plan de integración Agro360 — Web + API

Estado al **14/07/2026**. Documento vivo: se actualiza al cerrar cada fase.

---

## Resumen de fases

| Fase | Alcance | Estado |
|------|---------|--------|
| **1** | Backend: contrato compatible con el front | ✅ Completada |
| **2** | Frontend: auth Bearer, proxy, `chofer_id` | ✅ Completada |
| **3** | Verificación E2E + ABMs completos + transportistas | 🔄 3.1 ✅ · 3.3 en progreso |
| **4** | Cartas de porte (UI + CPE real) | ⏸ Fuera de alcance actual |

---

## Fase 1 — Backend (`agro360-api`) ✅

1. Rutas alineadas: `/usuarios`, `/conversaciones`, `/parametros`, `/preferencias`, `GET /catalogos`.
2. Despachos: `PUT /despachos/:id`, estado `borrador`/`activo`, acciones de viaje (`iniciar`, `duplicar`, `eliminar`).
3. Mensajería enriquecida: `viaje_id`, `origen`, `destino`, `estado_viaje`, autor `sistema`.
4. Catálogos: DELETEs por tipo, `modelo` en choferes, vendedores como usuarios con rol.
5. Seed ampliado (13 campañas, conversaciones, choferes).
6. Tests de integración con contrato nuevo.

---

## Fase 2 — Frontend (`agro360-web`) ✅

7. Auth JWT Bearer (`AuthTokenService` + interceptor).
8. Viajes con `chofer_id` (patente por viaje en `dominio`).
9. `mockApi: false`, proxy `/api` → `localhost:8000/api/v1`.
10. Mensajería sin respuesta fake del chofer.
11. Alta de usuarios con contraseña.

---

## Fase 3 — Verificación E2E + ABMs + Transportistas 🔄

### 3.1 Verificación punta a punta (UI + API)

Checklist de validación manual/automática:

- [x] Login y `GET /auth/me` con token persistido
- [x] Catálogos y listado de campañas
- [x] Crear / editar borrador con `chofer_id`
- [x] Activar campaña (estado `activo`)
- [x] Iniciar / duplicar / eliminar viaje
- [x] Enviar mensaje en mensajería
- [x] Parámetros y preferencias
- [x] Alta de chofer, vendedor y usuario
- [x] Fix: fecha de llegada estimada opcional (default = fecha inicio)
- [x] Playwright `e2e/fase3-integracion.spec.ts` en verde
- [ ] Reportes: filtros sobre datos reales (hoy client-side desde store)
- [ ] `environment.prod.ts` para deploy sin proxy

**Infra de desarrollo**

```bash
# API + Postgres
cd agro360-api && docker compose up --build -d

# Front
cd agro360-web && npm run start
# http://localhost:4200 — admin@agro360.com / demo12345
```

**Tests automáticos**

```bash
cd agro360-web && npx playwright test e2e/
cd agro360-api && poetry run pytest
```

---

### 3.2 ABMs completos (Configuración)

Hoy la pantalla de Configuración permite **alta y baja** de catálogos; falta **edición** y consistencia en todos los maestros.

| Entidad | Alta | Baja | Edición | Notas |
|---------|------|------|---------|-------|
| Usuarios | ✅ | ✅ | ❌ | Falta editar nombre/email/rol |
| Productores | ✅ | ✅ | ❌ | |
| Campos | ✅ | ❌ | ❌ | Falta baja/edición por productor |
| Materiales | ✅ | ✅ | ❌ | DELETE acepta id o nombre |
| Choferes | ✅ | ✅ | ❌ | Modelo plano (sin empresa ni flota) |
| Vendedores | ✅ | ✅ | ❌ | Son usuarios auth |
| Parámetros | — | — | ✅ | |
| Preferencias | — | — | ✅ | |

**Tareas Fase 3.2**

1. **API**: endpoints `PUT`/`PATCH` por entidad de catálogo y usuario.
2. **Front**: formularios de edición inline o modal en Configuración.
3. **Validaciones**: CUIT único, patente única, email único, no borrar entidades referenciadas en campañas activas.
4. **Entradas de campo**: sacar hardcode de crear-despacho; exponer entradas por campo en catálogo (lat/lng opcional).

---

### 3.3 Catálogo de transportistas, camiones y choferes

**Problema actual:** el chofer es un registro plano (`nombre`, `dominio`, `modelo`). En la realidad:

- Un **transportista** (empresa) tiene una flota de **camiones** y emplea **choferes**.
- Un chofer puede manejar **varios camiones** (no al revés por patente).
- En cada **viaje** se asigna `chofer_id` + `dominio` (patente de ese traslado).

**Modelo de dominio propuesto**

```
Transportista (empresa)
├── id, nombre, cuit, activo
├── Camiones[]
│   ├── id, dominio (patente), modelo, activo
│   └── transportista_id
└── Choferes[]
    ├── id, nombre, cuit, activo
    ├── transportista_id (nullable = independiente)
    └── camiones_habituales[] (opcional, many-to-many)
```

**Tablas (módulo `catalogos`, prefijo `catalogos_`)**

| Tabla | Campos clave |
|-------|----------------|
| `catalogos_transportista` | id, nombre, cuit, activo |
| `catalogos_camion` | id, dominio, modelo, transportista_id, activo |
| `catalogos_chofer` | id, nombre, cuit, transportista_id, activo — **sin dominio fijo** |

**Reglas de negocio**

- Patente (`dominio`) única por camión en el catálogo.
- Al crear viaje: `chofer_id` obligatorio; `dominio` = patente del camión usado en ese viaje (puede elegirse de la flota del transportista del chofer o tipearse).
- No inferir chofer por patente (regla ya acordada).
- Baja lógica (`activo=false`) si hay viajes en curso.

**API (nuevos endpoints)**

- `GET/POST/PUT/DELETE /catalogos/transportistas`
- `GET/POST/PUT/DELETE /catalogos/transportistas/{id}/camiones`
- `GET/POST/PUT/DELETE /catalogos/transportistas/{id}/choferes` (o choferes con `transportista_id`)
- Actualizar `GET /catalogos` agregado: incluir transportistas con camiones anidados
- Migración: choferes seed → asignar a transportista "Flota propia" o independientes

**Front (nueva sección Configuración → Transportistas)**

1. Listado de empresas de transporte con expand/collapse.
2. ABM transportista (nombre, CUIT).
3. Dentro de cada transportista: tablas de **camiones** y **choferes** con alta/edición/baja.
4. En crear-despacho: selector de chofer agrupado por transportista; al elegir chofer, combo de patentes de su empresa (editable manualmente).

**Orden de implementación (branches por entrega)**

| Branch API | Branch Web | Contenido | Estado |
|------------|------------|-----------|--------|
| `feat/3.3-1-transportistas-y-camiones` | — | Modelos + CRUD transportista/camión | ✅ merge main |
| `feat/3.3-2-chofer-transportista` | — | Chofer → transportista + `/catalogos` | ✅ merge main |
| — | `feat/3.3-3-transportistas-config` | Pestaña Transportistas en Config | ✅ merge main |
| — | `feat/3.3-4-viajes-chofer-patente` | Crear despacho: chofer + patente de flota | 🔄 |

**Workflow git:** cada fila = branch → test → merge a `main` en el repo correspondiente.

**Orden de implementación sugerido (detalle técnico)**

1. Backend: modelos + migración/seed + CRUD transportista/camión.
2. Backend: migrar `Chofer` (quitar `dominio` del catálogo, agregar `transportista_id`).
3. Backend: actualizar contrato y `GET /catalogos`.
4. Front: pantalla Transportistas en Configuración.
5. Front: adaptar crear-despacho / borradores (selector chofer + patente).
6. Tests BO + integración API + E2E Playwright.

---

## Fase 4 — Cartas de porte ⏸

- UI de generación CPE (botones hoy simulan notificación).
- Adaptador AFIP real (PyAfipWs) + RENSPA en campos del catálogo.
- Fuera del alcance de integración web↔API actual.

---

## Decisiones de arquitectura (recordatorio)

- Auth: **Bearer JWT** (no cookies).
- Chofer en viajes: **`chofer_id` obligatorio**; patente en `dominio` del viaje.
- Vendedores: usuarios con rol `vendedor` en `auth`.
- Comunicación entre módulos: **contratos** + eventos de dominio; sin FK cruzadas.
- Dev: API+Postgres Docker, front `ng serve` + proxy.

---

## Próximo paso inmediato

1. Cerrar checklist **3.1** (Playwright en verde tras fix de fecha llegada).
2. Commitear y pushear fix de fecha + plan actualizado.
3. Arrancar **3.3** (transportistas) como siguiente entrega funcional.
