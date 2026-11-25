"""National health facility registries: Malawi and Zambia, held until each ministry confirms reuse.

Both ministries publish their registries openly, with positions and phone numbers the 2019 list lacks:
* Malawi Health Facility Registry, https://zipatala.health.gov.mw/api: facilities, geolocations and contact people.
* Zambia Health Facility Registry, https://zhfr.moh.gov.zm/facilities/export.csv: one CSV with every field.

Neither states a licence. ACE's licence register marks the source ``cleared: false``, and the refresh skips it
with a held status until the ministry's written permission is recorded there. The connector is complete, so a
cleared source starts serving on the next refresh: the facility service prefers a registry snapshot to the
2019 list, and adds the facility's phone number when the registry has a plausible one.
"""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import timedelta

from ..countries import COUNTRIES
from ..snapshots import Snapshot, SnapshotStore
from .base import ConnectorError, http_get, iso
from .health_facilities import check_positions, clean_text

MW_API = "https://zipatala.health.gov.mw/api"
ZM_CSV = "https://zhfr.moh.gov.zm/facilities/export.csv"


def plausible_phone(value: str | None) -> str | None:
    """The digits of a phone number, or None for a placeholder such as 1234567890 or 0999999999."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) < 9 or len(digits) > 13 or len(set(digits)) <= 2 or "1234567" in digits or "0000000" in digits:
        return None
    return digits


def _float(value) -> float | None:
    try:
        return round(float(re.sub(r"\s", "", str(value))), 4)
    except (TypeError, ValueError):
        return None


def malawi_records(facilities: list[dict], geo: list[dict], contacts: list[dict]) -> list[list]:
    where = {g["facility_id"]: (_float(g.get("latitude")), _float(g.get("longitude"))) for g in geo}
    phone = {c["facility_id"]: plausible_phone(c.get("contact_person_phone")) for c in contacts}
    out = []
    for f in facilities:
        lat, lon = where.get(f["id"], (None, None))
        if lat is None or lon is None or f.get("archived_date") or f.get("facility_name") == "Facility Name":
            continue
        out.append([clean_text(f["facility_name"]), str(f.get("facility_type_id", "")), str(f.get("facility_owner_id", "")),
                    str(f.get("district_id", "")), lat, lon, phone.get(f["id"])])
    return sorted(out, key=lambda r: (r[3], r[0]))


def zambia_records(rows: list[dict]) -> list[list]:
    out = []
    for r in rows:
        lat, lon = _float(r.get("latitude")), _float(r.get("longitude"))
        if lat is None or lon is None or (r.get("operation_status") or "operational").lower() != "operational":
            continue
        out.append([clean_text(r["name"]), clean_text(r.get("facility_type", "")), clean_text(r.get("ownership", "")),
                    clean_text(r.get("province", "")), lat, lon, plausible_phone(r.get("phone"))])
    return sorted(out, key=lambda r: (r[3], r[0]))


class NationalRegistryConnector:
    name = "national_facility_registry"
    dataset = "facilities_registry"
    licence = "not stated; held until the ministry confirms reuse"
    refresh = timedelta(days=30)
    fallback = "public_health_facilities"
    countries = frozenset({"MW", "ZM"})

    def fetch(self, country: str, store: SnapshotStore | None = None) -> Snapshot:
        country = country.upper()
        if country == "MW":
            records = malawi_records(json.loads(http_get(f"{MW_API}/facilities")),
                                     json.loads(http_get(f"{MW_API}/geolocations")),
                                     json.loads(http_get(f"{MW_API}/contactPeople")))
            url, source = "https://zipatala.health.gov.mw/", "Malawi Health Facility Registry, Ministry of Health"
        elif country == "ZM":
            text = http_get(ZM_CSV, timeout=120).decode("utf-8-sig", "ignore")
            records = zambia_records(list(csv.DictReader(io.StringIO(text))))
            url, source = "https://zhfr.moh.gov.zm/", "Zambia Health Facility Registry, Ministry of Health"
        else:
            raise ConnectorError(f"no national registry for {COUNTRIES[country].name}")
        records, dropped = check_positions(records, country, store)
        return Snapshot(dataset=self.dataset, country=country, source_id=self.name, source=source, source_url=url,
                        licence=self.licence, retrieved_at=iso(), records=records, data_date=iso()[:10],
                        meta={"facilities": len(records), "dropped_positions": dropped,
                              "fields": ["name", "type", "ownership", "admin1", "lat", "lon", "phone"]})
