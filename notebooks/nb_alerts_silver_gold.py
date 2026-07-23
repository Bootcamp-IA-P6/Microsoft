# Fabric notebook — contract v4.3.1 · Phase 2 thin orchestrator
# Prereq: upload repo `pipeline/` → Lakehouse Files/python/pipeline/
# No %pip / no gtfs-realtime-bindings — decoder is in pipeline.ingestion.gtfs_rt_client
# Guide: docs/manual-lakehouse-ingestion.md

# COMMAND ----------

# MAGIC %md
# MAGIC # Alerts → bronze → silver_alerts → gold `alert_*` (Phase 2)
# MAGIC Does **not** update ETA / freq / stale.

# COMMAND ----------

bronze_table = "bronze_emt_raw"  # @param {type:"string"}
silver_alerts_table = "silver_alerts"  # @param {type:"string"}
gold_table = "gold_emt_stop_line"  # @param {type:"string"}
servicealerts_url = "https://openapi.emtmadrid.es/v1/bus/servicealerts/proto"  # @param {type:"string"}
verbose_display = False  # @param {type:"boolean"}

# COMMAND ----------

import sys

_FILES_PY = "/lakehouse/default/Files/python"
if _FILES_PY not in sys.path:
    sys.path.insert(0, _FILES_PY)

from pipeline.orchestrator.run_alerts import run_alerts

run_alerts(
    spark,
    bronze_table=bronze_table,
    silver_alerts_table=silver_alerts_table,
    gold_table=gold_table,
    servicealerts_url=servicealerts_url,
    verbose_display=bool(verbose_display),
)
