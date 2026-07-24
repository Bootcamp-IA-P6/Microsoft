# RTI (Phase 4)

Guide: [docs/phase4-rti.md](../docs/phase4-rti.md)

| Path | Fabric? | Role |
|------|---------|------|
| `udf/udf_emt_ingest.py` | **Paste → UDF** | Poll + silver expand → Eventstream |
| `kql/` | **Paste → Eventhouse** | DDL + `gold_emt_stop_line_build` |
| `lib/` | No | Spark-free ports (mirrored in UDF) |
| `ingest/` | **No** | Laptop JSONL only |

UDF entrypoints: `ping`, `poll_arrives_scope`, `poll_alerts_scope`.  
Connection aliases in repo: `lhemtmadrid`, `varemtmadrid` (match portal).
