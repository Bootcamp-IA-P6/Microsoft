# Fabric notebook — Phase 3 ingest alerts (HTTP → bronze only)
# Prereq: Files/python/pipeline/

# COMMAND ----------

# MAGIC %md
# MAGIC # Ingest servicealerts → bronze (Phase 3)
# MAGIC No silver/gold. Transform = `nb_transform_alerts`.

# COMMAND ----------

bronze_table = "bronze_emt_raw"  # @param {type:"string"}
servicealerts_url = "https://openapi.emtmadrid.es/v1/bus/servicealerts/proto"  # @param {type:"string"}

# COMMAND ----------

import sys

_FILES_PY = "/lakehouse/default/Files/python"
if _FILES_PY not in sys.path:
    sys.path.insert(0, _FILES_PY)

from pipeline.orchestrator.run_alerts import run_alerts_ingest_only

run_alerts_ingest_only(
    spark,
    bronze_table=bronze_table,
    servicealerts_url=servicealerts_url,
)
