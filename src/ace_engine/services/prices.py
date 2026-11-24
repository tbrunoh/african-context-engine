"""Market prices: what a food cost in the market nearest the person, and how that compares with the month before.

Built on the WFP price database. ACE refuses to quote a price older than four months, and says how old the
latest one is, because an old price presented as current is a wrong answer. Botswana has no WFP price data.
"""
from __future__ import annotations

from datetime import date

from ..connectors.hdx_prices import SLUGS
from ..countries import COUNTRIES
from ..geo import haversine_km
from ..text import fold, tokens
from .base import (
    LANGS,
    Answer,
    Context,
    Query,
    Refusal,
    Result,
    all_langs,
    cite_snapshot,
    fit,
    month_year,
    needs_place,
    say,
)

MAX_AGE_DAYS = 125  # about four months

# words people type -> a word found in WFP commodity names
FOODS = {
    "maize": "maize", "corn": "maize", "mahindi": "maize", "mais": "maize", "unga": "maize flour",
    "flour": "flour", "farine": "flour", "beans": "beans", "bean": "beans", "maharagwe": "beans", "haricot": "beans",
    "haricots": "beans", "rice": "rice", "mchele": "rice", "wali": "rice", "riz": "rice", "sorghum": "sorghum",
    "mtama": "sorghum", "sorgho": "sorghum", "millet": "millet", "uwele": "millet", "mil": "millet",
    "cassava": "cassava", "muhogo": "cassava", "manioc": "cassava", "gari": "gari", "attieke": "attieke",
    "sugar": "sugar", "sukari": "sugar", "sucre": "sugar", "oil": "oil", "mafuta": "oil", "huile": "oil",
    "milk": "milk", "maziwa": "milk", "lait": "milk", "potato": "potatoes", "potatoes": "potatoes", "viazi": "potatoes",
    "tomato": "tomatoes", "tomatoes": "tomatoes", "nyanya": "tomatoes", "tomate": "tomatoes", "tomates": "tomatoes",
    "onion": "onions", "onions": "onions", "vitunguu": "onions", "oignon": "onions", "oignons": "onions",
    "groundnuts": "groundnuts", "peanuts": "groundnuts", "karanga": "groundnuts", "arachide": "groundnuts",
    "cowpeas": "cowpeas", "niebe": "cowpeas", "yam": "yam", "yams": "yam", "igname": "yam", "plantain": "plantain",
    "bananas": "bananas", "ndizi": "bananas", "wheat": "wheat", "ngano": "wheat", "ble": "wheat", "bread": "bread",
    "mkate": "bread", "pain": "bread", "eggs": "eggs", "mayai": "eggs", "oeufs": "eggs", "meat": "meat",
    "nyama": "meat", "viande": "meat", "fish": "fish", "samaki": "fish", "poisson": "fish",
}

LINE = {"en": "{food} at {market}: {currency} {price} per {unit} in {month}",
        "sw": "{food} soko la {market}: {currency} {price} kwa {unit} mwezi {month}",
        "fr": "{food} au marché de {market} : {currency} {price} le {unit} en {month}"}
CHANGE = {"up": {"en": "up {pct}% on {prev}", "sw": "juu kwa {pct}% kuliko {prev}", "fr": "en hausse de {pct} % sur {prev}"},
          "down": {"en": "down {pct}% on {prev}", "sw": "chini kwa {pct}% kuliko {prev}",
                   "fr": "en baisse de {pct} % sur {prev}"},
          "same": {"en": "the same as {prev}", "sw": "sawa na {prev}", "fr": "comme en {prev}"}}
ITEM = {"en": "{food} {currency} {price} per {unit} ({month})", "sw": "{food} {currency} {price} kwa {unit} ({month})",
        "fr": "{food} {currency} {price} le {unit} ({month})"}
FAR = {"en": "({km} km from {place})", "sw": "(km {km} kutoka {place})", "fr": "(à {km} km de {place})"}
FOOT = {"en": "WFP prices.", "sw": "Bei za WFP.", "fr": "Prix du PAM."}
TOP = {"en": "Latest WFP prices at {market}{far}:", "sw": "Bei za karibuni za WFP soko la {market}{far}:",
       "fr": "Derniers prix du PAM au marché de {market}{far} :"}
STAPLES = ("maize", "beans", "rice", "sorghum", "millet", "cassava", "wheat", "flour", "yam", "gari", "plantain",
           "groundnut", "cowpea", "potato", "sugar", "oil")
OLD = {"en": "The latest WFP price ACE holds for {country} is from {month}, too old to use. Ask traders or your "
             "agriculture office.",
       "sw": "Bei ya karibuni ya WFP ambayo ACE inayo kwa {country} ni ya {month}, ya zamani mno. Waulize wafanyabiashara "
             "au ofisi ya kilimo.",
       "fr": "Le dernier prix du PAM dont ACE dispose pour {country} date de {month}, trop ancien. Demandez aux "
             "commerçants ou au service agricole."}
GAP = {"en": "WFP publishes no market prices for {country}, so ACE cannot give prices there. Ask traders or your "
             "agriculture office.",
       "sw": "WFP haichapishi bei za soko kwa {country}, hivyo ACE haiwezi kutoa bei huko. Waulize wafanyabiashara au "
             "ofisi ya kilimo.",
       "fr": "Le PAM ne publie pas de prix de marché pour {country}, donc ACE ne peut pas donner de prix. Demandez aux "
             "commerçants ou au service agricole."}
NO_FOOD = {"en": "ACE has no recent WFP price for {food} near {place}.",
           "sw": "ACE haina bei ya karibuni ya WFP ya {food} karibu na {place}.",
           "fr": "ACE n'a pas de prix récent du PAM pour {food} près de {place}."}


def wanted_food(text: str) -> str | None:
    for tok in tokens(text):
        if tok in FOODS:
            return FOODS[tok]
    return None


def fmt_price(value: float) -> str:
    return f"{value:,.0f}" if value >= 100 else f"{value:,.2f}".rstrip("0").rstrip(".")


def age_days(month: str, today: date) -> int:
    y, m = (int(v) for v in month[:7].split("-"))
    return (today - date(y, m, 15)).days


class PricesService:
    id = "market_prices"
    title = {"en": "Market prices", "sw": "Bei za soko", "fr": "Prix du marché"}
    countries = frozenset(SLUGS)
    connectors = ("wfp_prices",)

    def coverage(self, country: str, ctx: Context) -> tuple[bool, str]:
        if country not in SLUGS:
            return False, "WFP publishes no price dataset for this country"
        snap = ctx.snapshots.get("prices", country)
        if snap is None:
            return False, "no price snapshot yet"
        if snap.data_date and age_days(snap.data_date, date.today()) > MAX_AGE_DAYS:
            return False, f"latest WFP prices are from {month_year(snap.data_date, 'en')}, too old to quote"
        return True, f"{len(snap.records)} markets, latest {month_year(snap.data_date, 'en')}"

    def answer(self, q: Query, ctx: Context) -> Result:
        country = (q.place.country if q.place else q.country) or ""
        if country and country not in SLUGS:
            return Refusal(self.id, "gap", all_langs(GAP, country=COUNTRIES[country].name))
        if q.place is None and q.location is None:
            return needs_place(self.id, q.country)
        snap = ctx.snapshots.get("prices", country)
        if snap is None:
            return Refusal(self.id, "gap", all_langs(GAP, country=COUNTRIES.get(country).name if country else ""))
        today = q.now.date()
        if snap.data_date and age_days(snap.data_date, today) > MAX_AGE_DAYS:
            return Refusal(self.id, "stale", {lang: say(OLD, lang, country=COUNTRIES[country].name,
                                                        month=month_year(snap.data_date, lang)) for lang in LANGS},
                           [cite_snapshot(snap)])
        origin = (q.location.lat, q.location.lon) if q.location else q.place.point
        food = q.params.get("food") or wanted_food(q.text)
        fresh = []
        for m in snap.records:
            items = [i for i in m["items"] if age_days(i["series"][-1][0], today) <= MAX_AGE_DAYS]
            if food:
                items = [i for i in items if fold(food) in fold(i["commodity"])]
            if items:
                fresh.append((haversine_km(origin, (m["lat"], m["lon"])), m, items))
        if food:  # prefer the food itself to products made from it: maize grain over maize flour
            def exact(item: dict) -> bool:
                base = fold(item["commodity"]).split(" (")[0].strip()
                return base == fold(food) or base == fold(food).rstrip("s")
            if any(exact(i) for _, _, items in fresh for i in items):
                fresh = [(km, m, [i for i in items if exact(i)]) for km, m, items in fresh]
                fresh = [t for t in fresh if t[2]]
        place_name = q.place.name if q.place else ""
        if not fresh:
            name = food or ""
            return Refusal(self.id, "no_match", all_langs(NO_FOOD, food=name, place=place_name or country),
                           [cite_snapshot(snap)])
        km, market, items = min(fresh, key=lambda t: t[0])
        def staple_rank(item: dict) -> int:
            name = fold(item["commodity"])
            return next((n for n, word in enumerate(STAPLES) if word in name), len(STAPLES))
        items.sort(key=lambda i: (staple_rank(i), -len(i["series"]), i["commodity"]))
        shown = items[:1] if food else items[:3]
        text = {}
        for lang in LANGS:
            lines = []
            for item in shown:
                month, price = item["series"][-1]
                values = dict(food=item["commodity"], market=market["market"], currency=item["currency"],
                              price=fmt_price(price), unit=item["unit"], month=month_year(month, lang))
                line = say(LINE if food else ITEM, lang, **values)
                if food and len(item["series"]) >= 2:
                    prev_m, prev = item["series"][-2]
                    if prev:
                        pct = round((price - prev) / prev * 100)
                        kind = "up" if pct > 0 else "down" if pct < 0 else "same"
                        line += ", " + say(CHANGE[kind], lang, pct=abs(pct), prev=month_year(prev_m, lang))
                lines.append(line)
            far = f" {say(FAR, lang, km=round(km), place=place_name)}" if place_name and km > 25 else ""
            if food:
                pieces = [f"{lines[0]}{far}.", say(FOOT, lang)]
            else:
                pieces = [f"{say(TOP, lang, market=market['market'], far=far)} " + "; ".join(lines) + ".", say(FOOT, lang)]
            text[lang] = fit(pieces, q.max_chars)
        return Answer(
            self.id, text, [cite_snapshot(snap)], confidence="high", data_date=snap.data_date,
            data={"country": country, "market": {k: market[k] for k in ("market", "admin1", "lat", "lon")},
                  "distance_km": round(km, 1), "items": shown})
