# Contexto: Data Agent + Semantic → Eventhouse

**Fecha:** 2026-07-24  
**Público:** quien configure Data Agent y/o la capa semántica  
**Contrato lógico:** [data-source-contract-v4.md](./data-source-contract-v4.md) v4.3.1 

---

## Resumen

El hot path ya escribe en **Eventhouse**. El Data Agent (y el semantic layer) deben usar como SoT **`gold_emt_stop_line` en Eventhouse**, no el gold del Lakehouse.

El esquema lógico (columnas, grain, US) **no cambia**. Solo cambia la ubicación física del serving.

No hace falta comparar Lakehouse gold vs Eventhouse gold antes de trabajar: silver y gold en EH ya están disponibles.

---

## Arquitectura actual

```text
[1×/día]  Notebook bootstrap GTFS → Lakehouse silver_arrives (catálogo)
                 ↑
          La UDF solo LEE el catálogo / scope vía SQL del Lakehouse

[Hot path]
  UDF (login EMT + arrives / servicealerts)
    → Eventstream 
    → Eventhouse:
         bronze_emt_raw
         silver_arrives
         silver_alerts
    → KQL apply gold
         gold_emt_stop_line   ← SoT para Agent / Semantic
```

| Componente | Dónde | Ubicación |
|------------|--------|----------|
| Bootstrap GTFS | Lakehouse (pipeline + notebook), ~09:00 | base/nb_bootstrap_gtfs_silver_0 |
| Lectura de catálogo / scope | Lakehouse (`silver_arrives`) — solo la UDF | ./lh_emt_madrid |
| Ingesta arrives / alerts | UDF → Eventstream → Eventhouse | phase4/udf_emt_ingest <br>phase4/es_emt_* <br>phase4/eh_emt_madrid/db_emt |
| Serving Agent / Semantic | **Eventhouse `gold_emt_stop_line`** | |
| Rollback (path antiguo) | Lakehouse — no es SoT del Agent | |

---

## Tablas en Eventhouse (nombres = contrato)

En el explorador KQL verás **cuatro tablas** con estos nombres. Eso es correcto.

| Tabla | Rol | ¿La ve el Agent? |
|-------|-----|------------------|
| `bronze_emt_raw` | Raw ingest | **No** |
| `silver_arrives` | Hechos de poll / material de frecuencia | **No** |
| `silver_alerts` | Snapshot de alertas | **No** |
| `gold_emt_stop_line` | Serving (US-01, 02, 07, 08, …) | **Sí — único SoT de dominio** |

Nombres de ítem por defecto en docs (ajustar al portal si difieren):

- Eventhouse: `eh_emt_madrid`
- Base KQL: `db_emt`

---

## Trabajo Data Agent

1. Conectar el datasource al KQL DB de Eventhouse y exponer **`gold_emt_stop_line`** (o un semantic que solo lea esa tabla).
2. **No** conectar bronze ni silver al Agent ([ADR-031](adr/ADR-031-semantic-model-kpi-and-quality-logs-stay-outside-emt-domain-.md)).
3. Few-shots / instrucciones: mismas columnas que el contrato:
   - ETA: `eta_seconds_1/2`, `bus_id_1/2`, `has_upcoming_bus`, `is_stale`
   - Alertas: `alert_active`, `alert_header`, `alert_cause`, `alert_effect`, `alert_url` (grano `line_id`, replicado por fila stop×direction)
   - Frecuencia: `freq_observed_*`, `freq_sample_size_*`, `day_type`
   - PK: `(stop_id, line_id, direction_id)`
4. `is_stale`: el apply actual usa **900 s** (`gold_emt_stop_line_build(900)` en `rti/kql/06_apply_gold.kql`). El contrato ADR-028 habla de **180 s**. Alinear expectativas del Agent al valor real del apply (o cambiar el apply a 180 más adelante).

---

## Trabajo capa semántica (Semantic)

1. Construir **encima** de Eventhouse `gold_emt_stop_line`.
2. No meter KPI / quality logs dentro de las columnas de dominio Gold ([ADR-031](adr/ADR-031-semantic-model-kpi-and-quality-logs-stay-outside-emt-domain-.md)).
3. Si el Agent lee el Semantic: el Semantic apunta a **EH gold**, no al Lakehouse.
4. No exponer Silver en el Semantic de serving.
5. Consultar la historia de usuario: [enlace](https://docs.google.com/document/d/16bHtctB5ErOt3-3k4wkkNDAG9nX1HqJzbdtSrEMEPpI/edit?tab=t.psozsyssj9on#heading=h.uf0ozq2nmxrg)


---

## Referencias en el repo

| Documento / código | Uso |
|--------------------|-----|
| [data-source-contract-v4.md](./data-source-contract-v4.md) | Columnas, grain, US |
| [phase4-rti.md](./phase4-rti.md) | Operación UDF / Eventstream / EH |
| [ADR-031](adr/ADR-031-semantic-model-kpi-and-quality-logs-stay-outside-emt-domain-.md) | Semantic fuera del Gold de dominio |
| `rti/kql/01`–`06` | DDL, gold build, apply |
| `rti/udf/udf_emt_ingest.py` | Poller → Eventstream |

---

*Documento de handoff para el equipo. Actualizar nombres de Eventhouse/DB si el portal difiere de los defaults.*
