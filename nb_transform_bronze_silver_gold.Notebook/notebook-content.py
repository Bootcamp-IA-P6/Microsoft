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
# META     },
# META     "environment": {
# META       "environmentId": "fe076382-f415-4fda-b39c-e8019c36ad8a",
# META       "workspaceId": "8bfdf6eb-bff5-4647-9484-daa63a5b7ff0"
# META     }
# META   }
# META }

# CELL ********************

# MAGIC %md
# MAGIC # Transform bronze → silver → gold
# MAGIC
# MAGIC Thin wrapper → `emt_pipeline.transform`.

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

stale_after_sec = 180  # @param {type:"number"}
bronze_table = "bronze_emt_raw"  # @param {type:"string"}
incremental = True  # @param {type:"boolean"}
freq_min_samples = 20  # @param {type:"number"}

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from emt_pipeline.transform import run_transform

run_transform(
    spark,
    stale_after_sec=stale_after_sec,
    bronze_table=bronze_table,
    incremental=incremental,
    freq_min_samples=freq_min_samples,
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

