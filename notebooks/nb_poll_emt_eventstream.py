# Fabric notebook source — data-source-contract-v4.2
#
# Thin wrapper: delegates to src/emt_pipeline/poller.py

# COMMAND ----------

# MAGIC %md
# MAGIC # Poll EMT arrives → Eventstream (thin wrapper)

# COMMAND ----------

# MAGIC %pip install azure-eventhub --quiet

# COMMAND ----------

stop_ids = ""  # @param {type:"string"}
variable_library_name = "var_emt_madrid"  # @param {type:"string"}
poll_interval_sec = 60  # @param {type:"number"}
max_rounds = 30  # @param {type:"number"}
max_retries_per_stop = 2  # @param {type:"number"}
token_skew_sec = 90  # @param {type:"number"}
eventstream_connection_string = ""  # @param {type:"string"}

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

from emt_pipeline.poller import run_eventstream_poller

run_eventstream_poller(
    spark,
    stop_ids=stop_ids,
    variable_library_name=variable_library_name,
    poll_interval_sec=poll_interval_sec,
    max_rounds=max_rounds,
    max_retries_per_stop=max_retries_per_stop,
    token_skew_sec=token_skew_sec,
    eventstream_connection_string=eventstream_connection_string,
)
