"""HTTP transient error detection."""
from __future__ import annotations


def is_transient_http_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if "unexpected_eof" in msg or "ssl" in msg or "connection" in msg or "timed out" in msg:
        return True
    try:
        import requests

        return isinstance(
            exc,
            (
                requests.exceptions.SSLError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError,
            ),
        )
    except ImportError:
        return False
