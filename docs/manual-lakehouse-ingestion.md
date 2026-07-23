# 수동 적재 가이드 — Lakehouse + Notebook · **contract v4.3.1** · **Phase 2**

**계약:** [`data-source-contract-v4.md`](./data-source-contract-v4.md) (v4.3.1)  
**코드:** 레포 `pipeline/` 모듈 + 얇은 노트북 (`notebooks/nb_*.py`)  
**방식:** Environment / Git sync 없음. **Files/python** 업로드 + 노트북 복붙.  
**목표:** `gold_emt_stop_line` 유지·갱신. Arrives / alerts **분리** Pipeline. **스키마 변경 없음.**

---

## Fabric에 올릴 것 (Phase 2)

1. 레포 폴더 **`pipeline/`** 전체를 Lakehouse  
   `Files/python/pipeline/` 로 업로드 (덮어쓰기 OK).
2. `notebooks/nb_*.py` 네 개 **전체 복붙** (셀은 `# COMMAND ----------` 기준).

```text
/lakehouse/default/Files/python/pipeline/...
notebooks → Fabric Notebooks (이름 동일)
```

노트북 첫 코드 셀이 `sys.path`에 `/lakehouse/default/Files/python`을 넣는다.

---

## 테이블 (변경 없음)

| 테이블 | 역할 |
|--------|------|
| `bronze_emt_raw` | S1/S2 raw |
| `silver_arrives` | catalogue seed + poll history |
| `silver_alerts` | S2 alerts latest-only |
| `gold_emt_stop_line` | Data Agent (`alert_*` 포함) |

---

## 흐름

```text
[1회/마이그레이션] nb_create_tables
[1회·또는 매일]    nb_bootstrap_gtfs_silver

[반복] Pipeline → nb_poll_and_transform   # alert_* 안 건드림
[반복] Pipeline → nb_alerts_silver_gold   # ETA/freq 안 건드림
```

| 레포 파일 | Fabric 이름 |
|-----------|-------------|
| [`notebooks/nb_create_tables.py`](../notebooks/nb_create_tables.py) | `nb_create_tables` |
| [`notebooks/nb_bootstrap_gtfs_silver.py`](../notebooks/nb_bootstrap_gtfs_silver.py) | `nb_bootstrap_gtfs_silver` |
| [`notebooks/nb_poll_and_transform.py`](../notebooks/nb_poll_and_transform.py) | `nb_poll_and_transform` |
| [`notebooks/nb_alerts_silver_gold.py`](../notebooks/nb_alerts_silver_gold.py) | `nb_alerts_silver_gold` |

**Alerts:** `%pip` / `gtfs-realtime-bindings` 불필요 (디코더는 `pipeline.ingestion.gtfs_rt_client`).  
`requests` 없으면 arrives/bootstrap에서 한 번 `%pip install requests`.

---

## Variable Library

`var_emt_madrid`: `EMT_CLIENT_ID`, `EMT_MADRID_PASS_KEY` → arrives + bootstrap.

---

## Pipeline

| Pipeline (예) | Notebook | Schedule |
|---------------|----------|----------|
| `pl_emt_arrives` | `nb_poll_and_transform` | ~5분 POC |
| `pl_emt_alerts` | `nb_alerts_silver_gold` | ~5분 POC |

- create / bootstrap는 스케줄에 넣지 말 것  
- Instant: **Starter Pool** (Environment에 라이브러리 올리지 말 것 — on-demand 유발)

---

## Data Agent

→ `gold_emt_stop_line` (재바인딩 불필요).

---

## 체크리스트 (Phase 2)

- [ ] `Files/python/pipeline/` 업로드  
- [ ] 얇은 노트북 4개 복붙·저장  
- [ ] `nb_create_tables` Run  
- [ ] bootstrap (필요 시)  
- [ ] arrives Pipeline 1회 (`alert_*` 유지, freq ADR-038)  
- [ ] alerts Pipeline 1회  
- [ ] Agent 스모크  
