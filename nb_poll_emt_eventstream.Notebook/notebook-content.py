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
# MAGIC # Poll EMT arrives → Eventstream
# MAGIC
# MAGIC Thin wrapper → `emt_pipeline.poller`.
# MAGIC
# MAGIC `azure-eventhub` comes from Environment public libraries — no `%pip`.

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

stop_ids = ""  # @param {type:"string"}
variable_library_name = "var_emt_madrid"  # @param {type:"string"}
poll_interval_sec = 60  # @param {type:"number"}
max_rounds = 30  # @param {type:"number"}
max_retries_per_stop = 2  # @param {type:"number"}
token_skew_sec = 90  # @param {type:"number"}
eventstream_connection_string = ""  # @param {type:"string"}

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

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

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

