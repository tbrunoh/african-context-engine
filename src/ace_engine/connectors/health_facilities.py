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
NAMES = {"KE": "Kenya", "TZ": "Tanzania", "UG": "Uganda", "RW": "Rwanda", "ZA": "South Africa", "BW": "Botswana",
         "NA": "Namibia", "ZW": "Zimbabwe", "NG": "Nigeria", "GH": "Ghana", "SN": "Senegal", "CI": "Cote d'Ivoire",
         "TG": "Togo"}
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


def facility_records(rows: list[list[str]], country_name: str) -> list[list]:
    """[name, type, ownership, admin1, lat, lon] for one country, from the database's rows."""
    head = [h.strip() for h in rows[0]]
    idx = {h: head.index(h) for h in ("Country", "Admin1", "Facility_n", "Facility_t", "Ownership", "Lat", "Long")}
    out = []
    for r in rows[1:]:
        r = r + [""] * (len(head) - len(r))
        if r[idx["Country"]].strip() != country_name:
            continue
        try:
            lat, lon = round(float(r[idx["Lat"]]), 4), round(float(r[idx["Long"]]), 4)
        except ValueError:
            continue
        out.append([clean_text(r[idx["Facility_n"]]), clean_text(r[idx["Facility_t"]]),
                    clean_text(r[idx["Ownership"]]), clean_text(r[idx["Admin1"]]), lat, lon])
    out.sort(key=lambda f: (f[3], f[0]))
    return out


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
        return Snapshot(
            dataset="facilities", country=country, source_id="public_health_facilities",
            source="Maina et al. 2019, public health facilities in sub-Saharan Africa (KEMRI-Wellcome), via HDX",
            source_url=f"https://data.humdata.org/dataset/{HDX_SLUG}", licence=self.licence, retrieved_at=iso(),
            records=records, data_date="2019-07-25",
            meta={"facilities": len(records), "paper": "https://doi.org/10.1038/s41597-019-0142-2",
                  "fields": ["name", "type", "ownership", "admin1", "lat", "lon"]})
