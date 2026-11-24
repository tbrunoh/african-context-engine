"""The connector contract. Connectors are the only code in ACE that touches the network.

A connector fetches one public source for one country and returns a dated,
checksummed Snapshot. It runs on a schedule (see .github/workflows/refresh.yml),
never while a person is waiting. When a source is down, the last good snapshot
stays in place and services judge its freshness themselves.
"""
from __future__ import annotations

import json
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
                time.sleep(1.5 * (attempt + 1))
    raise ConnectorError(f"could not fetch {url}: {last}")


def http_json(url: str, timeout: float = 60.0) -> Any:
    try:
        return json.loads(http_get(url, timeout=timeout, accept="application/json"))
    except json.JSONDecodeError as exc:
        raise ConnectorError(f"{url} did not return JSON") from exc
