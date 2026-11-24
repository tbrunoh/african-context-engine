"""Connectors: the only code in ACE that touches the network. Each writes dated snapshots for services to read."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..countries import COUNTRIES
from ..snapshots import SnapshotStore
from .base import Connector, ConnectorError, ConnectorHealth, http_get, http_json
from .boundaries import BoundariesConnector
from .cap import CapConnector
from .hdx_prices import WfpPricesConnector
from .health_facilities import HealthFacilitiesConnector
from .open_meteo import OpenMeteoEnsembleConnector

# Order matters: weather reads the places snapshot that boundaries writes.
CONNECTORS: dict[str, Connector] = {c.name: c for c in (
    BoundariesConnector(), OpenMeteoEnsembleConnector(), CapConnector(), WfpPricesConnector(),
    HealthFacilitiesConnector())}


@dataclass
class RefreshReport:
    written: list[tuple[str, str]] = field(default_factory=list)
    failed: list[ConnectorHealth] = field(default_factory=list)
    skipped: list[ConnectorHealth] = field(default_factory=list)


def refresh(root: str | Path, names: list[str] | None = None, countries: list[str] | None = None) -> RefreshReport:
    """Run connectors and write snapshots. A failure leaves the last good snapshot in place."""
    report = RefreshReport()
    root = Path(root)
    for name in names or list(CONNECTORS):
        connector = CONNECTORS[name]
        for country in [c.upper() for c in (countries or COUNTRIES)]:
            if country not in connector.countries:
                report.skipped.append(ConnectorHealth(name, country, False, "source does not cover this country"))
                continue
            store = SnapshotStore(root)
            try:
                snap = connector.fetch(country, store)
            except (ConnectorError, KeyError, ValueError) as exc:
                report.failed.append(ConnectorHealth(name, country, False, str(exc)[:300]))
                continue
            snap.write(root)
            report.written.append((name, country))
    return report


__all__ = ["CONNECTORS", "Connector", "ConnectorError", "ConnectorHealth", "RefreshReport", "http_get", "http_json",
           "refresh"]
