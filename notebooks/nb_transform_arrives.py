# Fabric notebook — Phase 3 transform (bronze → silver → gold, no HTTP)
# Prereq: Files/python/pipeline/ ; bronze arrives rows from nb_ingest_arrives

# COMMAND ----------

# MAGIC %md
# MAGIC # Transform arrives → silver → gold ETA/freq (Phase 3)
# MAGIC Does **not** call EMT API. Does **not** update `alert_*`.

# COMMAND ----------

bronze_table = "bronze_emt_raw"  # @param {type:"string"}
stale_after_sec = 900  # @param {type:"number"}
incremental = True  # @param {type:"boolean"}
freq_min_samples = 20  # @param {type:"number"}
verbose_display = False  # @param {type:"boolean"}

# COMMAND ----------

import sys

_FILES_PY = "/lakehouse/default/Files/python"
if _FILES_PY not in sys.path:
    sys.path.insert(0, _FILES_PY)

from pipeline.orchestrator.run_arrives import run_arrives_transform

run_arrives_transform(
    spark,
    bronze_table=bronze_table,
    stale_after_sec=int(stale_after_sec),
    incremental=bool(incremental),
    freq_min_samples=int(freq_min_samples),
    verbose_display=bool(verbose_display),
)
