# RTI ops manual — Eventhouse + UDF (Phase 4 & 5)

**Branch:** `feat/fabric-phase5` (Phase 4 hot path + Phase 5 catalogue cutover)  
**Contract:** [data-source-contract-v4.md](./data-source-contract-v4.md) **v4.5** · [ADR-040](./adr/ADR-040-eventhouse-catalogue-sot-seed-tag-and-kusto-udf-read.md)  
**Roadmap:** [refactoring-plan.md](./refactoring-plan.md) Phase 4–5  
**Rollback:** Lakehouse Phase 0–3 (`pipeline/` + notebooks) until Agent + catalogue cutover are done.

> **이 문서가 Fabric에서 손대기 전에 읽는 체크리스트다.**  
> 순서를 건너뛰면 Gold ETA가 비거나 silver 컬럼이 null로 쌓일 수 있다.  
> **Step A → G 끝까지** 이 문서만 따라가면 된다 (중간에 "코드 생기면…" 절은 없음 — 레포에 이미 있음).

---

## 0. 절대 하지 말 것 (Do not)

| # | 금지 | 왜 |
|---|------|-----|
| 1 | **KQL seed 방어(P5.2) 없이** EH에 bootstrap 시드 대량 적재 | `max(datetime_polling)`이 시드를 최신으로 잡아 ETA가 증발함 |
| 2 | 시드를 `es_emt_arrives` / alerts ES로 보내기 | bronze·alerts 매핑에 silver 스키마 → 컬럼 null |
| 3 | poll의 `emt_record`를 `"silver_arrives"`에서 바꾸기 | ES 필터·관측 가정 깨짐. 시드만 `"silver_arrives_seed"` |
| 4 | EH에서 `silver_arrives` 전체 `.set-or-replace`로 "시드 청소" | poll 이력·freq 재료 삭제 |
| 5 | LH식 `DELETE WHERE bus_id IS NULL AND eta IS NULL…` 를 EH에 이식 | 빈 poll과 시드가 같은 모양 → 동시 실행 시 사고 |
| 6 | arrives 스케줄을 bootstrap 때문에 끄기 | arrives는 24/7; 겹침이 정상. 태+Gold 제외로 방어 |
| 7 | silver JSON을 bronze destination에 넣기 | 전부 null처럼 보임 |
| 8 | UDF에 `from __future__ import annotations` | Fabric UDF 깨짐 |

---

## 1. Topology (현재)

```text
Hot path (기존 / dual-run):
  udf-emt-ingest
    poll_arrives_scope    → LH catalogue → es_emt_arrives + es_emt_arrives_silver
    poll_alerts_scope     → LH catalogue → es_emt_alerts + es_emt_alerts_silver
    poll_arrives_scope_eh → EH catalogue (Kusto REST) → 동일 ES
    poll_alerts_scope_eh  → EH catalogue (Kusto REST) → 동일 ES
  KQL: gold_emt_stop_line_build → .set-or-replace gold_emt_stop_line

Catalogue today (아직 LH):
  daily nb_bootstrap_gtfs_silver → Lakehouse silver_arrives
  UDF는 LH SQL로 카탈로그 읽음

Phase 5 target:
  daily nb_bootstrap_eh_silver → es_emt_arrives_silver → silver_arrives (emt_record=silver_arrives_seed)
  UDF poll_*_scope_eh → Kusto REST (Query URI + SPN) → silver_arrives_catalogue_latest()
  KQL helper silver_arrives_catalogue_latest() = UDF와 동일 필터 (운영 스모크도 이 함수)
  LH bootstrap 스케줄 중지 (롤백용으로만 남김)
```

**Eventstreams (이름 고정):**

| Stream | Destination table |
|--------|-------------------|
| `es_emt_arrives` | `bronze_emt_raw` |
| `es_emt_arrives_silver` | `silver_arrives` |
| `es_emt_alerts` | `bronze_emt_raw` |
| `es_emt_alerts_silver` | `silver_alerts` |

Ownership: Arrives must not clear Gold `alert_*`; alerts must not clear ETA/freq.

---

## 2. Fabric object names

| Object | Name / note |
|--------|-------------|
| UDF | `udf-emt-ingest` |
| UDF Lakehouse SQL alias | `lhemtmadrid` (dual-run / rollback / Step C smoke) |
| EH catalogue (UDF) | Kusto REST: `EH_QUERY_URI` + VL SPN (`FABRIC_SP_*`) — **ehemtmadrid / shortcut 불필요** |
| UDF Variable Library alias | `varemtmadrid` |
| Eventhouse / DB | `eh_emt_madrid` / `db_emt` (포털과 다르면 포털 이름 사용) |
| Tables | `bronze_emt_raw`, `silver_arrives`, `silver_alerts`, `gold_emt_stop_line` |
| EH bootstrap notebook | [`notebooks/nb_bootstrap_eh_silver.py`](../notebooks/nb_bootstrap_eh_silver.py) |
| Daily pipeline (Fabric) | `pl_emt_bootstrap_daily` (Step F에서 생성) |

Paste: [`rti/udf/udf_emt_ingest.py`](../rti/udf/udf_emt_ingest.py) · KQL [`rti/kql/`](../rti/kql/) `01`…`06`  
UDF constants: `ARRIVES_SILVER_CONN` / `HUB` = `es_emt_arrives_silver` Custom endpoint (시드·poll silver 동일).  
UDF `EH_QUERY_URI` = Eventhouse **Query URI**; `EH_KQL_DB` = `db_emt` (포털명).

---

## 3. `emt_record` 값 (Phase 5)

| 값 | 의미 | 누가 씀 |
|----|------|---------|
| `bronze` | bronze 이벤트 | UDF → bronze ES |
| `silver_arrives` | poll / empty poll | UDF arrives expand — **바꾸지 말 것** |
| `silver_arrives_seed` | 카탈로그 시드 | Phase 5 bootstrap / `emit_seed_smoke_from_lh` |
| `silver_alerts` | alerts silver | UDF alerts |
| `gold_*_patch` | optional gold patch | 보통 미사용; Gold는 KQL apply |

KQL Gold/freq는 시드를 `emt_record != silver_arrives_seed` 로 제외한다 (`04`, `05`).  
카탈로그 헬퍼: `silver_arrives_catalogue_latest()` (`02`).

---

## 4. Phase 5 — 배포 순서 (반드시 이 순서)

로드맵 상세: [refactoring-plan.md](./refactoring-plan.md) P5.0–P5.7.

### Step A — KQL 방어만 먼저 (시드 쓰기 금지)

**목표:** 시드가 실수로 들어와도 Gold ETA가 안 깨지게.

1. Eventhouse `db_emt`에서 아래를 **순서대로** 붙여넣기·실행:
   - [`rti/kql/02_silver_arrives.kql`](../rti/kql/02_silver_arrives.kql) 전체  
     (끝에 `silver_arrives_catalogue_latest` 포함 — 시드 없어도 함수 생성은 OK)
   - [`rti/kql/05_freq_adr038.kql`](../rti/kql/05_freq_adr038.kql)
   - [`rti/kql/04_gold_emt_stop_line.kql`](../rti/kql/04_gold_emt_stop_line.kql)  
     (`gold_arrives_stage`가 seed 제외)
2. Gold 재적용:

```kusto
.set-or-replace gold_emt_stop_line <| gold_emt_stop_line_build(900, 20)
```

3. 스모크 (ETA가 있던 grain이 비면 **여기서 멈춤** — 시드 넣지 말 것):

```kusto
gold_emt_stop_line
| where has_upcoming_bus
| summarize n=count()

// 함수가 보이는지
.show functions | where Name has "catalogue" or Name has "gold_arrives"
```

4. 시드 방어 실검증은 **Step C**에서 한다. Step A에서는 KQL paste + gold apply만.

**Exit A:** Gold 정상 + seed exclude 함수 배포됨. **아직 EH에 bootstrap/시드 넣지 말 것.**

---

### Step B — ES 포털 확인 (`es_emt_arrives_silver`)

1. Fabric → `es_emt_arrives_silver` → destination `silver_arrives`.
2. `emt_record` **필터**가 있는지 확인:
   - 필터 없음 (매핑만) → OK. 시드 JSON 그대로 적재 가능.
   - `emt_record == "silver_arrives"` 만 허용 → **`silver_arrives_seed` allow-list 추가** 후에만 시드 송신.
3. Destination이 `bronze_emt_raw`가 아닌지 재확인.

**Exit B:** 시드가 이 스트림으로 가면 `silver_arrives`에 들어간다는 확신.

---

### Step C — 시드 1건 smoke (`emit_seed_smoke_from_lh`)

**전제:** Step A·B 통과. UDF에 최신 [`rti/udf/udf_emt_ingest.py`](../rti/udf/udf_emt_ingest.py) paste + Publish.  
Connections: `lhemtmadrid` (LH dual-run), `varemtmadrid`. Libraries: **`requests` only** (send + SPN token; no `azure-eventhub` / `azure-identity`).
VL (Eventstream SAS, paste once): `ARRIVES_BRONZE_CONN`, `ARRIVES_SILVER_CONN` (+ alerts/hubs as needed).  
`ARRIVES_SILVER_CONN` / `ARRIVES_SILVER_HUB` = `es_emt_arrives_silver` Custom endpoint (poll과 동일 값).

1. UDF 포털에서 **`emit_seed_smoke_from_lh`** 실행:
   - `maxRows` = `1` (기본)
   - LH 카탈로그에서 grain 1개를 `emt_record=silver_arrives_seed` 로 복사해 silver ES로 보냄
   - 기대 응답 예: `emit_seed_smoke_from_lh sent=1 scope_stops=… sample_stop=…`
2. EH KQL 확인 (1–2분 ES lag 허용):

```kusto
silver_arrives
| where emt_record == "silver_arrives_seed"
| take 5

silver_arrives_catalogue_latest()
| summarize grains=count(), stops=dcount(stop_id)
```

3. Gold 재적용 후 ETA 회귀 없는지.  
   **주의:** `.set-or-replace`는 **제어 명령** — 쿼리와 **같은 셀에 넣지 말 것**. 각각 따로 실행.

```kusto
.set-or-replace gold_emt_stop_line <| gold_emt_stop_line_build(900, 20)
```

그다음 **새 셀/새 실행**으로:

```kusto
gold_emt_stop_line
| where has_upcoming_bus
| summarize n=count()
```

**Exit C:** 시드 1건+ 적재 + Gold ETA 유지. **여기까지가 시드 안전 증명.** 그다음 전체 bootstrap.

---

### Step D — 전체 bootstrap → EH (`nb_bootstrap_eh_silver`)

**레포 산출물 (이미 있음):**

| Path | Role |
|------|------|
| [`rti/lib/bootstrap_seed.py`](../rti/lib/bootstrap_seed.py) | GTFS + S1 → seed JSON (`emt_record=silver_arrives_seed`) |
| [`pipeline/orchestrator/bootstrap_eh_impl.py`](../pipeline/orchestrator/bootstrap_eh_impl.py) | `run_bootstrap_eh(...)` → Event Hub send |
| [`notebooks/nb_bootstrap_eh_silver.py`](../notebooks/nb_bootstrap_eh_silver.py) | Fabric 노트북 셀 |

**한 번만 준비:**

1. Lakehouse Files에 업로드:
   - `Files/python/pipeline/` (레포 `pipeline/` 전체)
   - `Files/python/rti/` (레포 `rti/` 전체 — 최소 `rti/lib/`)
2. GTFS zip이 있으면 `Files/gtfs/gtfs_emt.zip` (없으면 노트북이 URL로 다운로드).
3. 노트북 전송은 requests+SAS (`azure.eventhub` 불필요). Fabric에서 노트북 신규 → [`nb_bootstrap_eh_silver.py`](../notebooks/nb_bootstrap_eh_silver.py) 내용 paste (또는 `.py` import).  
   **`%pip` 셀 넣지 말 것** — Pipeline 노트북 실행에서 기본 비활성 → `MagicUsageError`. Spark runtime의 `requests` 사용.
4. 파라미터 채우기:
   - `arrives_silver_conn` / `arrives_silver_hub` = UDF의 `ARRIVES_SILVER_*`와 **동일**
   - EMT creds: VL `var_emt_madrid` 키 `EMT_CLIENT_ID` + `EMT_MADRID_PASS_KEY` (UDF와 동일). 실패 시 셀 `client_id_override` / `pass_key_override`
5. **스모크 권장:** `line_ids_override = "027"` (또는 짧은 노선 하나)로 먼저 실행 → 전량 전에 ES/Gold 재확인.

**실행 규칙:**

- 출력은 **오직** `es_emt_arrives_silver` (`emt_record=silver_arrives_seed`)
- EH에서 null-shaped **DELETE 하지 않음** (append-only; 최신 `catalog_loaded_at`만 읽음)
- arrives/alerts 스케줄 **끄지 않음**
- LH `nb_bootstrap_gtfs_silver`는 **아직 스케줄 유지** (UDF가 아직 LH 읽는 동안 롤백망)

**검증:** (쿼리끼리 / `.` 명령은 **셀을 나눠** 실행)

```kusto
silver_arrives
| where emt_record == "silver_arrives_seed"
| summarize grains=dcount(strcat(stop_id,"|",line_id,"|",tostring(direction_id))),
            stops=dcount(stop_id),
            loaded=max(catalog_loaded_at)
```

```kusto
silver_arrives_catalogue_latest()
| summarize grains=count(), stops=dcount(stop_id)
```

```kusto
.set-or-replace gold_emt_stop_line <| gold_emt_stop_line_build(900, 20)
```

```kusto
gold_emt_stop_line
| where has_upcoming_bus
| summarize n=count()
```

**Exit D:** 아침 분량(또는 override 스모크) 시드가 EH에 쌓임; `catalog_loaded_at` = 실행일; Gold ETA 유지.  
그다음 `line_ids_override=""` 로 전량 1회.

---

### Step E — UDF 카탈로그를 EH로 (`poll_*_scope_eh`, Kusto REST)

UDF는 Eventhouse를 **Kusto REST**로 읽는다 (`POST {QueryURI}/v1/rest/query`).  
Lakehouse shortcut / SQL endpoint / `ehemtmadrid` **쓰지 않는다.**

**E.1 — Query URI**

1. Fabric → Eventhouse `eh_emt_madrid` (또는 포털 이름) → **URI** / Query URI 복사.  
   예: `https://<id>.zN.kusto.fabric.microsoft.com`
2. UDF 상수 `EH_QUERY_URI = "..."` 에 붙여넣기 **또는** Variable Library 키 `EH_QUERY_URI`.
3. `EH_KQL_DB = "db_emt"` (KQL DB 이름과 다르면 수정).

**E.2 — SPN (Variable Library)**

UDF에는 `notebookutils`가 없어서 Entra **앱 등록(SPN)** 으로 토큰을 받는다.

1. Entra ID에 앱 등록 → client secret 발급.
2. 그 SPN을 Fabric **워크스페이스**에 추가 (Eventhouse 쿼리 가능한 역할 — Contributor 또는 동등).
3. Variable Library `var_emt_madrid`에:

| Key | Value |
|-----|--------|
| `FABRIC_TENANT_ID` | 테넌트 GUID |
| `FABRIC_SP_CLIENT_ID` | 앱 클라이언트 ID |
| `FABRIC_SP_CLIENT_SECRET` | 클라이언트 시크릿 |
| `EH_QUERY_URI` | (UDF 상수 비웠을 때만) Query URI |
| `ARRIVES_BRONZE_CONN` / `ARRIVES_SILVER_CONN` | Eventstream Custom endpoint SAS (UDF 코드 CONN `""` 유지) |
| `ALERTS_BRONZE_CONN` / `ALERTS_SILVER_CONN` | alerts ES SAS |
| `ARRIVES_*_HUB` / `ALERTS_*_HUB` | hub 이름 (conn에 `EntityPath` 있으면 생략 가능) |

4. UDF Library management: **`requests==2.32.5`** (+ fabric UDF). `azure-eventhub` / `azure-identity` **제거** 권장.
5. 최신 `udf_emt_ingest.py` paste → Publish. Connections: `varemtmadrid` (+ dual-run용이면 `lhemtmadrid`).

**E.3 — 스모크**

1. KQL로 시드가 있는지 확인: `silver_arrives_catalogue_latest() | count`
2. UDF **`poll_arrives_scope_eh`** — `stopIdsCsv`에 알려진 stop, `batchLimit=1`
3. 성공 시 `scope_total`이 LH `poll_arrives_scope`와 비슷한지 비교
4. 통과 후 Pipeline arrives/alerts만 `poll_*_scope_eh` / `poll_alerts_scope_eh`로 전환

**Exit E:** 핫패스 Pipeline이 `*_eh`만 호출. 카탈로그는 EH seed. LH SQL 읽기 없음.

---

### Step F — Daily pipeline `pl_emt_bootstrap_daily`

Fabric에서 **새 Pipeline** 생성 (기존 arrives/alerts 스케줄과 **분리**).

```text
pl_emt_bootstrap_daily
  schedule: ~06:00–09:00 Europe/Madrid (LH bootstrap과 비슷한 창)
  activities:
    1. Notebook → nb_bootstrap_eh_silver
         (line_ids_override 비움 = 전량; arrives_silver_conn은 노트북 파라미터/셀)
         **노트북에 `%pip` 없을 것** (Pipeline에서 MagicUsageError)
    2. Wait 2–5 min (ES → EH lag)
    3. (optional) Script / KQL activity:
         .set-or-replace gold_emt_stop_line <| gold_emt_stop_line_build(900, 20)
```

운영 규칙:

- 기존 **arrives/alerts 스케줄은 그대로 24/7** (bootstrap 창에 끄지 않음)
- Bootstrap 실패 알림(메일/Teams) 켜기 — stale catalogue가 overlap보다 나쁨
- LH `nb_bootstrap_gtfs_silver` 스케줄은 **Step G까지 유지** 권장 (dual-run 비교)

**Exit F:** 무인 아침 1회 성공; 그사이 Gold ETA 끊기지 않음; `silver_arrives_catalogue_latest()` grains가 갱신됨.

---

### Step G — Cutover & rollback

**Cutover (EH 신뢰 후):**

1. LH `nb_bootstrap_gtfs_silver` **스케줄만 중지** (노트북·코드는 롤백용 보관).
2. Pipeline이 `poll_*_scope_eh`만 쓰는지 재확인.
3. 문서/Agent 컨텍스트: catalogue SoT = EH seed ([agent-eventhouse-cutover-context.md](./agent-eventhouse-cutover-context.md)).

**Rollback (EH catalogue 문제 시):**

1. Pipeline 함수를 다시 `poll_arrives_scope` / `poll_alerts_scope` (LH).
2. LH bootstrap 스케줄 재개.
3. Gold의 seed exclude (`04`/`05`)는 **그대로 둬도 무해**.

**Exit G:** 핫패스에 Lakehouse catalogue 의존 없음. LH는 롤백 전용.

---

## 5. Phase 4·5 운영 참고

### UDF functions

| Function | Catalogue | Role |
|----------|-----------|------|
| `ping` | — | Runtime smoke |
| `emit_seed_smoke_from_lh` | LH | Step C: seed 1건 → `es_emt_arrives_silver` |
| `poll_arrives_scope` | LH | Dual-run / rollback |
| `poll_alerts_scope` | LH | Dual-run / rollback |
| `poll_arrives_scope_eh` | EH Kusto REST | Cutover hot path |
| `poll_alerts_scope_eh` | EH Kusto REST | Cutover hot path |

### Parameters (`poll_arrives_scope` / `_eh`)

| Param | Use |
|-------|-----|
| `stopIdsCsv` | Empty = all catalogue stops. Smoke: `"2711"` |
| `batchOffset` / `batchLimit` | Timeout 시 청크 (예: 40) |
| `clientId` / `passKey` | Variable Library 실패 시만 |

### EMT arrives codes

| `api_code` | Meaning | UDF |
|------------|---------|-----|
| `00` | OK with estimations | Success |
| `01` | OK, no estimations | Success (empty Arrive) |
| `80`–`90` | Auth | Re-login / fail with detail |

예: `scope_total=1 batch=1 offset=0 bronze=1 silver=4 gold_patches=4(local) fails=0`  
`gold_patches=N(local)` = 메모리만 계산. EH gold는 KQL apply.

### SQL quirks

| Path | Client | Connect | DB constant |
|------|--------|---------|-------------|
| LH catalogue | `FabricLakehouseClient` | **`connectToSql()`** | `LH_SQL_DB` = Lakehouse **item** (`lh_emt_madrid`) ≠ alias |
| EH catalogue | Kusto REST (`requests` + SPN token endpoint) | `POST …/v1/rest/query` | `EH_QUERY_URI` + VL SPN |
| `map_ok` | — | T-SQL `map_ok = 1` | — |

### Map coordinates

| Column | Source |
|--------|--------|
| `stop_lat` / `stop_lon` | 카탈로그 denorm (시드 → UDF) |
| `bus_lat_1/2` / `bus_lon_1/2` | Arrive `geometry` `[lon, lat]` |

```kusto
gold_emt_stop_line
| where has_upcoming_bus
| project stop_id, line_id, stop_lat, stop_lon, bus_id_1, bus_lat_1, bus_lon_1
| take 20
```

### Gold apply

```kusto
.set-or-replace gold_emt_stop_line <| gold_emt_stop_line_build(900, 20)
```

### 스키마 evolve 주의

`.create-merge`는 컬럼을 **끝에 추가**. `project` 순서가 테이블과 다르면 `.set-or-replace`가 *Query schema does not match* 로 실패.  
→ drop + `04`로 gold 재생성 (Silver는 유지).

---

## 6. Repo map

| Path | Fabric? | Role |
|------|---------|------|
| `rti/udf/udf_emt_ingest.py` | Paste UDF | Poll LH/EH + `emit_seed_smoke_from_lh` |
| `rti/kql/01`–`06` | Paste EH | DDL, catalogue helper, gold, freq, apply |
| `rti/lib/bootstrap_seed.py` | Files upload | Seed builder (Spark-free) |
| `pipeline/orchestrator/bootstrap_eh_impl.py` | Files upload | EH bootstrap entry |
| `notebooks/nb_bootstrap_eh_silver.py` | Fabric notebook | Step D / F |
| `notebooks/nb_bootstrap_gtfs_silver.py` | Fabric notebook | LH rollback |
| `pipeline/` + 기타 notebooks | Lakehouse | Phase 0–3 + rollback |

---

## 7. Lessons learned

1. UDF Manage connections: `lhemtmadrid` (LH dual-run) + `varemtmadrid` (EMT + Kusto SPN). No ehemtmadrid.  
2. Never land silver-shaped events on bronze-only JSON mapping.  
3. Alerts protobuf in `payload` can be huge — keep alerts on `es_emt_alerts*`.  
4. No `from __future__ import annotations` in Fabric UDF.  
5. `api=01` is not a credential bug.  
6. After adding silver columns, re-apply `silver_arrives_json` mapping.  
7. Phase 5: **KQL seed exclude before any EH bootstrap**. Arrives 24/7 overlap is expected.  
8. UDF catalogue = Kusto REST로 `silver_arrives_catalogue_latest()` 호출 (Query URI + SPN).

---

## 8. Status checklist

| Step | Repo | Fabric (너) |
|------|------|-------------|
| A — KQL seed exclude + catalogue helper | Ready (`02`/`04`/`05`) | Paste + gold apply |
| B — `es_emt_arrives_silver` filter | — | Portal check / allow-list |
| C — `emit_seed_smoke_from_lh` | Ready (UDF) | Paste UDF → run maxRows=1 |
| D — `nb_bootstrap_eh_silver` | Ready | Files upload → notebook run |
| E — `poll_*_scope_eh` Kusto REST | Ready (UDF) | Query URI + SPN + Pipeline switch |
| F — `pl_emt_bootstrap_daily` | Guide only | Create pipeline + schedule |
| G — Stop LH bootstrap schedule | Docs | After dual-run trust |
| Agent rebind → EH gold | — | Phase 4 cutover track |

---

## 9. 지금 네가 할 일

**이미 Step C까지 했다고 가정하면 → Step D부터:**

1. **D:** Files에 `pipeline/` + `rti/` 업로드 → `nb_bootstrap_eh_silver` paste → `line_ids_override`로 스모크 → 전량.  
2. **E:** Query URI + VL SPN + ES CONN → `diag_eh_ready` / `poll_*_scope_eh` → Pipeline 전환 (`requests` only).  
3. **F:** `pl_emt_bootstrap_daily` 생성·스케줄.  
4. **G:** LH bootstrap 스케줄 중지.

아직 A–C가 아니면 **A → B → C**를 먼저 끝내고 D로 온다.  
막히면: 해당 Step의 에러 전문 + `silver_arrives | take 1` 스키마를 남긴다 (시드 대량으로 "고쳐보지" 말 것).
