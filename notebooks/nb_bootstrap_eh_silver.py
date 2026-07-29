# Fabric notebook — Phase 5 bootstrap → Eventhouse silver_arrives (seed tag)
# Prereq:
#   1. Paste KQL Step A (02→05→04) already done — seed exclude live
#   2. es_emt_arrives_silver → silver_arrives (allow silver_arrives_seed if filtered)
#   3. Upload: Files/python/pipeline/ + Files/python/rti/
# Guide: docs/phase4-rti.md Step D / F
# VL keys: EMT_CLIENT_ID, EMT_MADRID_PASS_KEY
# Send path: requests + SAS only (NO azure.eventhub)
#
# IMPORTANT — do NOT use %pip here:
#   Pipeline notebook runs disable %pip by default → MagicUsageError.
#   Fabric Spark runtime already includes requests; use that.

# COMMAND ----------

# MAGIC %md
# MAGIC # Bootstrap GTFS → EH `silver_arrives` (`emt_record=silver_arrives_seed`)
# MAGIC - Does **not** write Lakehouse. Arrives schedule stays on.
# MAGIC - Event Hub send = `requests` + SAS (no `azure.eventhub`).
# MAGIC - **No `%pip`** (Pipeline에서 기본 비활성). `requests` 없으면 Environment에만 추가.

# COMMAND ----------

gtfs_zip_path = "/lakehouse/default/Files/gtfs/gtfs_emt.zip"  # @param {type:"string"}
# Leave empty if zip already on Files (avoids re-download). Set URL only when zip missing.
gtfs_zip_url = ""  # @param {type:"string"}
geofence_lat = 40.416729  # @param {type:"number"}
geofence_lon = -3.703339  # @param {type:"number"}
geofence_radius_m = 600  # @param {type:"number"}
# Smoke first: "005" or "027". Empty = all candidate lines (slow / more EMT timeouts).
line_ids_override = "005"  # @param {type:"string"}

# Eventstream Custom endpoint (same values as UDF ARRIVES_SILVER_CONN / HUB)
arrives_silver_conn = ""  # @param {type:"string"}
arrives_silver_hub = ""  # @param {type:"string"}

variable_library_name = "var_emt_madrid"  # @param {type:"string"}
client_id_override = ""  # @param {type:"string"}
pass_key_override = ""  # @param {type:"string"}

# COMMAND ----------

import sys

try:
    import requests  # noqa: F401  — Fabric Spark runtime built-in
except ImportError as exc:  # noqa: BLE001
    raise RuntimeError(
        "requests missing in this Spark session. Do NOT add %pip (disabled in Pipeline). "
        "Attach a Fabric Environment with requests, or set notebook activity parameter "
        "_inlineInstallationEnabled=True only for interactive %pip experiments."
    ) from exc

_FILES_PY = "/lakehouse/default/Files/python"
if _FILES_PY not in sys.path:
    sys.path.insert(0, _FILES_PY)

client_id = (client_id_override or "").strip()
pass_key = (pass_key_override or "").strip()
vl_err = None
if not client_id or not pass_key:
    try:
        from pipeline.config.settings import load_emt_credentials

        client_id, pass_key = load_emt_credentials(variable_library_name)
    except Exception as exc:  # noqa: BLE001
        vl_err = exc
        print(f"Variable Library load failed ({exc!r})")

if not (arrives_silver_conn or "").strip():
    raise RuntimeError("Set arrives_silver_conn = es_emt_arrives_silver Custom endpoint SAS connection string")

if not client_id or not pass_key:
    raise RuntimeError(
        "EMT credentials missing. VL needs EMT_CLIENT_ID + EMT_MADRID_PASS_KEY "
        f"(library={variable_library_name!r}"
        + (f", err={vl_err!r}" if vl_err else "")
        + ") or set client_id_override / pass_key_override"
    )

print(
    f"Using EMT_CLIENT_ID len={len(client_id)} prefix={client_id[:8]}… "
    f"has_at={'@' in client_id}"
)

import importlib

import pipeline.orchestrator.bootstrap_eh_impl as _beh

_beh = importlib.reload(_beh)
run_bootstrap_eh = _beh.run_bootstrap_eh

# If zip missing and url empty, fall back to EMT datos URL once
_zip_url = (gtfs_zip_url or "").strip()
if not _zip_url:
    from pathlib import Path

    if not Path(gtfs_zip_path).is_file():
        _zip_url = (
            "https://datos.emtmadrid.es/dataset/9b23259a-4491-494b-9695-36a7709b2c12/"
            "resource/3cba2058-9833-422c-a704-bf992d31d2ee/download/gtfs_emt.zip"
        )
        print(f"GTFS zip missing — will download once to {gtfs_zip_path}")

msg = run_bootstrap_eh(
    client_id=client_id,
    pass_key=pass_key,
    arrives_silver_conn=arrives_silver_conn,
    arrives_silver_hub=arrives_silver_hub,
    gtfs_zip_path=gtfs_zip_path,
    gtfs_zip_url=_zip_url,
    geofence_lat=float(geofence_lat),
    geofence_lon=float(geofence_lon),
    geofence_radius_m=int(geofence_radius_m),
    line_ids_override=line_ids_override,
)
print(msg)
print("Next: EH KQL — silver_arrives | where emt_record == 'silver_arrives_seed' | take 5")
