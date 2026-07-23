"""Orchestrator: GTFS + EMT catalogue bootstrap."""
from __future__ import annotations

from pipeline.config.constants import (
    GEOFENCE_LAT,
    GEOFENCE_LON,
    GEOFENCE_RADIUS_M,
)
from pipeline.orchestrator.bootstrap_impl import run_bootstrap as _run_bootstrap

_DEFAULT_GTFS_URL = (
    "https://datos.emtmadrid.es/dataset/9b23259a-4491-494b-9695-36a7709b2c12/"
    "resource/3cba2058-9833-422c-a704-bf992d31d2ee/download/gtfs_emt.zip"
)


def run_bootstrap(
    spark,
    *,
    gtfs_zip_path: str = "/lakehouse/default/Files/gtfs/gtfs_emt.zip",
    gtfs_zip_url: str = _DEFAULT_GTFS_URL,
    geofence_lat: float = GEOFENCE_LAT,
    geofence_lon: float = GEOFENCE_LON,
    geofence_radius_m: int = GEOFENCE_RADIUS_M,
    variable_library_name: str = "var_emt_madrid",
    line_ids_override: str = "",
) -> None:
    _run_bootstrap(
        spark,
        gtfs_zip_path=gtfs_zip_path,
        gtfs_zip_url=gtfs_zip_url,
        geofence_lat=geofence_lat,
        geofence_lon=geofence_lon,
        geofence_radius_m=geofence_radius_m,
        variable_library_name=variable_library_name,
        line_ids_override=line_ids_override,
    )
