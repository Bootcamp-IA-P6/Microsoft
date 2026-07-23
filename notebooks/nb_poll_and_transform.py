# Fabric notebook — contract v4.3.1 · Phase 2 thin orchestrator
# Prereq: upload repo `pipeline/` → Lakehouse Files/python/pipeline/
# If ImportError requests: run once → %pip install requests
# Guide: docs/manual-lakehouse-ingestion.md

# COMMAND ----------

# MAGIC %md
# MAGIC # Poll arrives → bronze → silver → gold ETA/freq (Phase 2)
# MAGIC Does **not** update Gold `alert_*`. Freq = ADR-038 visit first-seen.

# COMMAND ----------

stop_ids = ""  # @param {type:"string"}
variable_library_name = "var_emt_madrid"  # @param {type:"string"}
bronze_table = "bronze_emt_raw"  # @param {type:"string"}
max_retries_per_stop = 2  # @param {type:"number"}
token_skew_sec = 90  # @param {type:"number"}
stale_after_sec = 900  # @param {type:"number"}
incremental = True  # @param {type:"boolean"}
freq_min_samples = 20  # @param {type:"number"}
verbose_display = False  # @param {type:"boolean"}

# COMMAND ----------

import sys

_FILES_PY = "/lakehouse/default/Files/python"
if _FILES_PY not in sys.path:
    sys.path.insert(0, _FILES_PY)

from pipeline.orchestrator.run_arrives import run_arrives

run_arrives(
    spark,
    stop_ids=stop_ids,
    variable_library_name=variable_library_name,
    bronze_table=bronze_table,
    max_retries_per_stop=int(max_retries_per_stop),
    token_skew_sec=int(token_skew_sec),
    stale_after_sec=int(stale_after_sec),
    incremental=bool(incremental),
    freq_min_samples=int(freq_min_samples),
    verbose_display=bool(verbose_display),
)
