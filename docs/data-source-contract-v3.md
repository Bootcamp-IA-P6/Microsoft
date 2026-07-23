# Contrato de Origen de Datos: Proyecto EMT Madrid (Sol / Gran Vía)
**Versión:** 3.1
**Fecha de actualización:** 2026-07-17
**Estado:** ✅ Cerrado (salvo Fase 2 MVP = sólo bronze/silver parcial, ver sección 8)

---

## 0. Qué cambió de v2 a v3

| # | Cambio |
|---|---|
| 1 | Reincorporamos `silver_arrival_observations`, `silver_stops_dim`, `silver_lines_dim` (necesarias para MVP) |
| 2 | `silver_incidents` y `gold_incident_line_current` confirmados como **postergados** (US-05, no MVP) |
| 3 | `gold_line_status_5m` confirmado como **postergado** (agregados operacionales, Fase 3+) |
| 4 | Reemplazada la lógica de `position_type_bus` (no existe en v2) con `is_terminus` derivado del GTFS (`stop_sequence = 1` en `stop_times.txt`) |
| 5 | Explicitado el plan de construcción por fases (Fase 2 MVP vs Fase 3+) |

### Cambios v3.0 → v3.1

| # | Cambio |
|---|---|
| 1 | §10: eliminado `Text_LineInfoRequired_YN` del body de `arrives` — no figura en la documentación oficial EMT ([apidocs.emtmadrid.es](https://apidocs.emtmadrid.es/)); se había introducido por error en scripts internos. Los metadatos de línea en `StopInfo.lines[]` se obtienen con `Text_StopRequired_YN: "Y"`. |

---

## 1. Resumen y Ámbito

Contrato de datos para EMT Madrid Sol/Gran Vía (a definir), bajo el límite de **250.000 llamadas/día (N3)**.

### Zona (Z1, A4)

- **Definición operativa:** radio caminable (~700m desde Puerta del Sol) o polígono sobre eje Gran Vía–Sol (definir geofence exacto, Z2/Z5).
- **Perfil:** turista.
- **Funcionalidad MVP:**
  - US-03: "¿qué autobuses llegan a la parada donde estoy parado?"
  - D1: match de destino contra cabeceras de línea (sin ruteo a paradas intermedias).
  - US-01/US-02: ETA y validación que la línea pasa por la parada.

### Límites contractuales

- **No incluye:** voz (Fase 6), incidencias en MVP (US-05, Fase 3+), ruteo a paradas intermedias (out-of-scope).
- **Catálogo:** GTFS descargado de https://datos.crtm.es/datasets/868df0e58fca47e79b942902dffd7da0/about

---

## 2. Resolución del problema "nulos en cabecera" — sin `position_type_bus`

v2 proponía usar `position_type_bus` para distinguir "bus en cochera" de "no hay buses". El campo no existe en v2 de la API.

**Solución confirmada:** usar el GTFS `stop_times.txt` para identificar cabeceras:

- Cualquier parada con `stop_sequence = 1` en un viaje es **cabecera de origen** de esa línea (en esa dirección).
- Se llena una columna `is_terminus` en `silver_stop_lines`.
- Si `eta_seconds` es null en una **parada cabecera**, marcar `origin_stop_notice = true` ("origen de línea, estimación puede no ser precisa").
- Si es null en una **parada no-cabecera**, es un vacío real (`has_upcoming_bus = false`).

---

## 3. Regla de frescura 

- `gold` se reconstruye **solo desde** la última ronda exitosa de polling por parada.
- Si el último poll exitoso de una parada excede **3x el intervalo normal** (~3 min con polling de 60s), se marca `is_stale = true` y el agente comunica "dato desactualizado".

---

## 4. Distinción "sin buses ahora" vs. "línea no pasa aquí"

Usado `LEFT JOIN` contra `silver_stop_lines` (relación estática línea↔parada):

| Situación | Resultado |
|---|---|
| Línea en catálogo + con ETA en poll | Mostrar ETA |
| Línea en catálogo + sin ETA en poll | `has_upcoming_bus = false` ("no hay buses ahora") |
| Línea no en catálogo | Pregunta inválida (la línea no pasa por esa parada) |

---

## 5. Matriz de Alcance Excluido (US-04)

- Incidencias / causas de retraso (postergado a Fase 3+, ver sección 8).
- Ruteo a paradas intermedias no-cabecera.
- Ocupación de vehículos.
- Tarifas, pagos, billetes.
- Metro, Cercanías u otros consorcios.
- Horarios teóricos (solo tiempo real).
- Paradas/líneas fuera de geofence (`in_scope = false`).

---

## 6. Esquemas de datos — FASE 2 MVP

### Capa Bronze: `bronze_emt_raw`

Respuesta cruda de `POST /v2/transport/busemtmad/stops/{stopId}/arrives/`, completa sin transformación.

| Campo | Descripción |
|---|---|
| `ingested_at` | Timestamp de ingesta |
| `endpoint` | Tipo de respuesta (`arrives`, `lines_info`, etc.) |
| `request_stop_id` | `stop_id` consultado |
| `api_code`, `api_description` | Envelope de estado de EMT |
| `payload_json` | Respuesta completa en JSON crudo |

### Capa Silver: `silver_arrival_observations` 

| Columna | Tipo | Restricción | Descripción |
|---|---|---|---|
| `_rk` | STRING | PRIMARY KEY | Hash SHA256(`stop_id + line_id + bus_id + datetime_polling`) para dedup |
| `stop_id` | INT | NOT NULL | Parada |
| `line_id` | STRING | NOT NULL | Línea |
| `line_label` | STRING | NOT NULL | Etiqueta de línea para mostrar al usuario |
| `bus_id` | STRING | NOT NULL | Identificador del vehículo |
| `destination` | STRING | NOT NULL | Cabecera de destino (usado en D1) |
| `eta_seconds` | INT | NULLABLE | Segundos estimados — null permitido, **no se descarta** |
| `datetime_polling` | TIMESTAMP | NOT NULL | Hora exacta del poll |
| `ingested_at` | TIMESTAMP | NOT NULL | Hora de ingesta en Fabric |

### Capa Silver: `silver_stops_dim`

Catálogo estático de paradas (GTFS bootstrap).

| Columna | Tipo | Descripción |
|---|---|---|
| `stop_id` | INT | Identificador único |
| `stop_name` | STRING | Nombre de la parada (p.ej. "Mercado San Fernando") |
| `stop_lat` | DOUBLE | Latitud |
| `stop_lon` | DOUBLE | Longitud |
| `direction_text` | STRING | Dirección/calle (opcional) |
| `in_scope` | BOOLEAN | `true` si está dentro del geofence Sol/Gran Vía |
| `catalog_loaded_at` | DATE | Fecha de carga del GTFS |

### Capa Silver: `silver_lines_dim`

Catálogo estático de líneas (GTFS).

| Columna | Tipo | Descripción |
|---|---|---|
| `line_id` | STRING | Código de línea (p.ej. "001") |
| `line_label` | STRING | Etiqueta para mostrar (p.ej. "M1") |
| `name_a` | STRING | Destino dirección A |
| `name_b` | STRING | Destino dirección B |
| `in_scope` | BOOLEAN | `true` si al menos una parada está dentro del geofence |
| `catalog_loaded_at` | DATE | Fecha de carga del GTFS |

### Capa Silver: `silver_stop_lines`

Relación estática línea↔parada + indicador de cabecera (GTFS).

| Columna | Tipo | Descripción |
|---|---|---|
| `stop_id` | INT | Parada |
| `line_id` | STRING | Línea que sirve esa parada |
| `line_label` | STRING | Etiqueta de línea |
| `is_terminus` | BOOLEAN | `true` si `stop_sequence = 1` en `trips/stop_times` (es cabecera/origen) |
| `direction_id` | INT | Dirección (0 o 1 en el GTFS) |
| `catalog_loaded_at` | DATE | Fecha de carga del GTFS |

### Capa Gold: `gold_stop_line_eta_latest`

Vista final optimizada para consultas del agente (US-01, US-02, US-03).

| Columna | Tipo | Restricción | Descripción |
|---|---|---|---|
| `stop_id` | INT | NOT NULL | Parada consultada |
| `line_id` | STRING | NOT NULL | Línea |
| `line_label` | STRING | NOT NULL | Etiqueta de línea |
| `destination` | STRING | NOT NULL | Usado para match D1 |
| `eta_seconds` | INT | NULLABLE | Tiempo estimado real — null si `has_upcoming_bus = false` |
| `has_upcoming_bus` | BOOLEAN | NOT NULL | Distingue "sin bus ahora" de "línea no pasa aquí" |
| `origin_stop_notice` | BOOLEAN | NOT NULL | `true` si la parada es cabecera y hay incertidumbre en ETA |
| `is_stale` | BOOLEAN | NOT NULL | `true` si el último poll excede 3x intervalo normal |
| `updated_at` | TIMESTAMP | NOT NULL | Timestamp de refresco |

---

## 7. Esquemas de datos — POSTERGADO (Fase 3+, no MVP)

Estos esquemas se definen acá para referencia, pero **no se construyen en Fase 2**. Se implementan cuando las historias de usuario correspondientes se activen.

### Capa Silver: `silver_incidents` (POSTERGADO — US-05)

Incidencias publicadas por EMT.

| Columna | Tipo | Descripción |
|---|---|---|
| `line_id` | STRING | Línea afectada |
| `incident_guid` | STRING | ID único de incidencia |
| `title` | STRING | Título del incidente |
| `description` | STRING | Descripción detallada |
| `cause` | STRING | Tipo de causa (ej. "04 - Manifestación") |
| `effect` | STRING | Efecto (ej. "05 - Desvío programado") |
| `valid_from` | TIMESTAMP | Inicio de la incidencia |
| `valid_to` | TIMESTAMP | Fin de la incidencia |
| `snapshot_ts` | TIMESTAMP | Timestamp del poll |

### Capa Gold: `gold_incident_line_current` (POSTERGADO — US-05)

Incidencias activas de cada línea.

| Columna | Tipo | Descripción |
|---|---|---|
| `line_id` | STRING | Línea |
| `incident_guid` | STRING | ID de incidencia |
| `title` | STRING | Título |
| `cause`, `effect` | STRING | Clasificación |
| `is_active_now` | BOOLEAN | `true` si `now()` está entre `valid_from` y `valid_to` |
| `snapshot_ts` | TIMESTAMP | Timestamp de refresco |

### Capa Gold: `gold_line_status_5m` (POSTERGADO — análisis operacional)

Agregados de estado de línea por ventana de 5 minutos.

| Columna | Tipo | Descripción |
|---|---|---|
| `window_start` | TIMESTAMP | Inicio de ventana (ej. 10:15:00) |
| `line_label` | STRING | Línea |
| `observations` | INT | Nº de registros en esa ventana |
| `avg_eta_seconds`, `p50_eta_seconds`, `p90_eta_seconds` | DOUBLE | Percentiles de ETA |
| `avg_deviation_min` | DOUBLE | Desviación promedio respecto a horario teórico (si está disponible) |

---

## 8. Plan de construcción por fases

### Fase 2 — MVP (ingesta y modelado básico, Milestone: Fase 2 cerrada)

**Construir:**
- ✅ Bronze (`bronze_emt_raw`) — sólo el endpoint `arrives`, de forma continua (Mejorar el tiempo)
- ✅ Silver (`silver_arrival_observations`, `silver_stops_dim`, `silver_lines_dim`, `silver_stop_lines`) — desde GTFS + primer poll
- ✅ Gold (`gold_stop_line_eta_latest`) — vista unida, con `has_upcoming_bus` + `origin_stop_notice`

**Notebooks:**
- 1 notebook: bronze → silver (enriquecer con GTFS, dedup)
- 1 notebook: silver → gold (últimas filas por parada, LEFT JOIN contra `silver_stop_lines`)

**Criterios de aceptación:**
- [ ] 30+ minutos de polling continuo sin fallos
- [ ] Gold reflejada dentro de 60s del último poll exitoso
- [ ] Validación manual: preguntas US-01/02 respondidas correctamente desde gold

### Fase 3+ — Extensiones (incidencias, agregados, segundo dominio)

- `silver_incidents` + `gold_incident_line_current` (cuando US-05 active)
- `gold_line_status_5m` (cuando análisis operacional sea relevante)
- Segundo dominio (Fase 6, si hay tiempo)

---

## 9. Pendientes finales

- [ ] Geofence exacto de Sol/Gran Vía (Z2/Z5) — Developer
- [ ] Conteo real de paradas en la zona — Developer
- [ ] Script de bootstrap GTFS (descarga + `silver_stop_lines` con `is_terminus`) — Developer
- [ ] Confirmar valores de `stop_sequence` en GTFS local — Developer (validación de la lógica `is_terminus`)

---

## 10. Request body — ingesta `arrives` (MVP)

Endpoint: `POST /v2/transport/busemtmad/stops/{stopId}/arrives/`  
Headers: `accessToken`, `Content-Type: application/json`

```json
{
  "cultureInfo": "es",
  "Text_StopRequired_YN": "Y",
  "Text_EstimationsRequired_YN": "Y",
  "Text_IncidencesRequired_YN": "N"
}
```

| Campo | Valor MVP | Efecto |
|---|---|---|
| `cultureInfo` | `"es"` | Idioma de textos en la respuesta. |
| `Text_StopRequired_YN` | `"Y"` | Metadatos de parada en la respuesta. |
| `Text_EstimationsRequired_YN` | `"Y"` | Estimaciones de llegada (ETA). |
| `Text_IncidencesRequired_YN` | `"N"` | Sin incidentes (fuera de MVP; ver §5). |
