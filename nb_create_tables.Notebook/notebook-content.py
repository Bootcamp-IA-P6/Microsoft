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

# # Create tables (thin v0.1.2)
#
# Calls `emt_pipeline.tables.recreate_tables` — DROP legacy + recreate contract tables.

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

from emt_pipeline.tables import recreate_tables

recreate_tables(spark)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
