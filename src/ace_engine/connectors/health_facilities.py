"""Nearest health facility: the public health facility database for sub-Saharan Africa.

Maina J, Ouma PO, Macharia PM et al. (2019), A spatial database of health facilities managed by the public
health sector in sub Saharan Africa, Scientific Data 6: 134, assembled by the KEMRI-Wellcome Trust Research
Programme from national master facility lists. It covers 98,745 public facilities in 50 countries, every
covered country included, and is published on HDX under CC BY 4.0. It lists name, type, ownership, first level
area and coordinates. It does not list phone numbers, opening hours or services, so ACE never claims them:
it names the nearest facilities, their type and distance, and gives the country's verified emergency number.
Private facilities and facilities opened after 2019 are not in it; the answer says the list dates from 2019.
"""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import timedelta

from ..countries import COUNTRIES
from ..snapshots import Snapshot, SnapshotStore
from .base import ConnectorError, http_get, http_json, iso

HDX_SLUG = "health-facilities-in-sub-saharan-africa"
HDX_API = "https://data.humdata.org/api/3/action/package_show?id="
# country -> the names the database uses for it. Zanzibar is listed apart from mainland Tanzania.
NAMES: dict[str, tuple[str, ...]] = {
    "KE": ("Kenya",), "TZ": ("Tanzania", "Zanzibar"), "UG": ("Uganda",), "RW": ("Rwanda",), "ZA": ("South Africa",),
    "BW": ("Botswana",), "NA": ("Namibia",), "ZW": ("Zimbabwe",), "NG": ("Nigeria",), "GH": ("Ghana",),
    "SN": ("Senegal",), "CI": ("Cote d'Ivoire",), "TG": ("Togo",), "CD": ("Democratic Republic of the Congo",),
    "MW": ("Malawi",), "BI": ("Burundi",), "CM": ("Cameroon",), "BJ": ("Benin",), "ZM": ("Zambia",), "TD": ("Chad",),
    "GN": ("Guinea",), "BF": ("Burkina Faso",), "SS": ("South Sudan",), "ET": ("Ethiopia",), "MZ": ("Mozambique",),
    "GW": ("Guinea Bissau",), "AO": ("Angola",), "SO": ("Somalia",), "SD": ("Sudan",)}
# North Africa is outside the database, which covers sub-Saharan Africa only; the facility service names the gap.
MAX_OUTSIDE_KM = 25.0  # a facility further than this outside its country's areas has a wrong position
_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_COL = re.compile(r"[A-Z]+")


def read_xlsx(data: bytes) -> list[list[str]]:
    """Rows of the first worksheet of an .xlsx file, using only the standard library."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", _NS):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{_NS['m']}}}t")))
        sheet = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))[0]
        rows = []
        for row in ET.fromstring(z.read(sheet)).iter(f"{{{_NS['m']}}}row"):
            cells: dict[int, str] = {}
            for c in row.findall("m:c", _NS):
                col = 0
                for ch in _COL.match(c.get("r", "A")).group(0):
                    col = col * 26 + (ord(ch) - 64)
                v = c.find("m:v", _NS)
                if c.get("t") == "inlineStr":
                    t = c.find("m:is/m:t", _NS)
                    value = t.text if t is not None else ""
                elif v is None:
                    value = ""
                elif c.get("t") == "s":
                    value = shared[int(v.text)]
                else:
                    value = v.text or ""
                cells[col - 1] = value
            if cells:
                rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
        return rows


MOJIBAKE = re.compile("[\u251c\u252c\u2502\u2557\u255d\u255a\u2554\u2550\u2551\u0393\u2310]")


def clean_text(value: str) -> str:
    """Repair the source's two artefacts. Accented letters were saved as UTF-8 read in code page 437, so
    Sant\u00e9 reads Sant\u251c\u2310; and title casing turned St. Mary's into St. Mary'S."""
    value = " ".join(value.split())
    if MOJIBAKE.search(value):
        try:
            value = value.encode("cp437").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return re.sub(r"(?<=[a-z])'S\b", "'s", value)


def facility_records(rows: list[list[str]], country_name: str | tuple[str, ...]) -> list[list]:
    """[name, type, ownership, admin1, lat, lon] for one country, from the database's rows."""
    head = [h.strip() for h in rows[0]]
    idx = {h: head.index(h) for h in ("Country", "Admin1", "Facility_n", "Facility_t", "Ownership", "Lat", "Long")}
    out = []
    for r in rows[1:]:
        r = r + [""] * (len(head) - len(r))
        names = (country_name,) if isinstance(country_name, str) else country_name
        if r[idx["Country"]].strip() not in names:
            continue
        try:
            lat, lon = round(float(r[idx["Lat"]]), 4), round(float(r[idx["Long"]]), 4)
        except ValueError:
            continue
        out.append([clean_text(r[idx["Facility_n"]]), clean_text(r[idx["Facility_t"]]),
                    clean_text(r[idx["Ownership"]]), clean_text(r[idx["Admin1"]]), lat, lon])
    out.sort(key=lambda f: (f[3], f[0]))
    return out


def check_positions(records: list[list], country: str, store: SnapshotStore | None) -> tuple[list[list], list[str]]:
    """Drop facilities whose position is wrong: outside the country, or far from the area their record names.

    A facility more than 25 km outside every area of its country, or more than 25 km from the first level area
    its own record names (when that name matches an area ACE knows), is left out, because sending someone there
    could send them the wrong way. The names of dropped facilities go in the snapshot's meta for review.
    """
    if store is None:
        return records, []
    from ..geo import distance_to_rings_km, in_bbox, in_polygons
    from ..places import Gazetteer, same_name

    def away(point: tuple[float, float], rings: list) -> float:
        return 0.0 if in_polygons(point, rings) else distance_to_rings_km(point, rings)
    places = Gazetteer(store)
    areas = places.areas(country)
    if not areas:
        return records, []
    kept, dropped = [], []
    for rec in records:
        point = (rec[4], rec[5])
        inside = [a for a in areas if in_bbox(point, a["bbox"], pad=0.25)]
        nearest = min((away(point, a["rings"]) for a in inside), default=float("inf"))
        if nearest > MAX_OUTSIDE_KM:
            dropped.append(f"{rec[0]} ({rec[3]}): outside {COUNTRIES[country].name}")
            continue
        # An old area name can map to several new areas (a region split in two), so check all of them.
        named = [a for a in areas if same_name(a["name"], rec[3])
                 or any(same_name(alias, rec[3]) for alias in a.get("aliases", ()))]
        if named and min(away(point, a["rings"]) for a in named) > MAX_OUTSIDE_KM:
            dropped.append(f"{rec[0]} ({rec[3]}): far from {named[0]['name']}")
            continue
        kept.append(rec)
    return kept, dropped


class HealthFacilitiesConnector:
    name = "public_health_facilities"
    dataset = "facilities"
    licence = "CC BY 4.0"
    refresh = timedelta(days=90)
    fallback = None
    countries = frozenset(NAMES)

    def __init__(self) -> None:
        self._rows: list[list[str]] | None = None

    def _all_rows(self) -> list[list[str]]:
        if self._rows is None:
            pkg = http_json(HDX_API + HDX_SLUG)["result"]
            res = next((r for r in pkg["resources"] if r["url"].lower().endswith(".xlsx")), None)
            if res is None:
                raise ConnectorError("no .xlsx resource in the HDX dataset")
            self._rows = read_xlsx(http_get(res["url"], timeout=300))
        return self._rows

    def fetch(self, country: str, store: SnapshotStore | None = None) -> Snapshot:
        country = country.upper()
        records = facility_records(self._all_rows(), NAMES[country])
        if not records:
            raise ConnectorError(f"no facilities for {COUNTRIES[country].name}")
        records, dropped = check_positions(records, country, store)
        return Snapshot(
            dataset="facilities", country=country, source_id="public_health_facilities",
            source="Maina et al. 2019, public health facilities in sub-Saharan Africa (KEMRI-Wellcome), via HDX",
            source_url=f"https://data.humdata.org/dataset/{HDX_SLUG}", licence=self.licence, retrieved_at=iso(),
            records=records, data_date="2019-07-25",
            meta={"facilities": len(records), "dropped_positions": dropped,
                  "paper": "https://doi.org/10.1038/s41597-019-0142-2",
                  "fields": ["name", "type", "ownership", "admin1", "lat", "lon"]})
