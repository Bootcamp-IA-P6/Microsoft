# Fabric notebook source — data-source-contract-v4.2
#
# Thin wrapper: delegates to src/emt_pipeline/bootstrap.py

# COMMAND ----------

# MAGIC %md
# MAGIC # Bootstrap seed (thin wrapper)

# COMMAND ----------

gtfs_zip_path = "/lakehouse/default/Files/gtfs/gtfs_emt.zip"  # @param {type:"string"}
gtfs_zip_url = ""  # @param {type:"string"}
geofence_lat = 40.416729  # @param {type:"number"}
geofence_lon = -3.703339  # @param {type:"number"}
geofence_radius_m = 600  # @param {type:"number"}
variable_library_name = "var_emt_madrid"  # @param {type:"string"}
line_ids_override = ""  # @param {type:"string"}

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

from emt_pipeline.bootstrap import run_bootstrap

run_bootstrap(
    spark,
    gtfs_zip_path=gtfs_zip_path,
    gtfs_zip_url=gtfs_zip_url,
    geofence_lat=geofence_lat,
    geofence_lon=geofence_lon,
    geofence_radius_m=geofence_radius_m,
    variable_library_name=variable_library_name,
    line_ids_override=line_ids_override,
)
