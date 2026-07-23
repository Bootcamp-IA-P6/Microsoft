"""Simple wall-clock laps for Phase 1 timing logs."""
from __future__ import annotations

import time


def phase1_timer():
    t0 = time.perf_counter()

    def lap(label: str) -> None:
        print(f"[phase1 timing] {label}: {time.perf_counter() - t0:.2f}s since start")

    return lap
