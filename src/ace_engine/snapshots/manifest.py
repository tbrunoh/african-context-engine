"""Snapshot sets that change while the service runs: publish a checked set, then swap it in without a restart.

A deployment keeps snapshot sets in one folder, which on Google Cloud is a Cloud Storage bucket mounted into Cloud
Run. Each set is a dated folder under releases/, and manifest.json names the one in use:

    manifest.json             {"set": "releases/20261127T090000Z", "published_at": "...", "datasets": {...}}
    releases/<time>/...       the same layout as the repository's snapshots folder

publish() copies the set in use, refreshes the chosen sources into the copy, checks every snapshot, and writes the
manifest only if the checks pass and no other run changed it in the meantime. It deletes sets older than seven days,
except the one in use. SnapshotWatcher reads the manifest every few minutes, loads a new set off the request path,
and swaps it in; on any failure it keeps the set it has.
"""
from __future__ import annotations

import json
import logging
import shutil
import threading
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .store import SnapshotStore, default_root, parse_time

log = logging.getLogger("ace.snapshots")
MANIFEST = "manifest.json"
KEEP = timedelta(days=7)
STAMP = "%Y%m%dT%H%M%SZ"
LIVE = ("weather", "warnings")  # datasets that carry a valid_until time


def read_manifest(base: str | Path) -> dict[str, Any] | None:
    path = Path(base) / MANIFEST
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) and data.get("set") else None


def check_set(root: str | Path) -> list[str]:
    """Every problem that should stop a set being published: a missing licence entry, a checksum that does not
    match, no data date, or a live dataset with no valid until time."""
    store = SnapshotStore(root)
    problems: list[str] = []
    if not store.register:
        problems.append("no licence register (register.yaml)")
    for dataset, country in store.available():
        name = f"{dataset}/{country}"
        try:
            snap = store.get(dataset, country)
        except (ValueError, KeyError, TypeError) as exc:
            problems.append(f"{name}: unreadable ({exc})")
            continue
        if snap is None:
            continue
        if snap.source_id not in store.register:
            problems.append(f"{name}: source {snap.source_id!r} is not in the licence register")
        if not snap.verify():
            problems.append(f"{name}: checksum does not match its records")
        if not snap.data_date:
            problems.append(f"{name}: no data date")
        if dataset in LIVE and not snap.valid_until:
            problems.append(f"{name}: no valid until time")
    return problems


def publish(base: str | Path, refresh_into: Callable[[Path], Any], now: datetime | None = None) -> dict[str, Any]:
    """Build, check and publish a new set. refresh_into(folder) runs the connectors into the copied set.

    Returns {"published": bool, "set": ..., "problems": [...], "refresh": <what refresh_into returned>}."""
    base = Path(base)
    now = now or datetime.now(timezone.utc)
    before = read_manifest(base)
    source = base / before["set"] if before else default_root()
    if source is None or not source.exists():
        raise FileNotFoundError("no snapshot set to start from: no manifest and no bundled snapshots")
    name = f"releases/{now.strftime(STAMP)}"
    target = base / name
    shutil.copytree(source, target)
    outcome = refresh_into(target)
    problems = check_set(target)
    if problems:
        log.error("snapshot set %s failed its checks and was not published: %s", name, problems)
        return {"published": False, "set": name, "problems": problems, "refresh": outcome}
    if read_manifest(base) != before:  # another run published while this one worked: leave its set in place
        return {"published": False, "set": name, "problems": ["the manifest changed during the run"],
                "refresh": outcome}
    store = SnapshotStore(target)
    manifest = {"set": name, "published_at": now.isoformat(),
                "datasets": {f"{d}/{c}": (store.get(d, c).retrieved_at if store.get(d, c) else None)
                             for d, c in store.available()}}
    tmp = base / f".{MANIFEST}.{now.strftime(STAMP)}"
    tmp.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    tmp.replace(base / MANIFEST)
    prune(base, keep=name, now=now)
    return {"published": True, "set": name, "problems": [], "refresh": outcome}


def prune(base: str | Path, keep: str, now: datetime | None = None) -> list[str]:
    """Delete sets older than seven days, never the one in use."""
    now = now or datetime.now(timezone.utc)
    removed = []
    for folder in sorted((Path(base) / "releases").glob("*")):
        rel = f"releases/{folder.name}"
        try:
            made = datetime.strptime(folder.name, STAMP).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if rel != keep and now - made > KEEP:
            shutil.rmtree(folder, ignore_errors=True)
            removed.append(rel)
    return removed


def preload(store: SnapshotStore, datasets: Iterable[tuple[str, str]] | None = None) -> int:
    """Read every snapshot of a set into memory, so swapping it in never makes a request wait on disk."""
    n = 0
    for dataset, country in datasets or store.available():
        n += store.get(dataset, country) is not None
    return n


class SnapshotWatcher:
    """Swaps the engine's V2 services to the set the manifest names, checking every interval seconds."""

    def __init__(self, engine: Any, base: str | Path, interval: float = 300.0,
                 on_swap: Callable[[Any], None] | None = None) -> None:
        self.engine = engine
        self.base = Path(base)
        self.interval = interval
        self.on_swap = on_swap
        self.current: str | None = None
        self.last_error: str | None = None
        self.checked_at: datetime | None = None
        self._stop = threading.Event()

    def check_once(self) -> bool:
        """Load and swap in the manifest's set if it is new. Returns True when the services changed."""
        from ..services import ServiceHub

        self.checked_at = datetime.now(timezone.utc)
        try:
            manifest = read_manifest(self.base)
            if not manifest or manifest["set"] == self.current:
                return False
            root = self.base / manifest["set"]
            store = SnapshotStore(root)
            if not store.register or not preload(store):
                raise FileNotFoundError(f"{root} holds no snapshots")
            hub = ServiceHub(store)
            hub.clock = self.engine.services.clock if self.engine.services is not None else hub.clock
            if self.on_swap is not None:
                self.on_swap(hub)  # for example, build the facility index before the hub takes traffic
            self.engine.use_services(hub)
            self.current = manifest["set"]
            self.last_error = None
            log.info("snapshot set %s is now in use", self.current)
            return True
        except Exception as exc:  # noqa: BLE001  keep the last good set on any failure
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.warning("kept snapshot set %s: %s", self.current or "bundled", self.last_error)
            return False

    def start(self) -> threading.Thread:
        def loop() -> None:
            while not self._stop.is_set():
                self.check_once()
                self._stop.wait(self.interval)

        thread = threading.Thread(target=loop, name="ace-snapshot-watcher", daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop.set()

    def status(self) -> dict[str, Any]:
        return {"set": self.current or "bundled", "checked_at": self.checked_at.isoformat() if self.checked_at else None,
                "error": self.last_error}


def freshness(store: SnapshotStore, now: datetime | None = None) -> list[dict[str, Any]]:
    """Each snapshot's data date, retrieval time and whether it is still valid, for the status page."""
    now = now or datetime.now(timezone.utc)
    out = []
    for dataset, country in store.available():
        snap = store.get(dataset, country)
        if snap is None:
            continue
        valid_until = parse_time(snap.valid_until) if snap.valid_until else None
        out.append({"dataset": dataset, "country": country, "data_date": snap.data_date,
                    "retrieved_at": snap.retrieved_at, "valid_until": snap.valid_until,
                    "valid": snap.is_valid(now), "expired": bool(valid_until and valid_until <= now)})
    return out
