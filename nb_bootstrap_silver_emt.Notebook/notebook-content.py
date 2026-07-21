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

# # Bootstrap silver_emt (thin v0.1.2)
#
# Calls `emt_pipeline.bootstrap.run_bootstrap`.

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

gtfs_zip_path = "/lakehouse/default/Files/gtfs/gtfs_emt.zip"  # @param {type:"string"}
gtfs_zip_url = "https://datos.emtmadrid.es/dataset/9b23259a-4491-494b-9695-36a7709b2c12/resource/3cba2058-9833-422c-a704-bf992d31d2ee/download/gtfs_emt.zip"  # @param {type:"string"}
geofence_lat = 40.416729  # @param {type:"number"}
geofence_lon = -3.703339  # @param {type:"number"}
geofence_radius_m = 600  # @param {type:"number"}
variable_library_name = "var_emt_madrid"  # @param {type:"string"}
line_ids_override = ""  # @param {type:"string"}

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }


# CELL ********************

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

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
