"""Dated snapshots of public data, and the licence register that covers them.

V2 decision services never call the network. Connectors fetch public data on
a schedule and write snapshots; services read them. Every snapshot carries its
source, licence, retrieval time, the date its data describes, how long it
stays valid and a checksum of its records, so an answer can always say where
a number came from and how fresh it is.

Layout:  snapshots/<dataset>/<COUNTRY>.json   plus  snapshots/register.yaml
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .licence import LicenceEntry, load_register

DATASETS = ("places", "weather", "warnings", "facilities", "prices")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def checksum(records: Any) -> str:
    blob = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


@dataclass
class Snapshot:
    dataset: str
    country: str
    source_id: str              # key in the licence register
    source: str                 # human readable source line, shown in citations
    source_url: str
    licence: str                # licence name, as in the register
    retrieved_at: str           # ISO 8601, UTC
    records: Any
    data_date: str | None = None    # the date the data describes, for example the forecast run or price month
    valid_until: str | None = None  # after this, services must not serve the data as current
    notes: str = ""
    sha256: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.sha256:
            self.sha256 = checksum(self.records)

    @property
    def retrieved(self) -> datetime:
        return parse_time(self.retrieved_at) or utcnow()

    def is_valid(self, now: datetime | None = None) -> bool:
        until = parse_time(self.valid_until)
        return until is None or (now or utcnow()) <= until

    def verify(self) -> bool:
        return checksum(self.records) == self.sha256

    def to_dict(self) -> dict[str, Any]:
        return {"dataset": self.dataset, "country": self.country, "source_id": self.source_id,
                "source": self.source, "source_url": self.source_url, "licence": self.licence, "retrieved_at": self.retrieved_at,
                "data_date": self.data_date, "valid_until": self.valid_until, "notes": self.notes,
                "meta": self.meta, "sha256": self.sha256, "records": self.records}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Snapshot:
        return cls(dataset=d["dataset"], country=d["country"], source_id=d["source_id"], source=d["source"],
                   source_url=d["source_url"], licence=d.get("licence", ""), retrieved_at=d["retrieved_at"], records=d["records"],
                   data_date=d.get("data_date"), valid_until=d.get("valid_until"), notes=d.get("notes", ""),
                   sha256=d.get("sha256", ""), meta=d.get("meta", {}))

    @property
    def odbl(self) -> bool:
        return "open database license" in self.licence.lower() or self.licence.upper().startswith("ODBL")

    def write(self, root: str | Path) -> Path:
        """Write to <root>/<dataset>/<COUNTRY>.json. ODbL data goes in its own store, <root>/odbl/, as the
        licence register requires, so share alike terms never spread to the rest of the snapshots."""
        base = Path(root) / "odbl" if self.odbl else Path(root)
        other = (Path(root) if self.odbl else Path(root) / "odbl") / self.dataset / f"{self.country}.json"
        if other.exists():
            other.unlink()  # the source changed licence; keep exactly one copy
        path = base / self.dataset / f"{self.country}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":")) + "\n",
                        encoding="utf-8")
        return path


class SnapshotStore:
    """Read only access to every snapshot under a root folder."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root else None
        self._cache: dict[tuple[str, str], Snapshot | None] = {}
        self.register: dict[str, LicenceEntry] = {}
        if self.root and (self.root / "register.yaml").exists():
            self.register = load_register(self.root / "register.yaml")

    def get(self, dataset: str, country: str) -> Snapshot | None:
        key = (dataset, country.upper())
        if key not in self._cache:
            self._cache[key] = self._load(*key)
        return self._cache[key]

    def put(self, snapshot: Snapshot) -> None:
        """Hold a snapshot in memory, for tests and for embedding ACE without files."""
        self._cache[(snapshot.dataset, snapshot.country.upper())] = snapshot

    def _load(self, dataset: str, country: str) -> Snapshot | None:
        if not self.root:
            return None
        path = self.root / dataset / f"{country}.json"
        if not path.exists():
            path = self.root / "odbl" / dataset / f"{country}.json"
        if not path.exists():
            return None
        return Snapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def available(self) -> list[tuple[str, str]]:
        found = {k for k, v in self._cache.items() if v is not None}
        if self.root and self.root.exists():
            for path in [*self.root.glob("*/*.json"), *self.root.glob("odbl/*/*.json")]:
                found.add((path.parent.name, path.stem.upper()))
        return sorted(found)


def default_root() -> Path | None:
    """The repository's snapshots folder, or the copy shipped inside the installed package."""
    here = Path(__file__).resolve()
    for candidate in (Path.cwd() / "snapshots", here.parents[3] / "snapshots", here.parents[1] / "data" / "snapshots"):
        if (candidate / "register.yaml").exists():
            return candidate
    return None
