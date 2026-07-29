# Contexto: Data Agent + Semantic → Eventhouse

**Fecha:** 2026-07-28  
**Público:** quien configure Data Agent y/o la capa semántica  
**Contrato lógico:** [data-source-contract-v4.md](./data-source-contract-v4.md) **v4.4**

---

## Resumen

El hot path ya escribe en **Eventhouse**. El Data Agent (y el semantic layer) deben usar como SoT **`gold_emt_stop_line` en Eventhouse**, no el gold del Lakehouse.

Grain y ownership arrives/alerts **igual**. Desde **v4.4** Gold también sirve **coordenadas de mapa** (`stop_lat`/`stop_lon`, `bus_lat_1/2`, `bus_lon_1/2`) para el mapa 3D / frontend sin mocks estáticos. Detalle operativo: [phase4-rti.md](./phase4-rti.md).

No hace falta comparar Lakehouse gold vs Eventhouse gold antes de trabajar: silver y gold en EH ya están disponibles. Las columnas de mapa están **primero en EH**; parity Lakehouse no es requisito del Agent.

---

## Arquitectura actual

> **Phase 5 (en curso):** el catálogo pasa de Lakehouse a seeds en Eventhouse  
> (`emt_record=silver_arrives_seed` vía `es_emt_arrives_silver`). Guía: [phase4-rti.md](./phase4-rti.md) Steps A–G.  
> Hasta Step E, la UDF puede seguir leyendo LH; después `poll_*_scope_eh` + SQL endpoint.

```text
[1×/día]  nb_bootstrap_eh_silver → es_emt_arrives_silver → silver_arrives (seed)
          (rollback: nb_bootstrap_gtfs_silver → Lakehouse silver_arrives)

[Hot path]
  UDF poll_*_scope[_eh] (login EMT + arrives / servicealerts)
    → Eventstream
    → Eventhouse:
         bronze_emt_raw
         silver_arrives   (+ bus_lat/bus_lon desde Arrive.geometry; seeds tagged)
         silver_alerts
    → KQL apply gold (excluye silver_arrives_seed)
         gold_emt_stop_line   ← SoT para Agent / Semantic / mapa
```

| Componente | Dónde | Ubicación |
|------------|--------|----------|
| Bootstrap GTFS (Phase 5) | Notebook → Eventstream silver | `nb_bootstrap_eh_silver` |
| Bootstrap GTFS (rollback) | Lakehouse notebook | `nb_bootstrap_gtfs_silver` |
| Lectura de catálogo / scope | EH Kusto REST tras Step E; LH dual-run antes | `poll_*_scope_eh` / `poll_*_scope` |
| Ingesta arrives / alerts | UDF → Eventstream → Eventhouse | `udf-emt-ingest` · `es_emt_*` · `eh_emt_madrid`/`db_emt` |
| Serving Agent / Semantic / mapa | **Eventhouse `gold_emt_stop_line`** | |
| Rollback (path antiguo) | Lakehouse — no es SoT del Agent | |

---

## Tablas en Eventhouse (nombres = contrato)

En el explorador KQL verás **cuatro tablas** con estos nombres. Eso es correcto.

| Tabla | Rol | ¿La ve el Agent? |
|-------|-----|------------------|
| `bronze_emt_raw` | Raw ingest | **No** |
| `silver_arrives` | Hechos de poll / material de frecuencia (+ coords bus) | **No** |
| `silver_alerts` | Snapshot de alertas | **No** |
| `gold_emt_stop_line` | Serving (US-01, 02, 07, 08, mapa, …) | **Sí — único SoT de dominio** |

Nombres de ítem por defecto en docs (ajustar al portal si difieren):

- Eventhouse: `eh_emt_madrid`
- Base KQL: `db_emt`

---

## Trabajo Data Agent

1. Conectar el datasource al KQL DB de Eventhouse y exponer **`gold_emt_stop_line`** (o un semantic que solo lea esa tabla).
2. **No** conectar bronze ni silver al Agent ([ADR-031](adr/ADR-031-semantic-model-kpi-and-quality-logs-stay-outside-emt-domain-.md)).
3. Few-shots / instrucciones: mismas columnas que el contrato v4.4:
   - ETA: `eta_seconds_1/2`, `bus_id_1/2`, `has_upcoming_bus`, `is_stale`
   - Mapa: `stop_lat`/`stop_lon`; buses vivos `bus_lat_1`/`bus_lon_1`, `bus_lat_2`/`bus_lon_2` (asociados a `bus_id_1/2`; NULL si no hay geometry)
   - Alertas: `alert_active`, `alert_header`, `alert_cause`, `alert_effect`, `alert_url` (grano `line_id`, replicado por fila stop×direction)
   - Frecuencia: `freq_observed_*`, `freq_sample_size_*`, `day_type`
   - PK: `(stop_id, line_id, direction_id)`
4. `is_stale`: el apply actual usa **900 s** (`gold_emt_stop_line_build(900)` en `rti/kql/06_apply_gold.kql`). El contrato ADR-028 habla de **180 s**. Alinear expectativas del Agent al valor real del apply (o cambiar el apply a 180 más adelante).
5. Coords: lat ≈ 40.4x, lon ≈ −3.7x en el geofence Sol. Si el Agent/mapa ve lon/lat intercambiados, el bug es de consumo (API = `[lon, lat]`).

---

## Trabajo capa semántica (Semantic)

1. Construir **encima** de Eventhouse `gold_emt_stop_line`.
2. No meter KPI / quality logs dentro de las columnas de dominio Gold ([ADR-031](adr/ADR-031-semantic-model-kpi-and-quality-logs-stay-outside-emt-domain-.md)).
3. Si el Agent lee el Semantic: el Semantic apunta a **EH gold**, no al Lakehouse.
4. No exponer Silver en el Semantic de serving.
5. Incluir medidas/columnas de mapa si el producto 3D las necesita (`stop_*`, `bus_*_1/2`).
6. Consultar la historia de usuario: [enlace](https://docs.google.com/document/d/16bHtctB5ErOt3-3k4wkkNDAG9nX1HqJzbdtSrEMEPpI/edit?tab=t.psozsyssj9on#heading=h.uf0ozq2nmxrg)

---

## Ops note (schema evolve)

Tras añadir columnas a Gold en KQL: `.create-merge` **añade al final**. Si el `project` del build usa otro orden, `.set-or-replace` falla con *Query schema does not match table schema*. Remedio: drop + recrear `gold_emt_stop_line` con `rti/kql/04` y volver a apply (Silver intacto; Gold es rebuild). Ver [phase4-rti.md](./phase4-rti.md).

---

## Referencias en el repo

| Documento / código | Uso |
|--------------------|-----|
| [data-source-contract-v4.md](./data-source-contract-v4.md) | Columnas, grain, US (v4.4) |
| [phase4-rti.md](./phase4-rti.md) | Operación UDF / Eventstream / EH / map coords deploy |
| [ADR-031](adr/ADR-031-semantic-model-kpi-and-quality-logs-stay-outside-emt-domain-.md) | Semantic fuera del Gold de dominio |
| `rti/kql/01`–`06` | DDL, gold build, apply |
| `rti/udf/udf_emt_ingest.py` | Poller → Eventstream |

---

*Documento de handoff para el equipo. Actualizar nombres de Eventhouse/DB si el portal difiere de los defaults.*
