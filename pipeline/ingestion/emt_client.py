"""EMT OpenAPI JSON client (S1)."""
from __future__ import annotations

import re
import time

from pipeline.common.http_retry import is_transient_http_error
from pipeline.config.constants import (
    ARRIVES_BODY,
    AUTH_API_CODES,
    BASE_URL,
    HTTP_HEADERS_JSON,
)


class TokenExpiredError(RuntimeError):
    pass


def http_json(
    method: str,
    path: str,
    headers=None,
    body=None,
    timeout: int = 30,
    *,
    attempts: int = 5,
) -> tuple[dict, int]:
    """EMT OpenAPI JSON call with retries — Fabric urllib often hits SSL EOF."""
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "requests is required — run once: %pip install requests"
        ) from exc

    url = f"{BASE_URL}{path}"
    hdrs = {**HTTP_HEADERS_JSON, **(headers or {})}
    last_err: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            resp = requests.request(
                method=method.upper(),
                url=url,
                headers=hdrs,
                data=body,
                timeout=timeout,
                allow_redirects=True,
            )
            raw = resp.text
            if resp.status_code == 401:
                raise TokenExpiredError(f"HTTP 401 on {path}: {raw[:200]}")
            if resp.status_code in {408, 425, 429, 500, 502, 503, 504}:
                raise RuntimeError(f"HTTP {resp.status_code} on {path}: {raw[:300]}")
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code} on {path}: {raw[:300]}")
            try:
                payload = resp.json()
            except ValueError as exc:
                raise RuntimeError(f"Non-JSON on {path}: {raw[:300]}") from exc
            if not isinstance(payload, dict):
                raise RuntimeError(f"Unexpected JSON type on {path}: {type(payload)}")
            return payload, int(resp.status_code)
        except TokenExpiredError:
            raise
        except RuntimeError as exc:
            last_err = exc
            m = re.match(r"HTTP (\d+)", str(exc))
            if m:
                code = int(m.group(1))
                if code >= 400 and code not in {408, 425, 429, 500, 502, 503, 504}:
                    raise
            if attempt < attempts:
                sleep_s = min(2**attempt, 20)
                print(
                    f"HTTP {method.upper()} {path} failed "
                    f"(attempt {attempt}/{attempts}): {exc!r}; retry in {sleep_s}s"
                )
                time.sleep(sleep_s)
                continue
            break
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < attempts and is_transient_http_error(exc):
                sleep_s = min(2**attempt, 20)
                print(
                    f"HTTP {method.upper()} {path} failed "
                    f"(attempt {attempt}/{attempts}): {exc!r}; retry in {sleep_s}s"
                )
                time.sleep(sleep_s)
                continue
            if attempt < attempts:
                sleep_s = min(2**attempt, 20)
                print(
                    f"HTTP {method.upper()} {path} failed "
                    f"(attempt {attempt}/{attempts}): {exc!r}; retry in {sleep_s}s"
                )
                time.sleep(sleep_s)
                continue
            break

    raise RuntimeError(
        f"HTTP {method.upper()} {path} failed after {attempts} attempts: {last_err}"
    ) from last_err


def login_with_ttl(client_id: str, pass_key: str) -> tuple[str, float]:
    last_err = None
    for attempt in range(3):
        try:
            payload, _ = http_json(
                "GET",
                "/v1/mobilitylabs/user/login/",
                headers={"X-ClientId": client_id, "passKey": pass_key},
            )
            if str(payload.get("code", "")) not in ("00", "01"):
                raise RuntimeError(
                    f"login code={payload.get('code')}: {payload.get('description')}"
                )
            data0 = payload["data"][0]
            ttl = float(data0.get("tokenSecExpiration") or 3000)
            return data0["accessToken"], time.time() + max(60.0, ttl)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"login failed: {last_err}")


def login_token(client_id: str, pass_key: str) -> str:
    payload, _ = http_json(
        "GET",
        "/v1/mobilitylabs/user/login/",
        headers={"X-ClientId": client_id, "passKey": pass_key},
        timeout=60,
    )
    if str(payload.get("code", "")) not in ("00", "01"):
        raise RuntimeError(f"login failed: {payload.get('description')}")
    return payload["data"][0]["accessToken"]


class EmtTokenSession:
    def __init__(self, client_id: str, pass_key: str, skew_sec: float):
        self.client_id = client_id
        self.pass_key = pass_key
        self.skew_sec = float(skew_sec)
        self.token = None
        self.expires_at = 0.0

    def ensure(self, force: bool = False) -> str:
        if force or not self.token or time.time() >= (self.expires_at - self.skew_sec):
            self.token, self.expires_at = login_with_ttl(self.client_id, self.pass_key)
            print(
                f"EMT login ok — TTL≈{max(0.0, self.expires_at - time.time()):.0f}s"
            )
        return self.token


def fetch_arrives(token: str, stop_id: str) -> tuple[dict, int]:
    payload, status = http_json(
        "POST",
        f"/v2/transport/busemtmad/stops/{stop_id}/arrives/",
        headers={"accessToken": token, "Content-Type": "application/json"},
        body=ARRIVES_BODY,
    )
    if str(payload.get("code", "")) in AUTH_API_CODES:
        raise TokenExpiredError(
            f"arrives api_code={payload.get('code')} stop={stop_id}"
        )
    return payload, status
