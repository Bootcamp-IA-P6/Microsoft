# Eventstream arrives 적재 — Fabric 모듈 MVP (contract v4.2)

핵심: **로직은** `emt_pipeline` **패키지(wheel)**, Notebook은 **Fabric 아이템 thin wrapper**, 공용 의존성은 **Environment**.

## 아키텍처

```text
src/emt_pipeline/                         # SoT (로컬 개발)
  common.py / fabric.py / tables.py
  bootstrap.py / poller.py / direct_ingest.py / transform.py

pyproject.toml                            # wheel 빌드
scripts/build_emt_wheel.sh                # wheel → Environment CustomLibraries

env_emt_pipeline.Environment/             # Fabric Git 아이템
  Libraries/CustomLibraries/emt_pipeline-*.whl
  Libraries/PublicLibraries/environment.yml   # azure-eventhub
  Setting/Sparkcompute.yml

nb_*.Notebook/                            # Fabric Git 아이템
  .platform
  notebook-content.py                     # import emt_pipeline.* only
```

| 층 | 역할 |
| ---- | ---- |
| `emt_pipeline` wheel | 비즈니스 로직 |
| `env_emt_pipeline` | custom wheel + public deps (workspace default) |
| `nb_*.Notebook` | 파라미터 + 함수 호출만 |

**하지 않는 것:** `sys.path` Lakehouse 탐색, notebook마다 `%pip`, Resources에 모듈 복붙, 노트북 메타에 Environment 강제 바인딩.

## 테이블 (ADR-015)

| 테이블 | 역할 |
| ---- | ---- |
| `bronze_emt_raw` | S1/S2 raw — 전 컬럼 STRING (ADR-018) |
| `silver_emt` | append-only poll + catalogue seed |
| `gold_emt_stop_line` | Data Agent serving |

## Cadence

| 작업 | 계약 (ADR-029 / v4.2) | **지금 POC** |
| ---- | ---- | ---- |
| GTFS + S1 line stops seed (+ calendar) | **1×/일** | **1×/일** (`pl_emt_daily`) |
| S1 `arrives` poll → bronze | 이상적 **~60s** | **3분** (`poll_interval_sec=180`) |
| Transform bronze → silver → gold | arrives와 같이 **~60s** | **poll 직후 같은 파이프** (3분마다) |
| `is_stale` | **180s** (60s×3) | **540s** (180s×3) — POC만 |
| `nb_create_tables` | 초기/스키마 리셋 | **수동만** — Pipeline에 넣지 않음 |

GTFS URL (삭제하지 말 것):

`https://datos.emtmadrid.es/dataset/9b23259a-4491-494b-9695-36a7709b2c12/resource/3cba2058-9833-422c-a704-bf992d31d2ee/download/gtfs_emt.zip`

SoT: `fabric_ids.json` → `gtfs.zip_url`

## Fabric에 올리는 법

1. branch를 Fabric Workspace Git에 연결.
2. Sync 후: `env_emt_pipeline`, `nb_*`, Lakehouse/Eventstream/Variable Library.
3. Environment **Publish**.
4. Workspace default Environment = `env_emt_pipeline`.
5. Eventstream: Custom Endpoint → Lakehouse `bronze_emt_raw`.
6. Variable Library `var_emt_madrid` + Eventstream connection string.

## 패키지 수정 후 배포

```bash
./scripts/build_emt_wheel.sh
# commit Environment CustomLibraries wheel
# Fabric sync → Environment Publish
```

## 수동 1회 (Pipeline 밖)

1. **`nb_create_tables`** — DROP legacy + CREATE 3 tables. **스케줄/파이프에 넣지 말 것.**
2. (선택) bootstrap 한 번 수동 Run으로 seed 확인.

## Pipeline

### `pl_emt_daily` — 하루 1번

| Step | Notebook | 비고 |
| ---- | ---- | ---- |
| 1 | `nb_bootstrap_silver_emt` | `gtfs_zip_url` = 위 EMT GTFS URL (기본값에 이미 있음) |

- Schedule: 매일 1회 (예: 06:00 Europe/Madrid)
- **포함 금지:** `nb_create_tables`
- GTFS는 `gtfs_zip_url`로 **자동 다운로드** (`emt_pipeline` ≥0.1.2: `requests` + 재시도 + SSL fallback). Fabric에서 옛 `urlretrieve` SSL EOF가 나던 경로를 대체함.
- EMT OpenAPI(`login` / `line_stops` / `arrives`)도 `http_json`이 **requests + 재시도** (`emt_pipeline` ≥0.1.3). 같은 SSL EOF가 line_stops에서 나던 문제 대응.

### `pl_emt_arrives` — 3분마다 (POC)

| Step | Notebook | 파라미터 |
| ---- | ---- | ---- |
| 1 | `nb_poll_emt_eventstream` | `poll_interval_sec=180`, `max_rounds=1` |
| 2 | `nb_transform_bronze_silver_gold` | `stale_after_sec=540`, `incremental=True` |

- Schedule: **every 3 minutes**
- 한 실행 = poll 1라운드 → 바로 transform
- Eventstream이 `bronze_emt_raw`로 붙어야 poll이 의미 있음
- Fallback: Eventstream 막히면 step1을 `nb_ingest_emt_arrives`로 교체 (같은 3분 스케줄)

### Fabric에서 만드는 법

1. New → **Data pipeline**
2. Activity **Notebook** 추가 → 워크스페이스의 `nb_*` 선택
3. Base parameters를 노트북 `@param`에 매핑 (비우면 노트북 기본값 사용)
4. `pl_emt_arrives`: poll **On success** → transform
5. Schedule 설정 후 Run once로 검증

나중에 계약(~60s)으로 조일 때: 스케줄 1분 + `poll_interval_sec=60` + `stale_after_sec=180` + `max_rounds=1`.

## 검증 체크리스트

- [ ] thin 노트북 (`thin v0.1.1`) 유지, 구버전 긴 SQL 아님
- [ ] `import emt_pipeline` / `azure.eventhub` OK (workspace default env)
- [ ] `nb_create_tables` 수동 1회 후 테이블 3개
- [ ] `pl_emt_daily` bootstrap 성공 (GTFS URL로 zip 다운로드)
- [ ] `pl_emt_arrives` 3분 주기: bronze 증가 → silver/gold 갱신
