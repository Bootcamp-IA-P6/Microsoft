# Fabric notebook — Phase 3 ingest (HTTP → bronze only)
# Prereq: Files/python/pipeline/ uploaded
# Pipeline: schedule this separately from transform (~60s target / ~5min POC)

# COMMAND ----------

# MAGIC %md
# MAGIC # Ingest arrives → bronze (Phase 3)
# MAGIC No silver/gold. Transform = `nb_transform_arrives`.

# COMMAND ----------

stop_ids = ""  # @param {type:"string"}
variable_library_name = "var_emt_madrid"  # @param {type:"string"}
bronze_table = "bronze_emt_raw"  # @param {type:"string"}
max_retries_per_stop = 2  # @param {type:"number"}
token_skew_sec = 90  # @param {type:"number"}
verbose_display = False  # @param {type:"boolean"}

# COMMAND ----------

import sys

_FILES_PY = "/lakehouse/default/Files/python"
if _FILES_PY not in sys.path:
    sys.path.insert(0, _FILES_PY)

from pipeline.orchestrator.run_arrives import run_arrives_ingest

run_arrives_ingest(
    spark,
    stop_ids=stop_ids,
    variable_library_name=variable_library_name,
    bronze_table=bronze_table,
    max_retries_per_stop=int(max_retries_per_stop),
    token_skew_sec=int(token_skew_sec),
    verbose_display=bool(verbose_display),
)
