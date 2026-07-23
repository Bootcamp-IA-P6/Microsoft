# 수동 적재 가이드 — Lakehouse + Notebook · **contract v4.3** · **쌩 복붙**

**계약:** [`data-source-contract-v4.md`](./data-source-contract-v4.md) (v4.3)  
**방식:** Fabric UI에 노트북 **전체 붙여넣기**. Environment / Git sync 없음.  
**목표:** `gold_emt_stop_line` 유지·갱신. Arrives / alerts **분리** Pipeline.

---

## 테이블 (ADR-015 + ADR-037)

| 테이블 | 역할 |
|--------|------|
| `bronze_emt_raw` | S1/S2 raw |
| `silver_arrives` | catalogue seed + poll history (ex `silver_emt`) |
| `silver_alerts` | S2 alerts latest-only |
| `gold_emt_stop_line` | Data Agent (`alert_*` 포함) |

---

## v4.2 → v4.3 마이그레이션 (데이터 유지)

Fabric에서 **먼저** 갱신된 [`nb_create_tables.py`](../notebooks/nb_create_tables.py) 복붙 → Run All:

1. `silver_emt` → `silver_arrives` 복사 후 `silver_emt` DROP  
2. `silver_alerts` CREATE IF NOT EXISTS  
3. **bronze / gold DROP 안 함**

건수 확인 후 Pipeline 재개.

---

## 흐름

```text
[1회/마이그레이션] nb_create_tables
[1회·또는 매일]    nb_bootstrap_gtfs_silver   → seed silver_arrives

[반복 ~5분 POC]    Pipeline → nb_poll_and_transform
                     S1 arrives → bronze → silver_arrives
                     → MERGE gold (ETA·freq·stale only — alert_* 안 건드림)

[반복 ~5분 POC]    Pipeline → nb_alerts_silver_gold
                     S2 servicealerts → bronze → silver_alerts (latest-only)
                     → MERGE gold alert_* by line_id
```

| 레포 파일 | Fabric 이름 |
|-----------|-------------|
| [`notebooks/nb_create_tables.py`](../notebooks/nb_create_tables.py) | `nb_create_tables` |
| [`notebooks/nb_bootstrap_gtfs_silver.py`](../notebooks/nb_bootstrap_gtfs_silver.py) | `nb_bootstrap_gtfs_silver` |
| [`notebooks/nb_poll_and_transform.py`](../notebooks/nb_poll_and_transform.py) | `nb_poll_and_transform` |
| [`notebooks/nb_alerts_silver_gold.py`](../notebooks/nb_alerts_silver_gold.py) | `nb_alerts_silver_gold` |

복붙: `# COMMAND ----------`로 셀 분할. Lakehouse attach.  
`from emt_pipeline` / `sys.path` 없음.

**Alerts:** `%pip` 셀 **넣지 말 것** (Pipeline에서 `MagicUsageError`).  
`gtfs-realtime-bindings` 불필요 — 노트북에 proto 디코더 인라인. `requests` 없으면 stdlib `urllib` 사용.

---

## Variable Library

`var_emt_madrid`: `EMT_CLIENT_ID`, `EMT_MADRID_PASS_KEY`  
→ **arrives** 노트북만 사용. Alerts(S2 proto)는 무인증.

---

## Pipeline

| Pipeline (예) | Notebook | Schedule |
|---------------|----------|----------|
| `pl_emt_arrives` | `nb_poll_and_transform` | ~5분부터 (계약 목표 ~60s) |
| `pl_emt_alerts` | `nb_alerts_silver_gold` | ~5분부터 (계약 목표 ~300s) |

- create / bootstrap는 스케줄에 넣지 말 것  
- arrives 잡은 **절대** Gold `alert_*`를 덮어쓰지 않음  
- 두 Pipeline이 같은 `gold_emt_stop_line`에 MERGE → 가끔 `ConcurrentAppendException` 가능. 노트북에 **재시도** 있음. 스케줄을 2–3분 어긋나게 하면 더 드묾. 

---

## Data Agent

→ `gold_emt_stop_line` (스키마 동일, 재바인딩 불필요). US-07 = `alert_*`.

---

## 체크리스트

- [ ] create/migrate Run → `silver_arrives` 건수 = 옛 `silver_emt`, `silver_alerts` 존재  
- [ ] `silver_emt` 없음  
- [ ] bootstrap / poll / **alerts** 노트북 v4.3 복붙·저장  
- [ ] arrives Pipeline 1회 성공 (`alert_*` 기존 값 유지)  
- [ ] alerts Pipeline 1회 성공 (`silver_alerts` > 0, gold `alert_active` 스모크)  
- [ ] Agent gold 스모크 (ETA + US-07)  
