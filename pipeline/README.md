# EMT Madrid Spark pipeline (Phase 2–3)

Upload this folder to Fabric Lakehouse:

```text
Files/python/pipeline/   ← contents of this package
```

Notebooks add `/lakehouse/default/Files/python` to `sys.path`.

## Phase 3 entrypoints

| Function | Role |
|----------|------|
| `run_arrives_ingest` | HTTP → bronze |
| `run_arrives_transform` | bronze → silver/gold (no HTTP) |
| `run_alerts_ingest_only` | HTTP → bronze |
| `run_alerts_transform_only` | bronze → silver/gold alert_* (no HTTP) |
| `run_arrives` / `run_alerts` | combined fallback |

Contract tables unchanged: `bronze_emt_raw`, `silver_arrives`, `silver_alerts`, `gold_emt_stop_line`.
