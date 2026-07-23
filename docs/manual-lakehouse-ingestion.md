# 수동 적재 가이드 — Lakehouse + Notebook · **contract v4.3.1** · **Phase 3**

**계약:** [`data-source-contract-v4.md`](./data-source-contract-v4.md) (v4.3.1) — **스키마 변경 없음**  
**코드:** 레포 `pipeline/` → Lakehouse `Files/python/pipeline/`  
**목표:** Spark **transform**은 외부 API를 호출하지 않음. Ingest와 Transform Pipeline 분리.

---

## Fabric 업로드

1. `pipeline/` → `Files/python/pipeline/`  
2. 노트북 복붙 (`# COMMAND ----------` 셀 분할)

---

## Phase 3 흐름 (권장)

```text
[1회]  nb_create_tables
[1회·매일] nb_bootstrap_gtfs_silver

pl_emt_arrives_ingest    → nb_ingest_arrives      # HTTP → bronze
pl_emt_arrives_transform → nb_transform_arrives   # bronze → silver → gold (ETA/freq)

pl_emt_alerts_ingest     → nb_ingest_alerts       # HTTP → bronze
pl_emt_alerts_transform  → nb_transform_alerts    # bronze → silver_alerts → gold alert_*
```

| 레포 파일 | 역할 |
|-----------|------|
| [`nb_ingest_arrives.py`](../notebooks/nb_ingest_arrives.py) | S1 → bronze |
| [`nb_transform_arrives.py`](../notebooks/nb_transform_arrives.py) | bronze → silver/gold (no HTTP) |
| [`nb_ingest_alerts.py`](../notebooks/nb_ingest_alerts.py) | S2 → bronze |
| [`nb_transform_alerts.py`](../notebooks/nb_transform_alerts.py) | bronze → silver/gold alert_* (no HTTP) |
| [`nb_poll_and_transform.py`](../notebooks/nb_poll_and_transform.py) | **fallback** 합본 (ingest+transform) |
| [`nb_alerts_silver_gold.py`](../notebooks/nb_alerts_silver_gold.py) | **fallback** 합본 |
| create / bootstrap | Phase 2와 동일 |

Transform은 Starter Pool + Spark. Ingest는 지금은 짧은 Spark 노트북 (**UDF equivalent**); 이후 Fabric User Data Function으로 옮길 자리.

---

## Variable Library

`var_emt_madrid` → **ingest arrives** + bootstrap만.

---

## 스케줄 예

| Pipeline | Notebook | 주기 (POC) |
|----------|----------|------------|
| arrives ingest | `nb_ingest_arrives` | ~5분 |
| arrives transform | `nb_transform_arrives` | ingest 직후 또는 ~5분 (약간 지연 OK) |
| alerts ingest | `nb_ingest_alerts` | ~5분 |
| alerts transform | `nb_transform_alerts` | ingest 직후 |

Arrives transform은 **절대** `alert_*`를 덮지 않음. Alerts transform은 ETA/freq를 덮지 않음.

---

## Data Agent

→ `gold_emt_stop_line` (재바인딩 불필요).

---

## 체크리스트 (Phase 3)

- [ ] `Files/python/pipeline/` 최신 업로드  
- [ ] ingest/transform 노트북 4개 복붙  
- [ ] Pipeline을 합본 → 분리 스케줄로 전환  
- [ ] transform 로그에 EMT/HTTP 호출 없음 확인  
- [ ] gold ETA + `alert_*` 스모크  
- [ ] (나중) ingest를 Fabric User Data Function으로 이전  
