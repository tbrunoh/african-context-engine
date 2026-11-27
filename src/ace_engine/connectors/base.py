"""The connector contract. Connectors are the only code in ACE that touches the network.

A connector fetches one public source for one country and returns a dated,
checksummed Snapshot. It runs on a schedule (see .github/workflows/refresh.yml),
never while a person is waiting. When a source is down, the last good snapshot
stays in place and services judge its freshness themselves.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Protocol

from ..snapshots import Snapshot, SnapshotStore, utcnow

USER_AGENT = "ACE/2.0 (African Context Engine; +https://github.com/tbrunoh/african-context-engine)"


class ConnectorError(RuntimeError):
    """Raised when a source cannot be fetched or parsed. The refresh run reports it and moves on."""


@dataclass(frozen=True)
class ConnectorHealth:
    name: str
    country: str
    ok: bool
    detail: str = ""


class Connector(Protocol):
    name: str                   # key in the licence register, for example open_meteo
    dataset: str                # snapshot folder it writes, for example weather
    licence: str
    refresh: timedelta          # how often the scheduled refresh runs it
    fallback: str | None        # what services fall back on when this source is down
    countries: frozenset[str]   # countries this source can serve

    def fetch(self, country: str, store: SnapshotStore) -> Snapshot: ...


def iso(dt=None) -> str:
    return (dt or utcnow()).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# Waiting out rate limits is capped for the whole run, so a burst of HTTP 429 on a source fetched point by point
# cannot stall a scheduled refresh for hours: once the budget is spent, a rate limited URL fails at once and the
# last good snapshot stays in place.
RATE_LIMIT_BUDGET = 600.0
_rate_waited = 0.0
_rate_lock = threading.Lock()


def reset_rate_limit_budget() -> None:
    """Start a new run's rate limit budget. refresh() calls it, so a long running scheduler never runs out."""
    global _rate_waited
    with _rate_lock:
        _rate_waited = 0.0


def http_get(url: str, timeout: float = 60.0, retries: int = 2, accept: str = "*/*") -> bytes:
    """GET with a clear user agent, a timeout and a short retry. Raises ConnectorError on failure."""
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310  fixed, registered hosts
                return resp.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
            if attempt < retries:
                # A rate limit (HTTP 429) clears after the provider's window, often a minute; a short pause would
                # only spend the retry. Other errors get a short pause.
                global _rate_waited
                limited = isinstance(exc, urllib.error.HTTPError) and exc.code == 429
                wait = _retry_after(exc) if limited else 1.5 * (attempt + 1)
                if limited:
                    with _rate_lock:
                        if _rate_waited + wait > RATE_LIMIT_BUDGET:
                            break
                        _rate_waited += wait
                time.sleep(wait)
    raise ConnectorError(f"could not fetch {url}: {last}")


def _retry_after(exc: urllib.error.HTTPError) -> float:
    """Seconds to wait after HTTP 429: the Retry-After header when it gives seconds, else a minute, at most two."""
    value = (exc.headers or {}).get("Retry-After", "") if exc.headers is not None else ""
    return min(float(value), 120.0) if str(value).strip().isdigit() else 61.0


def http_json(url: str, timeout: float = 60.0) -> Any:
    try:
        return json.loads(http_get(url, timeout=timeout, accept="application/json"))
    except json.JSONDecodeError as exc:
        raise ConnectorError(f"{url} did not return JSON") from exc
