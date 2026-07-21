# Fabric notebook source — data-source-contract-v4.2
#
# Thin wrapper: delegates to src/emt_pipeline/direct_ingest.py

# COMMAND ----------

# MAGIC %md
# MAGIC # Direct ingest arrives (thin wrapper)

# COMMAND ----------

stop_ids = ""  # @param {type:"string"}
variable_library_name = "var_emt_madrid"  # @param {type:"string"}
bronze_table = "bronze_emt_raw"  # @param {type:"string"}
max_retries_per_stop = 2  # @param {type:"number"}
token_skew_sec = 90  # @param {type:"number"}

# COMMAND ----------

import sys
from pathlib import Path

_cwd = Path.cwd().resolve()
_candidates = [_cwd, *_cwd.parents, Path("/lakehouse/default/Files"), Path("/lakehouse/default/Files/repo"), Path("/lakehouse/default/Files/microsoft")]
for _base in _candidates:
    _src = _base / "src"
    if (_src / "emt_pipeline").exists():
        _src_s = str(_src)
        if _src_s not in sys.path:
            sys.path.insert(0, _src_s)
        break
else:
    raise RuntimeError("Cannot locate src/emt_pipeline from this notebook runtime.")

from emt_pipeline.direct_ingest import run_direct_ingest

run_direct_ingest(
    spark,
    stop_ids=stop_ids,
    variable_library_name=variable_library_name,
    bronze_table=bronze_table,
    max_retries_per_stop=max_retries_per_stop,
    token_skew_sec=token_skew_sec,
)
