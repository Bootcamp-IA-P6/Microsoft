import json
import time

from .common import (
    EmtTokenSession,
    bronze_row,
    count_arrivals,
    fetch_arrives,
    load_emt_credentials,
    load_eventstream_connection_string,
    TokenExpiredError,
)
from .fabric import resolve_stop_ids as resolve_stop_ids_from_silver


def poll_one_stop(session, stop_id_str: str, max_retries: int):
    last_err = None
    for attempt in range(int(max_retries) + 1):
        try:
            token = session.ensure()
            payload, status = fetch_arrives(token, stop_id_str)
            if str(payload.get("code", "")) != "00":
                return None, (
                    f"stop {stop_id_str}: api_code={payload.get('code')} "
                    f"({payload.get('description')})"
                )
            ev = bronze_row("EMT_OPENAPI", "arrives", str(stop_id_str), status, payload)
            print(f"  stop {stop_id_str}: code=00 arrivals={count_arrivals(payload)}")
            return ev, None
        except TokenExpiredError as exc:
            last_err = exc
            print(f"  stop {stop_id_str}: token refresh ({exc})")
            session.ensure(force=True)
            time.sleep(0.5)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(1 + attempt)
    return None, f"stop {stop_id_str}: FAILED ({last_err})"


def push_events(connection_string: str, events: list[dict]) -> None:
    from azure.eventhub import EventData, EventHubProducerClient

    if not events:
        return
    producer = EventHubProducerClient.from_connection_string(connection_string)
    try:
        batch = producer.create_batch()
        for ev in events:
            data = EventData(json.dumps(ev, ensure_ascii=False))
            try:
                batch.add(data)
            except ValueError:
                producer.send_batch(batch)
                batch = producer.create_batch()
                batch.add(data)
        if len(batch) > 0:
            producer.send_batch(batch)
    finally:
        producer.close()


def run_eventstream_poller(
    spark,
    *,
    stop_ids: str,
    variable_library_name: str,
    poll_interval_sec: int,
    max_rounds: int,
    max_retries_per_stop: int,
    token_skew_sec: int,
    eventstream_connection_string: str,
) -> None:
    client_id, pass_key = load_emt_credentials(variable_library_name)
    conn_str = load_eventstream_connection_string(
        variable_library_name, eventstream_connection_string
    )
    parsed_stop_ids = resolve_stop_ids_from_silver(spark, stop_ids)
    session = EmtTokenSession(client_id, pass_key, token_skew_sec)

    est_daily = len(parsed_stop_ids) * 1440
    print(f"Stops/round={len(parsed_stop_ids)}  est calls/day≈{est_daily:,}/250000")
    print(f"max_rounds={max_rounds} poll_interval_sec={poll_interval_sec}")

    round_durations: list[float] = []
    for round_idx in range(1, int(max_rounds) + 1):
        t0 = time.time()
        print(f"\n=== Round {round_idx}/{max_rounds} ===")
        events, failures = [], []
        for sid in parsed_stop_ids:
            ev, err = poll_one_stop(session, sid, max_retries_per_stop)
            if ev:
                events.append(ev)
            if err:
                print(f"  {err}")
                failures.append(err)
        if events:
            push_events(conn_str, events)
            print(f"Pushed {len(events)} event(s) → Eventstream")
        else:
            print("No events pushed this round")
        elapsed = time.time() - t0
        round_durations.append(elapsed)
        print(f"Round done in {elapsed:.1f}s success={len(events)} fail={len(failures)}")
        if round_idx >= int(max_rounds):
            break
        sleep_for = float(poll_interval_sec) - elapsed
        if sleep_for > 0:
            print(f"Sleeping {sleep_for:.1f}s")
            time.sleep(sleep_for)
        else:
            print(f"WARNING: round {elapsed:.1f}s > poll_interval_sec={poll_interval_sec}")

    if round_durations:
        avg_s = sum(round_durations) / len(round_durations)
        max_s = max(round_durations)
        suggested = max(60.0, max_s + 15.0)
        print(
            f"avg={avg_s:.1f}s max={max_s:.1f}s → suggested poll_interval_sec≈{suggested:.0f}"
        )
        print("Next: nb_transform_bronze_silver_gold")

