"""GTFS-RT FeedMessage decoder (servicealerts; no pip / no Spark)."""
from __future__ import annotations

# --- Inlined GTFS-RT FeedMessage decoder (servicealerts subset; no pip) ---
_GTFS_CAUSE = {
    1: "UNKNOWN_CAUSE",
    2: "OTHER_CAUSE",
    3: "TECHNICAL_PROBLEM",
    4: "STRIKE",
    5: "DEMONSTRATION",
    6: "ACCIDENT",
    7: "HOLIDAY",
    8: "WEATHER",
    9: "MAINTENANCE",
    10: "CONSTRUCTION",
    11: "POLICE_ACTIVITY",
    12: "MEDICAL_EMERGENCY",
}
_GTFS_EFFECT = {
    1: "NO_SERVICE",
    2: "REDUCED_SERVICE",
    3: "SIGNIFICANT_DELAYS",
    4: "DETOUR",
    5: "ADDITIONAL_SERVICE",
    6: "MODIFIED_SERVICE",
    7: "OTHER_EFFECT",
    8: "UNKNOWN_EFFECT",
    9: "STOP_MOVED",
    10: "NO_EFFECT",
    11: "ACCESSIBILITY_ISSUE",
}


def _pb_read_varint(buf: bytes, i: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        b = buf[i]
        i += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, i
        shift += 7


def _pb_skip(buf: bytes, i: int, wt: int) -> int:
    if wt == 0:
        _, i = _pb_read_varint(buf, i)
        return i
    if wt == 1:
        return i + 8
    if wt == 2:
        ln, i = _pb_read_varint(buf, i)
        return i + ln
    if wt == 5:
        return i + 4
    raise ValueError(f"unknown protobuf wire type {wt}")


def _pb_parse(buf: bytes, i: int, end: int, handlers: dict, out=None):
    if out is None:
        out = {}
    while i < end:
        key, i = _pb_read_varint(buf, i)
        fn, wt = key >> 3, key & 7
        if fn in handlers:
            i = handlers[fn](buf, i, wt, out)
        else:
            i = _pb_skip(buf, i, wt)
    return out, i


def _pb_len(buf: bytes, i: int, wt: int) -> tuple[int, int]:
    if wt != 2:
        raise ValueError("expected length-delimited")
    ln, i = _pb_read_varint(buf, i)
    return i, i + ln


def _pb_translated(buf: bytes, i: int, end: int) -> dict:
    translations: list[dict] = []

    def h_tr(buf, i, wt, out):
        i0, i1 = _pb_len(buf, i, wt)

        def h_text(buf, i, wt, o):
            a, b = _pb_len(buf, i, wt)
            o["text"] = buf[a:b].decode("utf-8", "replace")
            return b

        def h_lang(buf, i, wt, o):
            a, b = _pb_len(buf, i, wt)
            o["language"] = buf[a:b].decode("utf-8", "replace")
            return b

        translations.append(_pb_parse(buf, i0, i1, {1: h_text, 2: h_lang})[0])
        return i1

    _pb_parse(buf, i, end, {1: h_tr})
    return {"translation": translations}


def _pb_time_range(buf: bytes, i: int, end: int) -> dict:
    def h_start(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i)
        out["start"] = str(v)
        return i

    def h_end(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i)
        out["end"] = str(v)
        return i

    return _pb_parse(buf, i, end, {1: h_start, 2: h_end})[0]


def _pb_entity_selector(buf: bytes, i: int, end: int) -> dict:
    def h_agency(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["agency_id"] = buf[a:b].decode("utf-8", "replace")
        return b

    def h_route(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["route_id"] = buf[a:b].decode("utf-8", "replace")
        return b

    def h_rtype(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i)
        out["route_type"] = v
        return i

    def h_trip(buf, i, wt, out):
        return _pb_skip(buf, i, wt)

    def h_stop(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["stop_id"] = buf[a:b].decode("utf-8", "replace")
        return b

    return _pb_parse(
        buf, i, end, {1: h_agency, 2: h_route, 3: h_rtype, 4: h_trip, 5: h_stop}
    )[0]


def _pb_alert(buf: bytes, i: int, end: int) -> dict:
    out = {"active_period": [], "informed_entity": []}

    def h_period(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["active_period"].append(_pb_time_range(buf, a, b))
        return b

    def h_ie(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["informed_entity"].append(_pb_entity_selector(buf, a, b))
        return b

    def h_cause(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i)
        out["cause"] = _GTFS_CAUSE.get(v, str(v))
        return i

    def h_effect(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i)
        out["effect"] = _GTFS_EFFECT.get(v, str(v))
        return i

    def h_url(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["url"] = _pb_translated(buf, a, b)
        return b

    def h_header(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["header_text"] = _pb_translated(buf, a, b)
        return b

    def h_desc(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["description_text"] = _pb_translated(buf, a, b)
        return b

    return _pb_parse(
        buf,
        i,
        end,
        {
            1: h_period,
            5: h_ie,
            6: h_cause,
            7: h_effect,
            8: h_url,
            10: h_header,
            11: h_desc,
        },
        out=out,
    )[0]


def _pb_entity(buf: bytes, i: int, end: int) -> dict:
    def h_id(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["id"] = buf[a:b].decode("utf-8", "replace")
        return b

    def h_alert(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["alert"] = _pb_alert(buf, a, b)
        return b

    return _pb_parse(buf, i, end, {1: h_id, 5: h_alert})[0]


def _pb_header(buf: bytes, i: int, end: int) -> dict:
    def h_ver(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["gtfs_realtime_version"] = buf[a:b].decode("utf-8", "replace")
        return b

    def h_inc(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i)
        out["incrementality"] = v
        return i

    def h_ts(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i)
        out["timestamp"] = str(v)
        return i

    return _pb_parse(buf, i, end, {1: h_ver, 2: h_inc, 3: h_ts})[0]


def decode_feed_to_dict(raw: bytes) -> dict:
    """Decode GTFS-RT FeedMessage without gtfs-realtime-bindings (Pipeline-safe)."""
    out: dict = {"header": {}, "entity": []}

    def h_header(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["header"] = _pb_header(buf, a, b)
        return b

    def h_ent(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["entity"].append(_pb_entity(buf, a, b))
        return b

    result = _pb_parse(raw, 0, len(raw), {1: h_header, 2: h_ent}, out=out)[0]
    return result
