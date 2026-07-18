# GTFS-Realtime Service Alerts (EMT) — Referencia de respuesta

**Fecha verificación:** 2026-07-18  
**Producer (dato real):** `GET https://openapi.emtmadrid.es/v1/bus/servicealerts/proto`  
**Catálogo (solo metadatos):** [Mobility Database mdb-3102](https://mobilitydatabase.org/feeds/gtfs_rt/mdb-3102) · [Swagger Catalog API](https://mobilitydata.github.io/mobility-feed-api/SwaggerUI/index.html#/)  
**Artefactos en repo:** [`docs/gtfs-rt-servicealerts/`](./gtfs-rt-servicealerts/)

> **Dos APIs distintas.** El Swagger de MobilityData **no** sirve ETA ni el cuerpo de las alertas: solo dice *dónde* está el feed. El protobuf de EMT es el dato. No mezclar.

---

## 0. Formato de respuesta (lo importante)

EMT **no** responde JSON. La respuesta HTTP es un fichero binario **GTFS-Realtime protobuf**.

| | Valor verificado (2026-07-18) |
|---|---|
| URL | `https://openapi.emtmadrid.es/v1/bus/servicealerts/proto` |
| HTTP | `200` |
| `Content-Type` | `application/octet-stream` |
| `Content-Disposition` | `attachment; filename=servicealerts.pb` |
| Cuerpo | Bytes protobuf ≈ `FeedMessage` (~100 KB en la sonda) |
| Auth | **Ninguna** |

```text
EMT  ──►  servicealerts.pb  (único formato de la API)
              │
              ▼  parseo local (gtfs-realtime-bindings / protoc)
         objetos Python / JSON legible
```

### Qué hay en `docs/gtfs-rt-servicealerts/`

| Archivo | Origen | Qué es |
|---|---|---|
| `servicealerts.pb` | **Respuesta cruda de EMT** | Binario protobuf (así llega la API) |
| `feed_full.json` | **Conversión local** del `.pb` | Mismo contenido, para leer/diff en el repo |
| `inventory.json` | **Resumen local** | Paths presentes, usage de campos, lista de alerts |

Los `.json` **no** los sirve EMT. Existen solo como artefacto de inspección tras parsear el `.pb`.

Parseo típico:

```python
from google.transit import gtfs_realtime_pb2

feed = gtfs_realtime_pb2.FeedMessage()
feed.ParseFromString(open("servicealerts.pb", "rb").read())
# feed.header / feed.entity[].alert
```

---

## 1. Quién es quién (rate limits)

| | **EMT producer** (`…/servicealerts/proto`) | **Mobility Database Catalog API** |
|---|---|---|
| Qué hace | Devuelve el **FeedMessage** protobuf de incidencias | Lista / busca feeds (`mdb-*`), URLs, entity types |
| Auth | **Ninguna** (HTTP 200 sin `accessToken`) | OAuth2 Bearer; access token ~1 h; refresh token largo |
| ¿Cuenta en cuota MobilityLabs? | **No** (no login / no header de sesión) | N/A — otro producto |
| Rate limit documentado | **No** aparece en headers ni en OpenAPI EMT | **No** hay umbral público numérico ([issue #44](https://github.com/MobilityData/mobility-feed-api/issues/44) sigue abierto / Future) |
| Headers vistos | `cache-control: no-cache`, **sin** `X-RateLimit-*` / `Retry-After` | Sin token → redirect login (302 IAP) |
| En Swagger EMT (`openapi.json`) | **No** figura como path | — |
| Uso PoC | **Sí** — fuente US-07 preferible a poll `arrives.Incident` | Solo discovery puntual. No poll en pipeline |

### Cuota MobilityLabs (solo REST autenticada: `arrives`, login, …)

Viene en login (`apiCounter`), **no** aplica al producer protobuf. Ver login en la referencia REST del proyecto (`apiCounter.current` / `dailyUse`).

### Paginación ≠ rate limit (Catalog API)

En el OpenAPI del catálogo, `limit` es **tamaño de página** (p. ej. `gtfs_rt_feeds`: default/max **1000**), no un cupo de requests/min.

Auth Catalog ([README MobilityData](https://github.com/MobilityData/mobility-feed-api)):

```bash
curl -sS 'https://api.mobilitydatabase.org/v1/tokens' \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token":"<REFRESH>"}'

curl -sS 'https://api.mobilitydatabase.org/v1/gtfs_rt_feeds/mdb-3102' \
  -H "Authorization: Bearer <ACCESS>"
```

| Método | Path | Notas |
|---|---|---|
| `GET` | `/v1/metadata` | Smoke test |
| `GET` | `/v1/gtfs_rt_feeds` | Lista; `entity_types=sa` filtra Service Alerts |
| `GET` | `/v1/gtfs_rt_feeds/{id}` | p. ej. `mdb-3102` → `producer_url` |
| `GET` | `/v1/search` | Búsqueda |

Schema `GtfsRTFeed.entity_types`: `vp` | `tu` | `sa`. EMT Madrid = **`sa` only**.

---

## 2. Llamada al producer

```http
GET /v1/bus/servicealerts/proto HTTP/1.1
Host: openapi.emtmadrid.es
```

| | Valor verificado |
|---|---|
| HTTP | `200` |
| Body | Protobuf `FeedMessage` (archivo `.pb`) |
| Auth | Ninguno |
| Incremental | Snapshot **FULL** (toda la lista cada vez; no hay diff feed) |

**Poll PoC:** cada **2–5 min** basta. No martillar aunque no haya rate limit publicado.

---

## 3. Envelope del feed (tras parsear el `.pb`)

| Campo | Tipo | ¿Presente? | Ejemplo / notas |
|---|---|---|---|
| `header.gtfs_realtime_version` | string | **Sí** | `"2.0"` |
| `header.timestamp` | uint64 (unix) | **Sí** | frescura del feed |
| `header.incrementality` | enum | No seteado (default FULL) | Tratar como dataset completo |
| `header.feed_version` | string | **No** | — |
| `entity[]` | FeedEntity | **Sí** | Solo tipo `alert` en EMT |

Sonda 2026-07-18: **144** entities, **todas** `alert` → **~30** eventos únicos (fan-out 1 evento × N `route_id`).

---

## 4. `FeedEntity`

| Campo | ¿Presente? | Notas |
|---|---|---|
| `id` | **Sí** | `{UUID}-{route}` p. ej. `AE1D8066-…-001`. El UUID es el evento; el sufijo es la línea. |
| `is_deleted` | **No** | — |
| `alert` | **Sí** | Único payload útil |
| `trip_update` / `vehicle` / `shape` / … | **No** | — |

---

## 5. `Alert` — campos usados vs nunca vistos

### 5.1 Presentes en el 100 % de entidades (sonda)

| Campo | Tipo | Ejemplo vivo | Uso PoC |
|---|---|---|---|
| `active_period[].start` | unix | `1783083600` | → `incident_valid_from` |
| `active_period[].end` | unix | `1785823200` | → `incident_valid_to` |
| `cause` | enum | `OTHER_CAUSE` / `DEMONSTRATION` / `CONSTRUCTION` | → `incident_cause` |
| `effect` | enum | `DETOUR` / `STOP_MOVED` / `MODIFIED_SERVICE` | → `incident_effect` |
| `url.translation[].language` | string | `"es"` | |
| `url.translation[].text` | string | PDF `http://feeds.emtmadrid.es:8082/docs/…` | Opcional (more info) |
| `header_text.translation[].language` | string | `"es"` | |
| `header_text.translation[].text` | string | título corto | → `incident_title` |
| `description_text.translation[].language` | string | `"es"` | |
| `description_text.translation[].text` | string | texto largo | → `incident_description` |
| `informed_entity[].route_id` | string | `"001"`, `"M1"`, `"N19"` | Join a `line_id` / label |
| `informed_entity[].stop_id` | string | **siempre `""`** | No usable para filtrar parada |

`active_period`: **1** por alert. `informed_entity`: **1** por entity (por eso el fan-out por línea).

### 5.2 Definidos en el estándar pero **nunca** en esta sonda

`severity_level`, `tts_header_text`, `tts_description_text`, `image`, `image_alternative_text`, `cause_detail`, `effect_detail`  
En `EntitySelector`: `agency_id`, `route_type`, `trip`, `direction_id` (además de `stop_id` vacío).

### 5.3 Distribución cause / effect (sonda)

| cause | n | effect | n |
|---|---|---|---|
| `OTHER_CAUSE` | 56 | `DETOUR` | 107 |
| `CONSTRUCTION` | 49 | `STOP_MOVED` | 36 |
| `DEMONSTRATION` | 39 | `MODIFIED_SERVICE` | 1 |

---

## 6. Activo ahora / grano gold

```text
incident_active = (now >= start) AND (now <= end)   # unix UTC
```

No hay boolean nativo (igual que `arrives.Incident`).

**Grano US-07:** deduplicar por UUID de evento, expandir a filas `(stop_id, line_id)` in-scope cuyo `line_label`/`line_id` matchee `informed_entity.route_id` (normalizar `001` vs `1` vs label).

---

## 7. Comparación con `arrives.Incident`

Misma familia de avisos (mismo `guid` / UUID y mismos PDFs en solapes).

| | **GTFS-RT Alerts** | **`arrives` → `Incident.ListaIncident.data[]`** |
|---|---|---|
| Formato | **Protobuf `.pb`** | JSON REST |
| Auth / cuota | No | Sí (`accessToken` + `apiCounter`) |
| Cobertura | Red completa, 1 GET | Solo lo que EMT adjunte al poll de **esa** parada |
| Join a línea | `route_id` explícito | Texto en `description` / contexto del stop |
| Join a parada | `stop_id` vacío | Implícito (la parada polleada) |
| cause / effect | Enum GTFS grueso | Strings EMT más ricos (`"12 - Evento deportivo"`) |
| Ventana | unix `start`/`end` | `rssFrom` / `rssTo` (`DD/MM/YYYY HH:MM:SS`) |
| Extra | — | `pubDate`, `moreInfo.@type/@length` |

**Conclusión PoC:** para US-07 priorizar **RT Alerts** (barato, red completa, `route_id`). `arrives.Incident` queda como fallback o para cause labels más legibles.

---

## 8. Artefactos

| Ruta | Contenido |
|---|---|
| [`docs/gtfs-rt-servicealerts/servicealerts.pb`](./gtfs-rt-servicealerts/servicealerts.pb) | Respuesta API (protobuf) |
| [`docs/gtfs-rt-servicealerts/feed_full.json`](./gtfs-rt-servicealerts/feed_full.json) | Conversión legible del `.pb` |
| [`docs/gtfs-rt-servicealerts/inventory.json`](./gtfs-rt-servicealerts/inventory.json) | Inventario de campos (sonda) |
