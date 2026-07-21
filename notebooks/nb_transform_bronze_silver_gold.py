# Fabric notebook source — data-source-contract-v4.2
#
# Thin wrapper: delegates to src/emt_pipeline/transform.py

# COMMAND ----------

# MAGIC %md
# MAGIC # Transform bronze → silver → gold (thin wrapper)

# COMMAND ----------

stale_after_sec = 180  # @param {type:"number"}
bronze_table = "bronze_emt_raw"  # @param {type:"string"}
incremental = True  # @param {type:"boolean"}
freq_min_samples = 20  # @param {type:"number"}

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

from emt_pipeline.transform import run_transform

run_transform(
    spark,
    stale_after_sec=stale_after_sec,
    bronze_table=bronze_table,
    incremental=incremental,
    freq_min_samples=freq_min_samples,
)
