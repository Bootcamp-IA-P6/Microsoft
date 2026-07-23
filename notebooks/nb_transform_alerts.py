# Fabric notebook — Phase 3 transform alerts (bronze → silver → gold alert_*, no HTTP)

# COMMAND ----------

# MAGIC %md
# MAGIC # Transform alerts → silver_alerts → gold `alert_*` (Phase 3)
# MAGIC Reads latest bronze `servicealerts` payload. No EMT HTTP.

# COMMAND ----------

bronze_table = "bronze_emt_raw"  # @param {type:"string"}
silver_alerts_table = "silver_alerts"  # @param {type:"string"}
gold_table = "gold_emt_stop_line"  # @param {type:"string"}
verbose_display = False  # @param {type:"boolean"}

# COMMAND ----------

import sys

_FILES_PY = "/lakehouse/default/Files/python"
if _FILES_PY not in sys.path:
    sys.path.insert(0, _FILES_PY)

from pipeline.orchestrator.run_alerts import run_alerts_transform_only

run_alerts_transform_only(
    spark,
    bronze_table=bronze_table,
    silver_alerts_table=silver_alerts_table,
    gold_table=gold_table,
    verbose_display=bool(verbose_display),
)
