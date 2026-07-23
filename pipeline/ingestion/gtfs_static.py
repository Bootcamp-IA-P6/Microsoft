"""GTFS static zip download / resolve / haversine."""
from __future__ import annotations

import math
import shutil
import ssl
import time
import urllib.request
from pathlib import Path

GTFS_DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; emt-pipeline/0.1; "
        "+https://github.com/Bootcamp-IA-P6/Microsoft)"
    ),
    "Accept": "application/zip,application/octet-stream,*/*",
    "Connection": "close",
}


def download_gtfs_zip(url: str, dest: Path, *, attempts: int = 10) -> None:
    """Download GTFS zip with retries — datos.emtmadrid.es is often very slow from Fabric."""
    url = str(url).strip()
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    last_err: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            if tmp.exists():
                tmp.unlink()
            print(f"Downloading GTFS (attempt {attempt}/{attempts}) from {url} ...")
            _download_via_requests(url, tmp)
            if tmp.stat().st_size < 1024:
                raise RuntimeError(f"Downloaded file too small ({tmp.stat().st_size} bytes)")
            tmp.replace(dest)
            print(f"GTFS saved → {dest} ({dest.stat().st_size} bytes)")
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"GTFS download failed (attempt {attempt}/{attempts}): {exc!r}")
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            if attempt < attempts:
                time.sleep(min(2 ** attempt, 120))

    # Last resort: urllib with explicit TLS 1.2+ context (some runtimes differ)
    try:
        print("GTFS download: falling back to urllib + SSL context ...")
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers=GTFS_DOWNLOAD_HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=1800) as resp:
            with open(tmp, "wb") as out:
                shutil.copyfileobj(resp, out)
        if tmp.stat().st_size < 1024:
            raise RuntimeError(f"Downloaded file too small ({tmp.stat().st_size} bytes)")
        tmp.replace(dest)
        print(f"GTFS saved via urllib → {dest} ({dest.stat().st_size} bytes)")
        return
    except Exception as exc:  # noqa: BLE001
        last_err = exc
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass

    raise RuntimeError(
        f"Failed to download GTFS after {attempts} attempts (+ urllib fallback): {last_err}"
    ) from last_err


def _download_via_requests(url: str, tmp: Path) -> None:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "requests is required for GTFS download; run once: %pip install requests"
        ) from exc

    with requests.Session() as session:
        session.headers.update(GTFS_DOWNLOAD_HEADERS)
        # datos.emtmadrid.es: slow connect + slow body from Fabric egress
        with session.get(url, stream=True, timeout=(600, 1800), allow_redirects=True) as resp:
            resp.raise_for_status()
            with open(tmp, "wb") as out:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        out.write(chunk)


def resolve_zip_path(preferred: str) -> Path:
    p = Path(preferred)
    if p.is_file():
        return p
    parent = (
        p.parent
        if p.parent.as_posix().endswith("gtfs")
        else Path("/lakehouse/default/Files/gtfs")
    )
    if parent.is_dir():
        for cand in sorted(parent.glob("*.zip")):
            print(f"Using zip found: {cand}")
            return cand
    raise FileNotFoundError(f"GTFS zip not found at {preferred}. Upload to Lakehouse Files/gtfs/.")


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
