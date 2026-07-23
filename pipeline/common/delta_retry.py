"""Delta concurrent write retries."""
from __future__ import annotations

import time


def delta_sql_retry(spark, sql: str, *, label: str, attempts: int = 6) -> None:
    """Retry Delta MERGE/DELETE on ConcurrentAppendException (arrives+alerts share gold)."""
    last: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            spark.sql(sql)
            if attempt > 1:
                print(f"{label}: succeeded on attempt {attempt}/{attempts}")
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            msg = str(exc)
            name = type(exc).__name__
            concurrent = (
                "ConcurrentAppendException" in name
                or "ConcurrentAppendException" in msg
                or "DELTA_CONCURRENT_APPEND" in msg
                or "ConcurrentTransactionException" in msg
            )
            if not concurrent or attempt >= attempts:
                raise
            sleep_s = min(2**attempt, 30)
            print(
                f"{label}: concurrent Delta write "
                f"(attempt {attempt}/{attempts}); retry in {sleep_s}s"
            )
            time.sleep(sleep_s)
    raise RuntimeError(f"{label}: exhausted retries") from last
