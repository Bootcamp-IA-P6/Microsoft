# Fabric notebook source — data-source-contract-v4.2
#
# Thin wrapper: delegates to src/emt_pipeline/tables.py

# COMMAND ----------

# MAGIC %md
# MAGIC # Create tables (thin wrapper)
# MAGIC Contract logic lives in `src/emt_pipeline/tables.py`.

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

from emt_pipeline.tables import recreate_tables

recreate_tables(spark)
