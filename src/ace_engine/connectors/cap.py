"""Official warnings: Common Alerting Protocol (CAP) feeds from each country's alerting authority.

The feeds are the ones the WMO Register of Alerting Authorities lists for each covered country
(alertingauthority.wmo.int, read on 24 November 2026). ACE stores only alerts that are actual, public and not
yet expired, drops any alert a later message cancels, and keeps the authority's own words. Rwanda and
Namibia list no CAP feed in the register, so ACE says so instead of guessing.
"""
from __future__ import annotations

import email.utils
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from ..geo import simplify
from ..snapshots import Snapshot, SnapshotStore, parse_time, utcnow
from .base import ConnectorError, http_get, iso

REGISTER_URL = "https://alertingauthority.wmo.int/"

# country -> (authority, feed URLs in order of preference). The first URL is the one the register lists.
FEEDS: dict[str, tuple[str, tuple[str, ...]]] = {
    "KE": ("Kenya Meteorological Department",
           ("https://meteo.go.ke/api/cap/rss.xml", "https://cap-sources.s3.amazonaws.com/ke-kmd-en/rss.xml")),
    "TZ": ("Tanzania Meteorological Authority", ("https://cap-sources.s3.amazonaws.com/tz-tma-en/rss.xml",)),
    "UG": ("Uganda Department of Meteorological Services", ("https://wids.mwe.go.ug/api/v1/cap/feed",)),
    "ZA": ("South African Weather Service", ("http://caps.weathersa.co.za/Home/RssFeed",)),
    "BW": ("Botswana Meteorological Services", ("https://cap-sources.s3.amazonaws.com/bw-met-en/rss.xml",)),
    "ZW": ("Zimbabwe Meteorological Services Department", ("https://www.weatherzw.org.zw/api/cap/rss.xml",)),
    "NG": ("Nigerian Meteorological Agency", ("https://cap-sources.s3.amazonaws.com/ng-nimet-en/rss.xml",)),
    "GH": ("Ghana Meteorological Agency", ("https://www.meteo.gov.gh/api/cap/rss.xml",)),
    "SN": ("Agence Nationale de l'Aviation Civile et de la Météorologie (ANACIM)", ("https://cap-sources.s3.amazonaws.com/sn-anacim-fr/rss.xml",)),
    "CI": ("Direction de la Météorologie Nationale (SODEXAM)", ("https://cap-sources.s3.amazonaws.com/ci-sodexam-fr/rss.xml",)),
    "TG": ("Agence Nationale de la Météorologie du Togo", ("https://meteotogo.tg/api/cap/rss.xml",)),
    # Added in 2.1, each from the feed URL the WMO Register of Alerting Authorities lists for the country
    "CD": ("METTELSAT, Météo RD Congo", ("https://meteordcongo.cd/api/cap/rss.xml",
                                         "https://cap-sources.s3.amazonaws.com/cd-mettelsat-fr/rss.xml")),
    "MW": ("Department of Climate Change and Meteorological Services", ("https://www.metmalawi.gov.mw/api/cap/rss.xml",)),
    "BI": ("Institut Géographique du Burundi (IGEBU)", ("https://www.igebu.bi/api/cap/rss.xml",)),
    "CM": ("Direction de la Météorologie Nationale du Cameroun", ("https://cap-sources.s3.amazonaws.com/cm-meteo-fr/rss.xml",
                                                                   "https://cap-sources.s3.amazonaws.com/cm-meteo-en/rss.xml")),
    "BJ": ("Météo-Bénin", ("https://www.meteobenin.bj/api/cap/rss.xml",)),
    "ZM": ("Zambia Meteorological Department", ("https://zmd.gov.zm/api/cap/rss.xml",)),
    "TD": ("Agence Nationale de la Météorologie du Tchad", ("https://www.meteotchad.org/api/cap/rss.xml",)),
    "GN": ("Agence Nationale de la Météorologie de Guinée", ("https://anmeteo.gov.gn/api/cap/rss.xml",)),
    "BF": ("Agence Nationale de la Météorologie du Burkina Faso", ("https://www.meteoburkina.bf/api/cap/rss.xml",)),
    "SS": ("South Sudan Meteorological Service", ("https://meteosouthsudan.com.ss/api/cap/rss.xml",)),
    "ET": ("Ethiopian Meteorological Institute", ("https://www.ethiomet.gov.et/api/cap/rss.xml",)),
    "MZ": ("Instituto Nacional de Meteorologia de Moçambique", ("https://cap-sources.s3.amazonaws.com/mz-inam-pt/rss.xml",)),
    "GW": ("Instituto Nacional de Meteorologia da Guiné-Bissau", ("https://meteoguinebissau.gw/api/cap/rss.xml",)),
    "SO": ("Somalia National Meteorological Agency", ("https://meteosomalia.so/api/cap/rss.xml",)),
    "SD": ("Sudan Meteorological Authority", ("https://meteosudan.sd/api/cap/rss.xml",)),
    "DZ": ("Office National de la Météorologie", ("https://ametvigilance.meteo.dz/rss/rss_meteo_dz.xml",)),
    "EG": ("Egyptian Meteorological Authority", ("https://cap-sources.s3.amazonaws.com/eg-ema-en/rss.xml",
                                                 "https://cap-sources.s3.amazonaws.com/eg-ema-ar/rss.xml")),
    "LY": ("Libyan National Meteorological Centre", ("https://cap-sources.s3.amazonaws.com/ly-nmc-ar/rss.xml",
                                                     "https://cap-sources.s3.amazonaws.com/ly-nmc-en/rss.xml")),
    "TN": ("Institut National de la Météorologie", ("https://cap-sources.s3.amazonaws.com/tn-meteo-fr/rss.xml",)),
}
NO_FEED = {"RW": "Rwanda Meteorology Agency", "NA": "Namibia Meteorological Service",
           "AO": "Instituto Nacional de Meteorologia e Geofísica (INAMET)",
           "MA": "Direction Générale de la Météorologie"}

MAX_ITEMS = 40
LOOKBACK = timedelta(days=10)
VALID_FOR = timedelta(hours=6)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(el: ET.Element, name: str) -> list[ET.Element]:
    return [c for c in el if _local(c.tag) == name]


def _text(el: ET.Element | None, name: str) -> str:
    if el is None:
        return ""
    found = _children(el, name)
    return " ".join((found[0].text or "").split()) if found else ""


def feed_items(xml: bytes) -> list[tuple[str, datetime | None]]:
    """(link to a CAP message, published time) for each RSS item or Atom entry, newest first."""
    root = ET.fromstring(xml)
    items = []
    for el in root.iter():
        name = _local(el.tag)
        if name not in ("item", "entry"):
            continue
        link = _text(el, "link")
        if not link:
            for child in _children(el, "link"):
                if child.get("href"):
                    link = child.get("href", "")
                    if child.get("type", "").endswith("xml") or child.get("rel") in (None, "alternate"):
                        break
        when = None
        for field in ("pubDate", "published", "updated"):
            raw = _text(el, field)
            if raw:
                try:
                    when = (email.utils.parsedate_to_datetime(raw) if field == "pubDate"
                            else datetime.fromisoformat(raw.replace("Z", "+00:00")))
                except (TypeError, ValueError):
                    when = None
                if when is not None and when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
                break
        if link:
            items.append((link.strip(), when))
    items.sort(key=lambda t: t[1] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return items


def _polygon(raw: str) -> list[list[float]]:
    pts = []
    for pair in raw.split():
        try:
            lat, lon = (float(v) for v in pair.split(",")[:2])
        except ValueError:
            continue
        pts.append([round(lat, 3), round(lon, 3)])
    return simplify(pts, 0.01) if len(pts) >= 4 else []


def parse_alert(xml: bytes, url: str, prefer: tuple[str, ...] = ("en", "fr", "pt", "ar")) -> dict | None:
    """One CAP message as a compact record, or None when it is not an actual, public alert or update."""
    root = ET.fromstring(xml)
    if _local(root.tag) != "alert":
        return None
    status, scope, msg_type = _text(root, "status"), _text(root, "scope"), _text(root, "msgType")
    record = {"id": _text(root, "identifier"), "sender": _text(root, "sender"), "sent": _text(root, "sent"),
              "msg_type": msg_type, "references": _text(root, "references").split(), "url": url}
    if status != "Actual" or scope != "Public":
        return None
    if msg_type == "Cancel":
        record["cancel"] = True
        return record
    infos = _children(root, "info")
    if not infos:
        return None
    infos.sort(key=lambda i: next((n for n, lang in enumerate(prefer) if _text(i, "language").lower().startswith(lang)),
                                  len(prefer)))
    info = infos[0]
    areas = _children(info, "area")
    record.update({
        "language": (_text(info, "language") or "en")[:2].lower(), "event": _text(info, "event"),
        "headline": _text(info, "headline"), "severity": _text(info, "severity"),
        "urgency": _text(info, "urgency"), "certainty": _text(info, "certainty"),
        "onset": _text(info, "onset") or _text(info, "effective") or record["sent"],
        "expires": _text(info, "expires"), "sender_name": _text(info, "senderName"),
        "description": _text(info, "description"), "instruction": _text(info, "instruction"),
        "web": _text(info, "web"),
        "area_desc": [d for d in (_text(a, "areaDesc") for a in areas) if d],
        "polygons": [p for a in areas for p in (_polygon(c.text or "") for c in _children(a, "polygon")) if p],
    })
    return record


class CapConnector:
    name = "cap"
    dataset = "warnings"
    licence = "official public warnings, terms set by each authority"
    refresh = timedelta(hours=1)
    fallback = None
    countries = frozenset(FEEDS)

    def fetch(self, country: str, store: SnapshotStore | None = None) -> Snapshot:
        country = country.upper()
        if country not in FEEDS:
            raise ConnectorError(f"the WMO register lists no CAP feed for {country}")
        authority, urls = FEEDS[country]
        now = utcnow()
        feed_url, items, errors = "", [], []
        for url in urls:  # the register's URL first; a mirror only when it is down or older
            try:
                found = feed_items(http_get(url, timeout=45))
            except (ConnectorError, ET.ParseError) as exc:
                errors.append(str(exc))
                continue
            newest = found[0][1] if found and found[0][1] else None
            current = items[0][1] if items and items[0][1] else None
            if not feed_url or (newest and (current is None or newest > current)):
                feed_url, items = url, found
        if not feed_url:
            raise ConnectorError("; ".join(errors) or f"no feed reachable for {country}")
        alerts: dict[str, dict] = {}
        cancelled: set[str] = set()
        for link, when in items[:MAX_ITEMS]:
            if when and now - when > LOOKBACK:
                continue
            try:
                rec = parse_alert(http_get(link, timeout=45), link)
            except (ConnectorError, ET.ParseError):
                continue
            if rec is None:
                continue
            for ref in rec["references"]:  # sender,identifier,sent triples
                parts = ref.split(",")
                if len(parts) >= 2:
                    cancelled.add(parts[1])
            if rec.get("cancel"):
                continue
            expires = parse_time(rec["expires"]) if rec["expires"] else None
            if expires is None or expires < now:
                continue
            alerts[rec["id"]] = rec
        live = sorted((a for i, a in alerts.items() if i not in cancelled),
                      key=lambda a: parse_time(a["onset"]) or now)
        for a in live:
            a.pop("references", None)
        return Snapshot(
            dataset="warnings", country=country, source_id="cap",
            source=f"{authority}, official CAP warnings", source_url=feed_url,
            licence=self.licence, retrieved_at=iso(now), records=live, data_date=iso(now),
            valid_until=iso(now + VALID_FOR),
            meta={"authority": authority, "feed": feed_url, "register": REGISTER_URL, "alerts": len(live),
                  "primary": feed_url == urls[0],
                  "newest_item": iso(items[0][1]) if items and items[0][1] else None})

