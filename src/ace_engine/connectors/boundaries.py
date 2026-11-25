"""Administrative boundaries for the places gazetteer.

Sources, chosen per country for the level people actually name:
* geoBoundaries (gbOpen), first level areas, for 11 of the first 13 countries. Each country keeps the licence
  geoBoundaries records for it: public domain, CC BY, CC BY-SA or ODbL.
* OCHA Common Operational Datasets (COD-AB) on HDX, CC BY-IGO, for Uganda (its 135 districts, from the
  Uganda Bureau of Statistics), Namibia (its regions, from the Namibia Statistics Agency) and all 21
  countries added in 2.1, where national statistics offices endorse the layer and it is newer than
  geoBoundaries. Malawi uses its 28 districts, the level people name; the others their first level.
  The alternative names a COD layer carries (Arabic, French or Portuguese spellings) become aliases.

Shapes are simplified to about 300 metres, which is plenty to tell which area a point is in.
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import timedelta

from ..countries import COUNTRIES, ISO3
from ..geo import bbox, centroid, simplify
from ..snapshots import Snapshot, SnapshotStore
from .base import ConnectorError, http_get, http_json, iso

GB_MEDIA = "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen"
GB_PAGE = "https://www.geoboundaries.org/countryDownloads.html"
HDX_API = "https://data.humdata.org/api/3/action/package_show?id="

# country -> (source, level). Everything else uses geoBoundaries ADM1.
COD_AB = {"UG": "ADM2", "NA": "ADM1", "MW": "ADM2", "LY": "ADM2", "TN": "ADM2",
          **{c: "ADM1" for c in ("CD", "BI", "CM", "BJ", "ZM", "TD", "GN", "BF", "SS", "ET", "MZ", "GW", "AO",
                                 "SO", "SD", "DZ", "EG", "MA")}}
# Placeholder areas a layer carries that no one lives in or names (a contested strip), left out of the gazetteer.
SKIP = {"contested", "disputed"}

# Common names people use for an area whose official name differs. Capitals and spelling fixes only.
ALIASES: dict[str, dict[str, list[str]]] = {
    "NG": {"Abuja Federal Capital Territory": ["Abuja", "FCT"]},
    "GH": {"Greater Accra Region": ["Accra"], "Ashanti Region": ["Kumasi"]},
    "ZA": {"Gauteng": ["Johannesburg", "Pretoria"], "Western Cape": ["Cape Town"], "KwaZulu-Natal": ["Durban"]},
    "RW": {"City of Kigali": ["Kigali"]},
    "CI": {"District Autonome D'Abidjan": ["Abidjan"], "District Autonome De Yamoussoukro": ["Yamoussoukro"]},
    "KE": {"Tharaka": ["Tharaka Nithi"], "Elgeyo-Marakwet": ["Elgeyo Marakwet", "Keiyo"]},
    "TZ": {"Pwani": ["Coast"]},
    "CD": {"Kongo-Central": ["Kongo Central", "Muanda", "Moanda", "Matadi", "Boma"], "Haut-Katanga": ["Lubumbashi"],
           "Nord-Kivu": ["Goma", "North Kivu"], "Sud-Kivu": ["Bukavu", "South Kivu"], "Tshopo": ["Kisangani"],
           "Kasaï-Oriental": ["Mbuji-Mayi"], "Kasaï-Central": ["Kananga"], "Ituri": ["Bunia"]},
    "CM": {"Littoral": ["Douala"], "Centre": ["Yaoundé", "Yaounde"], "West": ["Bafoussam"], "North-West": ["Bamenda"]},
    "BJ": {"Littoral": ["Cotonou"], "Oueme": ["Porto-Novo", "Porto Novo"], "Borgou": ["Parakou"]},
    "ZM": {"Copperbelt": ["Ndola", "Kitwe"], "Southern": ["Livingstone", "Choma"], "Eastern": ["Chipata"]},
    "TD": {"N'DJAMENA": ["Ndjamena", "N'Djamena"]},
    "BF": {"Kadiogo": ["Ouagadougou"], "Guiriko": ["Bobo-Dioulasso", "Bobo Dioulasso"]},
    "SS": {"Central Equatoria": ["Juba"], "Western Bahr el Ghazal": ["Wau"], "Upper Nile": ["Malakal"]},
    "ET": {"Oromia": ["Oromiyaa", "Adama", "Jimma"], "Amhara": ["Bahir Dar", "Gondar"], "Tigray": ["Mekelle"],
           "Sidama": ["Hawassa"], "Addis Ababa": ["Addis Abeba", "Finfinne", "አዲስ አበባ"], "Dire Dawa": ["ድሬዳዋ"]},
    "MZ": {"Cidade de Maputo": ["Maputo City"], "Sofala": ["Beira"], "Zambézia": ["Quelimane"]},
    "AO": {"Luanda": ["Luanda city"], "Huíla": ["Lubango"], "Benguela": ["Lobito"]},
    "SO": {"Banadir": ["Mogadishu", "Muqdisho", "مقديشو"], "Woqooyi Galbeed": ["Hargeisa", "Hargeysa"],
           "Bari": ["Bosaso", "Boosaaso"], "Nugaal": ["Garowe"], "Bay": ["Baidoa", "Baydhabo"]},
    "SD": {"Khartoum": ["Omdurman", "Bahri"], "Red Sea": ["Port Sudan", "بورتسودان"], "Aj Jazirah": ["Gezira", "Wad Madani"]},
    "MA": {"Casablanca Settat": ["Casablanca"], "Rabat Sale Kenitra": ["Rabat", "Kenitra"], "Marrakech Safi": ["Marrakech"],
           "Fez Meknes": ["Fès", "Fes", "Meknès", "Fès-Meknès"], "Tangier Tetouan Al Hoceima": ["Tanger", "Tangier"],
           "Souss Massa": ["Agadir"], "Oriental": ["Oujda"]},
}

# The official spelling where the source drops accents, misspells or title cases a name. People see this name;
# the source's own spelling stays as an alias, so a message typed either way still matches.
DISPLAY: dict[str, dict[str, str]] = {
    "KE": {"Tharaka": "Tharaka-Nithi"},
    "ZA": {"Nothern Cape": "Northern Cape"},
    "SN": {"Thies": "Thiès", "Kedougou": "Kédougou", "Sedhiou": "Sédhiou", "Saint Louis": "Saint-Louis"},
    "CI": {"Comoe": "Comoé", "Denguele": "Denguélé", "District Autonome D'Abidjan": "District Autonome d'Abidjan",
           "District Autonome De Yamoussoukro": "District Autonome de Yamoussoukro", "Goh-Djiboua": "Gôh-Djiboua",
           "Sassandra-Marahoue": "Sassandra-Marahoué", "Valle Du Bandama": "Vallée du Bandama"},
    "TG": {"Centrale Region": "Centrale", "Kara Region": "Kara", "Maritime Region": "Maritime",
           "Plateaux Region": "Plateaux", "Savanes Region": "Savanes"},
    "GN": {"Boke": "Boké", "Labe": "Labé", "Nzerekore": "Nzérékoré"},
    "BJ": {"Oueme": "Ouémé"},
    "GW": {"Bafata": "Bafatá", "Gabu": "Gabú", "Bolama/Bijagos": "Bolama-Bijagós"},
    "CD": {"Equateur": "Équateur"},
    "MW": {"Nkhatabay": "Nkhata Bay"},
    "ET": {"Addis Ababa": "Addis Ababa"},
}


def tidy_case(name: str) -> str:
    """Some layers write names in capitals (BARH EL GAZEL). People see them in title case: Barh El Gazel."""
    if not name.isupper():
        return name
    return " ".join(w if "'" in w and len(w) <= 3 else "-".join(p.capitalize() for p in w.split("-"))
                    for w in name.lower().split()).replace("N'djamena", "N'Djamena")


def named(country: str, source_name: str) -> tuple[str, list[str]]:
    """The name people see and its aliases, from the name the source uses."""
    display = DISPLAY.get(country, {}).get(source_name) or tidy_case(source_name)
    aliases = list(ALIASES.get(country, {}).get(source_name, []))
    if display != source_name:
        aliases.append(source_name)
    return display, aliases


TOLERANCE = 0.003  # degrees, about 330 m


def _rings(geometry: dict) -> list[list[list[float]]]:
    """GeoJSON (lon, lat) polygons to simplified (lat, lon) outer and inner rings."""
    polys = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    out = []
    for poly in polys:
        for ring in poly:
            latlon = [[round(p[1], 3), round(p[0], 3)] for p in ring]
            simple = simplify(latlon, TOLERANCE)
            if len(simple) >= 4:
                out.append(simple)
    return out


def _record(code: str, name: str, level: str, geometry: dict, aliases: list[str]) -> dict:
    rings = _rings(geometry)
    if not rings:
        raise ConnectorError(f"empty geometry for {name}")
    rec = {"code": code, "name": name, "level": level, "centroid": list(centroid(rings)),
           "bbox": [round(v, 3) for v in bbox(rings)], "rings": rings}
    if aliases:
        rec["aliases"] = aliases
    return rec


class BoundariesConnector:
    name = "boundaries"
    dataset = "places"
    licence = "varies by country, see the licence register"
    refresh = timedelta(days=365)
    fallback = None
    countries = frozenset(COUNTRIES)

    def fetch(self, country: str, store: SnapshotStore | None = None) -> Snapshot:
        country = country.upper()
        if country in COD_AB:
            return self._cod_ab(country, COD_AB[country])
        return self._geoboundaries(country)

    def _geoboundaries(self, country: str) -> Snapshot:
        iso3 = ISO3[country]
        base = f"{GB_MEDIA}/{iso3}/ADM1/geoBoundaries-{iso3}-ADM1"
        meta = json.loads(http_get(base + "-metaData.json"))
        geo = json.loads(http_get(base + "_simplified.geojson"))
        seen: set[str] = set()
        records = []
        for f in geo["features"]:
            p = f["properties"]
            name = p["shapeName"]
            if name in seen:
                continue
            seen.add(name)
            display, also = named(country, name)
            records.append(_record(p.get("shapeISO") or p["shapeID"], display, "ADM1", f["geometry"], also))
        records.sort(key=lambda r: r["name"])
        return Snapshot(
            dataset="places", country=country, source_id="geoboundaries",
            source=f"geoBoundaries gbOpen ADM1, from {meta.get('boundarySource', 'geoBoundaries')}",
            source_url=GB_PAGE, licence=meta.get("boundaryLicense", ""), retrieved_at=iso(),
            records=records, data_date=meta.get("sourceDataUpdateDate"),
            meta={"boundary_id": meta.get("boundaryID"), "level": "ADM1", "areas": len(records)})

    def _cod_ab(self, country: str, level: str) -> Snapshot:
        iso3 = ISO3[country].lower()
        pkg = http_json(HDX_API + f"cod-ab-{iso3}")["result"]
        res = next((r for r in pkg["resources"] if r["format"].lower() == "geojson"), None)
        if res is None:
            raise ConnectorError(f"no GeoJSON resource in cod-ab-{iso3}")
        n = level[-1]
        with zipfile.ZipFile(io.BytesIO(http_get(res["url"], timeout=300))) as z:
            member = next(m for m in z.namelist() if m.endswith(f"admin{n}.geojson"))
            geo = json.loads(z.read(member))
        records = []
        for f in geo["features"]:
            p = f["properties"]
            name = p[f"adm{n}_name"]
            if any(w in name.lower() for w in SKIP):
                continue
            display, also = named(country, name)
            others = [str(v).strip() for k, v in p.items()
                      if k.startswith((f"adm{n}_name", f"adm{n}_ref_name", f"adm{n}_alt")) and v and str(v).strip() != name]
            also = list(dict.fromkeys([*also, *(o for o in others if o != display)]))
            records.append(_record(p[f"adm{n}_pcode"], display, level, f["geometry"], also))
        records.sort(key=lambda r: r["name"])
        return Snapshot(
            dataset="places", country=country, source_id="ocha_cod_ab",
            source=f"OCHA COD-AB {COUNTRIES[country].name} {level}, from {pkg.get('dataset_source', 'OCHA')}",
            source_url=f"https://data.humdata.org/dataset/cod-ab-{iso3}", licence=pkg.get("license_title", ""),
            retrieved_at=iso(), records=records, data_date=(pkg.get("last_modified") or "")[:10] or None,
            meta={"level": level, "areas": len(records)})
