# Contrato de Origen de Datos: Proyecto EMT Madrid
**Versión:** 4.2
**Fecha:** 2026-07-20
**Estado:** Alineado con esquema medallion aprobado (Bronze / Silver / Gold — 1 tabla cada uno)

---

## 0. Qué cambió respecto a la revisión anterior

| # | Antes (revisión 4.1) | Ahora (4.2) |
|---|---|---|
| 1 | Incidencias SoT = `arrives` Incident (`Text_IncidencesRequired_YN=Y`) | SoT = S2 GTFS-RT `servicealerts/proto`; arrives con `Incidences=N` ([ADR-011](adr/ADR-011-disruption-sot-is-gtfs-rt-servicealerts-not-arrive-incident.md), [ADR-010](adr/ADR-010-eta-sot-is-post-arrives-only.md)) |
| 2 | Gold = `gold_parada_linea`; ETA de 1 slot; `incident_*` | Gold = `gold_emt_stop_line`; ETA `eta_seconds_1/2` + `bus_id_1/2`; `alert_*` ([ADR-015](adr/ADR-015-medallion-physical-schema-one-bronze-one-silver-one-gold-tab.md), [ADR-022](adr/ADR-022-gold-eta-exposes-two-slots-under-one-table-constraint.md), [ADR-027](adr/ADR-027-alerts-denormalized-onto-gold-rows-at-line-grain-under-one-t.md)) |
| 3 | Freq = `freq_observed_minutes` + `freq_window_desc` | `freq_observed_weekday/weekend_min` + `freq_sample_size_*`; sin `freq_window_desc` ([ADR-023](adr/ADR-023-gold-frequency-windows-weekday-weekend-with-sample-sizes-no-.md)) |
| 4 | Silver con columnas `incident_*` | Silver **sin** alert; historial de polls + `day_type` + `map_ok` ([ADR-016](adr/ADR-016-silver-is-append-only-poll-fact-wide-rows-not-polymorphic-re.md)) |
| 5 | Bronze solo arrives | Bronze = S1 REST + S2 RT (JSON); GTFS no entra en Bronze ([ADR-017](adr/ADR-017-bronze-holds-rest-and-rt-payloads-only-gtfs-bootstraps-silve.md), [ADR-018](adr/ADR-018-bronze-contract-uuid-ingest-id-and-no-enforced-column-types.md)) |
| 6 | Paso = GTFS bootstrap | Paso = S1 line stops SoT; path → `direction_id`; Arrive `destination` → dirección ([ADR-009](adr/ADR-009-served-stop-sot-is-s1-line-stops-path-not-gtfs-alone.md), [ADR-026](adr/ADR-026-map-arrive-destination-to-direction-id-require-path-mapping-.md)) |
| 7 | Semantic / KPI como parte del contrato de datos | Fuera del esquema físico de dominio ([ADR-031](adr/ADR-031-semantic-model-kpi-and-quality-logs-stay-outside-emt-domain-.md)) |

**Geofence, poll sin bus, frecuencia observada (sin GTFS planificado) y documento autocontenido** se mantienen.

---

## 1. Ámbito y geofence (cerrado)

([ADR-007](adr/ADR-007-geographic-scope-puerta-del-sol-geofence-600m-with-52-in-sco.md), [ADR-006](adr/ADR-006-product-scope-emt-city-bus-rest-plus-gtfs-rt-service-alerts-.md))

- **Centro:** Puerta del Sol — lat `40.416729`, lon `-3.703339`
- **Método:** radio circular (Haversine)
- **Radio:** **600 metros**
- **Regla `in_scope`:** parada `≤ 600m` → `true`. Una línea es `true` si pasa por al menos una parada in-scope.
- **Resultado confirmado:** **52** paradas in-scope
- **Perfil de usuario:** turista / persona en la zona preguntando por buses cercanos
- **Timezone:** `Europe/Madrid` ([ADR-008](adr/ADR-008-timezone-europe-madrid-for-calendar-day-type-and-alert-activ.md))

---

## 2. Historias de usuario cubiertas

| US | Pregunta tipo | Cubierta por |
|---|---|---|
| US-01 | ¿Cuánto tarda la línea X en llegar a la parada Y? | `gold_emt_stop_line` (`eta_seconds_1/2`, `has_upcoming_bus`); sin paso = sin fila |
| US-02 | ¿Qué autobuses llegan ahora a la parada Y? | `gold_emt_stop_line` (varias filas por `stop_id`; máx. 2 ETA por línea) |
| US-03 | ¿Qué líneas pasan por la parada Y (por nombre)? | Búsqueda nombre→`stop_id` en app/Agent (GTFS + refuerzo o Gold `stop_name`); sin cambio de esquema ([ADR-033](adr/ADR-033-us-03-name-resolution-may-stay-outside-gold-no-schema-change.md)) |
| US-04 (control) | Fuera de alcance / dato insuficiente → "no lo sé" | Incluye freq NULL; nunca inventar |
| US-07 | ¿Hay incidencias activas en la línea X? | `gold_emt_stop_line` (`alert_*`, replicado por `line_id`) |
| US-08 | ¿Cada cuánto pasa la línea X? | `gold_emt_stop_line` (`freq_observed_*`, `freq_sample_size_*`, `day_type`) |

US-05 (chat) y US-06 quedan fuera del dominio Fabric de este contrato.

---

## 3. Fuera de alcance

([ADR-006](adr/ADR-006-product-scope-emt-city-bus-rest-plus-gtfs-rt-service-alerts-.md), [ADR-036](adr/ADR-036-no-peak-or-off-peak-labels-no-daily-total-vehicle-counts-in-.md))

- Usar Incident de `arrives` como SoT de incidencias
- Cuerpo JSON del MDB Catalog API; GTFS frequencies / EMT Frequency* como SoT de frecuencia
- `deviation` / `positionTypeBus` / `isHead`
- Retraso vs horario teórico (sin enlace `bus_id`↔`trip_id`; sin TripUpdates)
- Ocupación, tarifas, billetes; Metro / Cercanías / otros consorcios
- Paradas/líneas fuera del geofence
- Etiquetas de pico, flota diaria total, log de calidad US-06, KPI, detalle Semantic (fuera del esquema físico)
- Columnas alert en Silver; doble almacenamiento Bronze raw `.pb`; columna `in_scope` en Gold; `direction_path` / `direction_code`; `freq_window_desc`

---

## 4. Arquitectura — 3 tablas físicas, roles distintos

([ADR-015](adr/ADR-015-medallion-physical-schema-one-bronze-one-silver-one-gold-tab.md), [ADR-005](adr/ADR-005-source-taxonomy-s1-rest-only-s2-rt-servicealerts-s3-gtfs.md), [ADR-029](adr/ADR-029-polling-cadences-arrives-60s-try-and-adjust-rt-300s.md))

| Código | Significado |
|--------|-------------|
| **S1** | EMT OpenAPI (**solo REST**) |
| **S2** | mdb-3102 GTFS-RT **`servicealerts/proto`** (+ meta del catalog). Aunque el host sea EMT → **S2** |
| **S3** | GTFS static |

| Concepto | Primary | Fallback | No usado |
|----------|---------|----------|----------|
| Maestro de paradas | **S3** GTFS `stops` | Nombre/dirección S1 | S2 Catalog JSON |
| ID de línea | S1 `line` = S3 `route_id` | — | S2 Catalog JSON |
| ETA | **S1** `arrives` | Ninguno | S3, S2 |
| Paso · seed | **S1** line stops | Atributos GTFS (nombre·coords) | S2 |
| Incidencias | **S2** proto | Ninguno | S1 Incident, S2 Catalog JSON |
| Frecuencia | **Observación poll Silver** | Ninguno | GTFS freq, EMT Frequency* |
| day type | **S1** calendar | GTFS calendar | — |

```mermaid
flowchart LR
  S1[S1_EMT_OpenAPI]
  S2[S2_mdb3102_RT]
  S3[S3_GTFS_zip]
  B[bronze_emt_raw]
  S[silver_emt]
  G[gold_emt_stop_line]
  S1 --> B
  S2 --> B
  S3 --> S
  B --> S
  S --> G
```

GTFS (S3) bootstrap → Silver directamente (no entra en Bronze). Semantic / Data Agent leen Gold ([ADR-031](adr/ADR-031-semantic-model-kpi-and-quality-logs-stay-outside-emt-domain-.md)).

**Frecuencia de actualización**

| Fuente | Frecuencia | Notas |
|--------|------------|-------|
| GTFS + seed S1 line stops | 1×/día | Paso alineado con S1 |
| S1 calendar | 1×/día | Material para `day_type` |
| S1 `arrives` | Ideal **60s** | Mantener·intentar. `is_stale` = 180s fijo |
| S2 `servicealerts` | **300s** | |

- **Bronze:** carga bruta S1/S2; sin forzar tipos ni NOT NULL.
- **Silver:** historial append-only de polls; fuente para reconstruir Gold y calcular frecuencia.
- **Gold:** una fila por `(stop_id, line_id, direction_id)` in-scope con paso S1; estado reciente + agregados.

### Pipeline

1. **1×/día:** atributos GTFS + S1 line stops → seed `silver_emt` · `catalog_loaded_at`
2. **1×/día:** S1 calendar → Bronze → Silver/Gold `day_type`
3. **~60s:** S1 `arrives` → Bronze → append Silver (`_rk`, resolve label, `destination`→`direction_id`)
4. **300s:** S2 `.pb` → JSON → Bronze → al ensamblar Gold, MERGE `alert_*` por `line_id`
5. Desde Silver: freq `line_id`+ventana + último poll (ETA 1·2) → MERGE `gold_emt_stop_line`

---

## 5. Diagrama del esquema físico completo

Tres tablas Delta (`lh_emt_madrid`). Relaciones lógicas de pipeline (no FK físicas obligatorias). Detalle de columnas y reglas: §6–§8.

```mermaid
erDiagram
  bronze_emt_raw {
    string ingest_id
    timestamp ingested_at
    string source_system
    string resource_kind
    string resource_key
    int http_status
    string api_code
    string api_description
    string payload
    string content_sha256
    string timezone_note
  }

  silver_emt {
    string _rk PK
    string stop_id
    string line_id
    string line_label
    int direction_id
    string bus_id
    string destination
    int eta_seconds
    timestamp datetime_polling
    timestamp ingested_at
    string stop_name
    double stop_lat
    double stop_lon
    string direction_text
    string name_a
    string name_b
    boolean is_terminus
    date catalog_loaded_at
    string day_type
    boolean map_ok
  }

  gold_emt_stop_line {
    string stop_id PK
    string line_id PK
    int direction_id PK
    string line_label
    string stop_name
    string direction_text
    string name_a
    string name_b
    string destination
    int eta_seconds_1
    string bus_id_1
    int eta_seconds_2
    string bus_id_2
    boolean has_upcoming_bus
    boolean is_stale
    boolean origin_stop_notice
    boolean is_terminus
    date catalog_loaded_at
    string day_type
    timestamp updated_at
    double freq_observed_weekday_min
    double freq_observed_weekend_min
    int freq_sample_size_weekday
    int freq_sample_size_weekend
    boolean alert_active
    string alert_header
    string alert_cause
    string alert_effect
    string alert_url
  }

  bronze_emt_raw ||--o{ silver_emt : "transform / append polls"
  silver_emt ||--o| gold_emt_stop_line : "MERGE último poll + freq + alert"
```

| Tabla | Grain | Rol |
|-------|-------|-----|
| `bronze_emt_raw` | `(ingest_id, resource_kind, resource_key)` | Crudo S1+S2 |
| `silver_emt` | 1 poll `(stop_id, line_id, direction_id)` · PK `_rk` | Historial; sin alert |
| `gold_emt_stop_line` | PK `(stop_id, line_id, direction_id)` | Serving agente |

---

## 6. Capa Bronze: `bronze_emt_raw`

([ADR-017](adr/ADR-017-bronze-holds-rest-and-rt-payloads-only-gtfs-bootstraps-silve.md), [ADR-018](adr/ADR-018-bronze-contract-uuid-ingest-id-and-no-enforced-column-types.md))

**Propósito:** carga en bruto de S1 REST y S2 RT. **GTFS no entra en Bronze.**

**Grain:** una recolección = `(ingest_id, resource_kind, resource_key)`.  
Ej.: `arrives:86`, `servicealerts:proto`, `calendar:20260720`, `line_stops:027:1`.

**Body de request `arrives`** ([ADR-010](adr/ADR-010-eta-sot-is-post-arrives-only.md)):

```json
{
  "cultureInfo": "es",
  "Text_StopRequired_YN": "Y",
  "Text_EstimationsRequired_YN": "Y",
  "Text_IncidencesRequired_YN": "N"
}
```

Sin `Text_LineInfoRequired_YN` (no está en el esquema oficial). Con Incidences=`N` no hacen falta campos DateTime de incidencias.

| column | Descripción |
|--------|-------------|
| `ingest_id` | UUID |
| `ingested_at` | Momento de ingestión |
| `source_system` | `EMT_OPENAPI` \| `MDB_GTFS_RT` |
| `resource_kind` | `arrives` \| `servicealerts` \| `calendar` \| `line_stops` … |
| `resource_key` | stopId / proto / fecha, etc. |
| `http_status` | Estado HTTP |
| `api_code` / `api_description` | Envelope S1 (si aplica) |
| `payload` | S1: JSON. S2: `.pb` → guardar **después de decodificar a JSON** |
| `content_sha256` | Hash del payload |
| `timezone_note` | `Europe/Madrid` |

**Deduplicación:** append-only. Se permite re-ingestar el mismo hash.

---

## 7. Capa Silver: `silver_emt`

([ADR-016](adr/ADR-016-silver-is-append-only-poll-fact-wide-rows-not-polymorphic-re.md), [ADR-019](adr/ADR-019-direction-grain-key-is-direction-id-only.md), [ADR-020](adr/ADR-020-stop-id-stored-as-string-for-stability-and-portability.md), [ADR-021](adr/ADR-021-line-id-vs-line-label-and-failed-arrive-label-resolution-exc.md))

**Propósito:** fact de historial de polls. Material de frecuencia observada. Fuera del alcance del Data Agent. **Sin** columnas alert (POC).

**Grain / PK:** una fila = 1 poll de `(stop_id, line_id, direction_id)` in-scope (con o sin bus).

```text
_rk = SHA256(
  stop_id | line_id | coalesce(direction_id,'') | coalesce(bus_id,'') | datetime_polling
)
```

| column | data type | Origen / derivado | Regla NULL |
|--------|-----------|-------------------|------------|
| `_rk` | string | PK | NOT NULL |
| `stop_id` | string | S3/S1 | NOT NULL |
| `line_id` | string | ID interno resuelto | NOT NULL |
| `line_label` | string | Arrive `line` / maestro | NOT NULL |
| `direction_id` | int | GTFS `0`\|`1` | grain; empty → bootstrap fail-fast |
| `bus_id` | string | Arrive `bus` | NULL = sin bus |
| `destination` | string | Arrive | NULL si no hay bus |
| `eta_seconds` | int | Arrive `estimateArrive` | NULL si no hay bus |
| `datetime_polling` | timestamp | Momento del poll | NOT NULL |
| `ingested_at` | timestamp | Bronze | NOT NULL |
| `stop_name` / `stop_lat` / `stop_lon` | — | GTFS denorm | |
| `direction_text` | string | GTFS | NULL permitido |
| `name_a` / `name_b` | string | Catálogo | NULL permitido |
| `is_terminus` | boolean | Catálogo | |
| `catalog_loaded_at` | date | Día del snapshot | |
| `day_type` | string | S1 calendar `LA`\|`SA`\|`FE` | Día del poll |
| `map_ok` | boolean | Resolve label→line_id | false → excluido de Gold |

| `direction_id` | Significado |
|----------------|-------------|
| `0` | GTFS 0 ↔ path EMT `…/stops/1/` (medido en 027·014) ([ADR-004](adr/ADR-004-close-emt-path-a-b-vs-gtfs-direction-id-mapping-for-lines-02.md)) |
| `1` | Sentido contrario |

| `day_type` | Significado |
|------------|-------------|
| `LA` | Laborable |
| `SA` | Sábado |
| `FE` | Festivo/domingo |

### Reglas de `silver_emt`

1. **Seed:** insertar `(stop_id, line_id, direction_id)` in-scope. Conjunto de paso = alineado con **S1 line stops SoT**. path `1` → `direction_id=0`, path `2` → `direction_id=1` (**obligatorio**). Nombre·coords pueden denormalizarse desde GTFS ([ADR-009](adr/ADR-009-served-stop-sot-is-s1-line-stops-path-not-gtfs-alone.md)).
2. **Sin paso:** no hay combinación → no hay fila Gold.
3. **Poll without bus:** cargar fila con `bus_id` NULL.
4. **Poll with bus:** 1 fila por vehículo (`bus_id` en `_rk`). En la práctica, máx. **2 buses** por mismo stop×label. Arrive no trae direction → **`destination` ≈ `name_b` → `direction_id=0`**, **`≈ name_a` → `1`**. Si falla el match, prohibido actualizar a ciegas ambas direcciones en Gold ([ADR-026](adr/ADR-026-map-arrive-destination-to-direction-id-require-path-mapping-.md)).
5. **Fallo de resolve de label:** `map_ok=false` — excluido del MERGE a Gold ([ADR-021](adr/ADR-021-line-id-vs-line-label-and-failed-arrive-label-resolution-exc.md)).

**Deduplicación:** append-only, `_rk` idempotente.

**Nota:** denormalización a propósito (nombre, coords, etc. por fila). Con ~52 paradas el volumen es chico; cero joins para servir Gold/agente pesa más que el almacenamiento en PoC.

---

## 8. Capa Gold: `gold_emt_stop_line`

([ADR-015](adr/ADR-015-medallion-physical-schema-one-bronze-one-silver-one-gold-tab.md), [ADR-022](adr/ADR-022-gold-eta-exposes-two-slots-under-one-table-constraint.md), [ADR-027](adr/ADR-027-alerts-denormalized-onto-gold-rows-at-line-grain-under-one-t.md), [ADR-028](adr/ADR-028-freshness-is-stale-after-180-seconds-no-gold-in-scope-column.md))

**Propósito:** serving US-01/02/03/07/08. Tabla de dominio que lee el Data Agent.

**PK = `(stop_id, line_id, direction_id)`**  
Una fila por combinación in-scope·paso S1 alineado, con o sin bus. Sin filas de dirección indeterminada.

| column | data type | Origen / derivado | Regla NULL |
|--------|-----------|-------------------|------------|
| `stop_id` | string | — | NOT NULL · **PK** |
| `line_id` | string | — | NOT NULL · **PK** |
| `direction_id` | int | `0`\|`1` | NOT NULL · **PK** |
| `line_label` | string | — | NOT NULL |
| `stop_name` | string | — | NOT NULL |
| `direction_text` | string | — | NULL permitido |
| `name_a` / `name_b` | string | — | NULL permitido |
| `destination` | string | Último poll (1.º bus) | NULL si no hay bus |
| `eta_seconds_1` | int | **ETA mínimo** del último poll del mismo grain | NULL si no hay |
| `bus_id_1` | string | Vehículo de `eta_seconds_1` | NULL si no hay |
| `eta_seconds_2` | int | Segundo ETA más rápido | NULL si solo hay 1 |
| `bus_id_2` | string | Vehículo de `eta_seconds_2` | NULL si no hay |
| `has_upcoming_bus` | boolean | `eta_seconds_1 IS NOT NULL` | NOT NULL |
| `is_stale` | boolean | `(now - updated_at) > 180s` | NOT NULL |
| `origin_stop_notice` | boolean | `is_terminus AND eta_seconds_1 IS NULL` | NOT NULL |
| `is_terminus` | boolean | — | NOT NULL |
| `catalog_loaded_at` | date | — | NOT NULL |
| `day_type` | string | Hoy S1 calendar `LA`\|`SA`\|`FE` | NOT NULL |
| `updated_at` | timestamp | Último poll | NOT NULL |
| `freq_observed_weekday_min` | double | Mediana (min) de intervalos observados `line_id`+ventana LA | NULL si &lt; 20 · replicado por línea |
| `freq_observed_weekend_min` | double | Igual fórmula `line_id`+ventana SA/FE | NULL si &lt; 20 · replicado por línea |
| `freq_sample_size_weekday` | int | Nº observaciones válidas line·LA | Replicado por línea |
| `freq_sample_size_weekend` | int | Nº observaciones válidas line·SA/FE | Replicado por línea |
| `alert_active` | boolean | S2 `active_period` vs now | NOT NULL |
| `alert_header` | string | S2 | NULL si inactivo |
| `alert_cause` | string | S2 | NULL si inactivo |
| `alert_effect` | string | S2 | NULL si inactivo |
| `alert_url` | string | S2 | NULL si inactivo |

**Contrato `alert_*`:** atributo a nivel `line_id` **replicado** en cada fila stop×direction. No es incidencia por parada. Prohibido join por RT `stop_id`.

**Contrato `freq_*`:** grain de agregación = **`line_id` + ventana**. No por stop×direction. **Mismo valor replicado** en todas las filas Gold del mismo `line_id`.

**Deduplicación:** MERGE on PK.

**Tratamiento de NULL**

- Sin bus → `eta_*` / `bus_id_*` NULL, `has_upcoming_bus=false`.
- `alert_active=false` → textos alert NULL.
- freq NULL → historial insuficiente.
- Sin paso → no hay fila.

**No va en Gold:** `in_scope`, `freq_window_desc`, picos, flota diaria, Incident, log de calidad, KPI, Semantic, `direction_path`/`direction_code`.

---

## 9. Modelo semántico y KPIs (fuera del esquema físico)

([ADR-031](adr/ADR-031-semantic-model-kpi-and-quality-logs-stay-outside-emt-domain-.md))

El esquema físico de dominio termina en `gold_emt_stop_line`. Semantic Model, medidas de negocio, logs de calidad y KPIs **no** forman parte de este contrato de columnas.

Orientación no vinculante para quien monte el Semantic sobre Gold:

| Nombre de negocio (ejemplo) | Columna en gold |
|---|---|
| Minutos estimados (1.er bus) | `eta_seconds_1 / 60` si `has_upcoming_bus` |
| Hay autobús | `has_upcoming_bus` |
| Dato obsoleto | `is_stale` |
| Aviso cabecera | `origin_stop_notice` |
| Alerta activa | `alert_active` |
| Descripción alerta | `alert_header` (solo si activa) |
| Frecuencia laborable / fin de semana | `freq_observed_weekday_min` / `freq_observed_weekend_min` (NULL → "no tengo ese dato todavía") |

**KPIs** — placeholder; no se inventan umbrales aquí. Candidatos con stakeholder: % respondidas sin "no lo sé", precisión vs app oficial, latencia, uptime del poll, cobertura in-scope fresca.

---

## 10. Reglas de negocio — US-08 (frecuencia observada)

([ADR-012](adr/ADR-012-frequency-sot-is-observed-silver-polls-with-no-planned-fallb.md), [ADR-024](adr/ADR-024-observed-frequency-aggregation-grain-is-line-id-plus-day-typ.md), [ADR-025](adr/ADR-025-observed-headway-formula-is-median-of-successive-gaps-in-min.md), [ADR-030](adr/ADR-030-frequency-response-gate-20-observations-preferred-24h-warmup.md))

**Decisión cerrada:** frecuencia = agregación del historial real de `silver_emt`. Nunca GTFS planificado ni Frequency* de EMT. Sin historial suficiente → US-04 ("no lo sé"), sin fallback silencioso.

- Solo Silver con `bus_id IS NOT NULL` cuenta como observación válida. Mismo poll bucket·mismo `bus_id` = 1 vez.
- Grain de agregación: **`line_id` + ventana** (weekday=`LA`, weekend=`SA`\|`FE`).
- Fórmula: timestamps válidos ordenados → **mediana** de intervalos consecutivos (min) → `freq_observed_*_min`.
- Sample de la ventana **&lt; 20** → ese `freq_observed_*` = NULL.
- Warm-up operativo recomendado **24h**. Gate de respuesta: prioridad a **20 muestras**.
- Agent: si no se indica día → elegir ventana con `day_type`; si se dice “laborable/fin de semana” → columna correspondiente.

**Formato de respuesta:** *"la M1 pasa cada 8 minutos entre semana"* / *"cada 12 minutos los fines de semana"*.

---

## 11. Incidencias (US-07) — S2 servicealerts

([ADR-011](adr/ADR-011-disruption-sot-is-gtfs-rt-servicealerts-not-arrive-incident.md), [ADR-027](adr/ADR-027-alerts-denormalized-onto-gold-rows-at-line-grain-under-one-t.md), [ADR-008](adr/ADR-008-timezone-europe-madrid-for-calendar-day-type-and-alert-activ.md))

**Fuente de verdad:** S2 GTFS-RT `servicealerts/proto` (poll ~300s). **No** usar Incident embebido en `arrives`.

- Ingestión: `.pb` → JSON → `bronze_emt_raw` → al MERGE de Gold, proyectar `alert_*` por `line_id`.
- `alert_active`: `true` si `now` (Europe/Madrid) cae en `active_period` del alert S2.
- Textos (`alert_header`, `alert_cause`, `alert_effect`, `alert_url`) NULL cuando inactivo.
- Semántica: atributo de **línea**, replicado en cada fila stop×direction del mismo `line_id`. No join por `stop_id` del RT.

El body de `arrives` permanece con `Text_IncidencesRequired_YN=N` (ver §6); ETA no depende de incidencias.

---

## 12. Pendientes reales antes de implementar

- [ ] Validar el umbral de 20 observaciones para `freq_observed_*` con los primeros días de datos reales ([ADR-030](adr/ADR-030-frequency-response-gate-20-observations-preferred-24h-warmup.md))
- [ ] Reportar intervalo real de arrives en producción (ideal 60s) ([ADR-029](adr/ADR-029-polling-cadences-arrives-60s-try-and-adjust-rt-300s.md))
- [ ] Definir KPIs con el stakeholder (fuera del esquema físico — [ADR-031](adr/ADR-031-semantic-model-kpi-and-quality-logs-stay-outside-emt-domain-.md))
- [ ] Almacenamiento Azure · región: **UNVERIFIED**
