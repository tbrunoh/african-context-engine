"""Market prices: the World Food Programme price database, as published per country on HDX.

WFP publishes monthly food prices by market under CC BY-IGO on the Humanitarian Data Exchange. ACE keeps,
for every market, the last six monthly retail prices of each food it reports (WFP's non food items are
left out) (wholesale only where no retail
price exists), so a service can say what a food cost in the nearest market and how that compares with the
month before. Services refuse to quote prices that are too old to use. Botswana has no WFP price dataset.
"""
from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import timedelta

from ..countries import COUNTRIES
from ..snapshots import Snapshot, SnapshotStore
from .base import ConnectorError, http_get, http_json, iso

HDX_API = "https://data.humdata.org/api/3/action/package_show?id="
SLUGS = {"KE": "kenya", "TZ": "united-republic-of-tanzania", "UG": "uganda", "RW": "rwanda", "ZA": "south-africa",
         "NA": "namibia", "ZW": "zimbabwe", "NG": "nigeria", "GH": "ghana", "SN": "senegal", "CI": "cote-d-ivoire",
         "TG": "togo"}
KEEP_MONTHS = 6


def aggregate(rows: list[dict]) -> tuple[list[dict], str | None]:
    """Group WFP rows into markets with the last few monthly prices per food. Returns (markets, latest month)."""
    series: dict[tuple, dict[str, float]] = defaultdict(dict)
    markets: dict[str, dict] = {}
    for r in rows:
        if r.get("priceflag", "actual") not in ("actual", "aggregate") or not r.get("price"):
            continue
        if r.get("date", "").startswith("#") or r.get("category", "").lower() == "non-food":  # HXL row, or not food
            continue
        try:
            price = float(r["price"])
            lat, lon = float(r["latitude"]), float(r["longitude"])
        except (TypeError, ValueError):
            continue
        mid = r["market_id"]
        markets.setdefault(mid, {"market": r["market"], "admin1": r.get("admin1", ""), "admin2": r.get("admin2", ""),
                                 "lat": round(lat, 4), "lon": round(lon, 4)})
        key = (mid, r["commodity"], r["unit"], r["pricetype"], r["currency"])
        series[key][r["date"][:7]] = price
    by_market: dict[str, dict[tuple, dict]] = defaultdict(dict)
    for (mid, commodity, unit, ptype, currency), points in series.items():
        by_market[mid][(commodity, unit, ptype, currency)] = points
    out, latest = [], None
    for mid, items in by_market.items():
        chosen = []
        names = {c for c, _, _, _ in items}
        for name in sorted(names):
            options = [(k, v) for k, v in items.items() if k[0] == name]
            retail = [o for o in options if o[0][2].lower() == "retail"]
            pick = max(retail or options, key=lambda o: max(o[1]))  # the series with the latest month
            (commodity, unit, ptype, currency), points = pick
            months = sorted(points)[-KEEP_MONTHS:]
            chosen.append({"commodity": commodity, "unit": unit, "pricetype": ptype, "currency": currency,
                           "series": [[m, points[m]] for m in months]})
            latest = max(latest or months[-1], months[-1])
        out.append({**markets[mid], "id": mid, "items": chosen})
    out.sort(key=lambda m: m["market"])
    return out, latest


class WfpPricesConnector:
    name = "wfp_prices"
    dataset = "prices"
    licence = "CC BY-IGO"
    refresh = timedelta(days=7)
    fallback = None
    countries = frozenset(SLUGS)

    def fetch(self, country: str, store: SnapshotStore | None = None) -> Snapshot:
        country = country.upper()
        if country not in SLUGS:
            raise ConnectorError(f"WFP publishes no price dataset on HDX for {COUNTRIES[country].name}")
        slug = f"wfp-food-prices-for-{SLUGS[country]}"
        pkg = http_json(HDX_API + slug)["result"]
        res = next((r for r in pkg["resources"] if r["format"].lower() == "csv"
                    and "qc" not in r["name"].lower() and "quickchart" not in r["name"].lower()), None)
        if res is None:
            raise ConnectorError(f"no CSV in {slug}")
        text = http_get(res["url"], timeout=180).decode("utf-8-sig")
        markets, latest = aggregate(list(csv.DictReader(io.StringIO(text))))
        if not markets:
            raise ConnectorError(f"no usable prices in {slug}")
        return Snapshot(
            dataset="prices", country=country, source_id="wfp_prices",
            source=f"WFP Price Database, {COUNTRIES[country].name} food prices, via HDX",
            source_url=f"https://data.humdata.org/dataset/{slug}", licence=pkg.get("license_title", self.licence),
            retrieved_at=iso(), records=markets, data_date=latest, meta={"markets": len(markets)})
