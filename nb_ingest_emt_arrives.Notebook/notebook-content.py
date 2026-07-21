# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "6fc8888d-9aaf-46c0-b6fc-5aace3d34640",
# META       "default_lakehouse_name": "lh_emt_madrid",
# META       "default_lakehouse_workspace_id": "8bfdf6eb-bff5-4647-9484-daa63a5b7ff0",
# META       "known_lakehouses": [
# META         {
# META           "id": "6fc8888d-9aaf-46c0-b6fc-5aace3d34640"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Direct ingest fallback (thin v0.1.1)
#
# Calls `emt_pipeline.direct_ingest.run_direct_ingest`.

# CELL ********************

from emt_pipeline import __version__ as _emt_ver
print(f"=== emt_pipeline thin wrapper v{_emt_ver} ===")
print("If you still see CREATE TABLE / long SQL bodies, discard workspace notebook changes and Update from Git.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }


# CELL ********************

stop_ids = ""  # @param {type:"string"}
variable_library_name = "var_emt_madrid"  # @param {type:"string"}
bronze_table = "bronze_emt_raw"  # @param {type:"string"}
max_retries_per_stop = 2  # @param {type:"number"}
token_skew_sec = 90  # @param {type:"number"}

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }


# CELL ********************

from emt_pipeline.direct_ingest import run_direct_ingest

run_direct_ingest(
    spark,
    stop_ids=stop_ids,
    variable_library_name=variable_library_name,
    bronze_table=bronze_table,
    max_retries_per_stop=max_retries_per_stop,
    token_skew_sec=token_skew_sec,
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
