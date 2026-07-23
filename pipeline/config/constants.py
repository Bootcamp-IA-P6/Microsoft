"""Shared EMT pipeline constants (contract v4.3.1)."""
from __future__ import annotations

import json

BASE_URL = "https://openapi.emtmadrid.es"
TZ_NOTE = "Europe/Madrid"
SERVICEALERTS_URL = "https://openapi.emtmadrid.es/v1/bus/servicealerts/proto"

BRONZE_TABLE = "bronze_emt_raw"
SILVER_ARRIVES = "silver_arrives"
SILVER_ALERTS = "silver_alerts"
GOLD_TABLE = "gold_emt_stop_line"

ARRIVES_BODY = json.dumps(
    {
        "cultureInfo": "es",
        "Text_StopRequired_YN": "Y",
        "Text_EstimationsRequired_YN": "Y",
        "Text_IncidencesRequired_YN": "N",
    }
).encode("utf-8")
AUTH_API_CODES = frozenset({"80", "81", "82", "83", "89", "90"})
HTTP_HEADERS_JSON = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; emt-pipeline/0.1; "
        "+https://github.com/Bootcamp-IA-P6/Microsoft)"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Connection": "close",
}
HTTP_HEADERS_PROTO = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; emt-pipeline/0.1; "
        "+https://github.com/Bootcamp-IA-P6/Microsoft)"
    ),
    "Accept": "application/x-protobuf,application/octet-stream,*/*",
    "Connection": "close",
}

# ADR-038 observed headway
FREQ_VISIT_BREAK_MIN = 20.0
FREQ_GAP_MIN_MIN = 1.0
FREQ_GAP_MAX_MIN = 60.0
FREQ_MIN_SAMPLES_DEFAULT = 20

GEOFENCE_LAT = 40.416729
GEOFENCE_LON = -3.703339
GEOFENCE_RADIUS_M = 600
