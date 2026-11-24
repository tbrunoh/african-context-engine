"""Rain this week: ECMWF ensemble forecasts through the Open-Meteo Ensemble API.

ECMWF publishes its IFS ensemble as open data under CC BY 4.0. Open-Meteo serves it as JSON with no key,
free for non-commercial use under 10,000 calls a day, and asks for attribution. ACE asks for one point per
area (the area's centre from the places snapshot), takes the 51 members' daily rainfall, and stores for
each day the share of members with at least 1 mm (the chance of a wet day), the median amount and the share
with at least 20 mm (the chance of heavy rain). Chances, not certainties, is the rule every answer follows.
"""
from __future__ import annotations

import statistics
from datetime import timedelta
from urllib.parse import urlencode

from ..countries import COUNTRIES
from ..snapshots import Snapshot, SnapshotStore, utcnow
from .base import ConnectorError, http_json, iso

API = "https://ensemble-api.open-meteo.com/v1/ensemble"
MODEL = "ecmwf_ifs025"
WET_MM = 1.0
HEAVY_MM = 20.0
BATCH = 40          # points per request
VALID_FOR = timedelta(hours=36)


def summarise(daily: dict) -> list[list]:
    """[[date, chance of >=1 mm, median mm, chance of >=20 mm], ...] from one location's daily members."""
    members = [k for k in daily if k.startswith("precipitation_sum_member")]
    if "precipitation_sum" in daily:
        members.append("precipitation_sum")  # the control run
    out = []
    for i, day in enumerate(daily["time"]):
        values = [daily[m][i] for m in members if daily[m][i] is not None]
        if not values:
            continue
        out.append([day, round(sum(v >= WET_MM for v in values) / len(values), 2),
                    round(statistics.median(values), 1), round(sum(v >= HEAVY_MM for v in values) / len(values), 2)])
    return out


class OpenMeteoEnsembleConnector:
    name = "open_meteo"
    dataset = "weather"
    licence = "CC BY 4.0"
    refresh = timedelta(hours=12)
    fallback = None
    countries = frozenset(COUNTRIES)

    def fetch(self, country: str, store: SnapshotStore) -> Snapshot:
        country = country.upper()
        places = store.get("places", country)
        if places is None or not places.records:
            raise ConnectorError(f"no places snapshot for {country}; run the boundaries connector first")
        areas = places.records
        records = []
        for start in range(0, len(areas), BATCH):
            chunk = areas[start:start + BATCH]
            query = urlencode({
                "latitude": ",".join(str(a["centroid"][0]) for a in chunk),
                "longitude": ",".join(str(a["centroid"][1]) for a in chunk),
                "daily": "precipitation_sum", "models": MODEL, "forecast_days": 7, "timezone": "auto"})
            data = http_json(f"{API}?{query}")
            data = data if isinstance(data, list) else [data]
            if len(data) != len(chunk):
                raise ConnectorError("Open-Meteo returned a different number of locations than requested")
            for area, loc in zip(chunk, data, strict=True):
                if "daily" not in loc:
                    raise ConnectorError(f"Open-Meteo error: {loc.get('reason', 'no daily data')}")
                records.append({"code": area["code"], "name": area["name"], "lat": area["centroid"][0],
                                "lon": area["centroid"][1], "timezone": loc.get("timezone"),
                                "days": summarise(loc["daily"])})
        now = utcnow()
        first = records[0]["days"][0][0] if records and records[0]["days"] else None
        return Snapshot(
            dataset="weather", country=country, source_id="open_meteo",
            source="ECMWF IFS ensemble forecast (open data), via Open-Meteo", source_url="https://open-meteo.com/",
            licence=self.licence, retrieved_at=iso(now), records=records, data_date=first,
            valid_until=iso(now + VALID_FOR),
            meta={"model": MODEL, "members": 51, "wet_mm": WET_MM, "heavy_mm": HEAVY_MM, "areas": len(records)})
