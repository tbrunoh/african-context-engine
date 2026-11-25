"""Market prices: what a food cost in the market nearest the person, and how that compares with the month before.

Built on the WFP price database. ACE refuses to quote a price older than four months, and says how old the
latest one is, because an old price presented as current is a wrong answer. Botswana has no WFP price data.
"""
from __future__ import annotations

from datetime import date

from .. import i18n
from ..connectors.hdx_prices import SLUGS
from ..geo import haversine_km
from ..text import contains_phrase, fold, tokens, word_forms
from .base import (
    LANGS,
    Answer,
    Context,
    Query,
    Refusal,
    Result,
    cite_snapshot,
    country_said,
    fit,
    french,
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
    "teff": "teff", "barley": "barley", "lentils": "lentils", "pasta": "pasta",
}
FOODS = {fold(k): v for k, v in i18n.phrase_map("services.prices.FOODS", FOODS).items()}
FOOD_PHRASES = sorted((k for k in FOODS if " " in k), key=len, reverse=True)

# WFP names commodities in English. The common ones are said in the person's language; the rest stay as WFP wrote them.
LOCAL_FOOD: dict[str, dict[str, str]] = {
    "en": {},
    "sw": {"maize": "Mahindi", "maize flour": "Unga wa mahindi", "maize meal": "Unga wa mahindi", "beans": "Maharagwe",
           "rice": "Mchele", "sorghum": "Mtama", "millet": "Uwele", "cassava": "Muhogo",
           "cassava flour": "Unga wa muhogo", "sugar": "Sukari", "oil": "Mafuta", "wheat flour": "Unga wa ngano",
           "groundnuts": "Karanga", "cowpeas": "Kunde", "potatoes": "Viazi", "tomatoes": "Nyanya",
           "onions": "Vitunguu", "salt": "Chumvi", "milk": "Maziwa", "eggs": "Mayai", "bread": "Mkate",
           "wheat": "Ngano"},
    "fr": {"maize": "Maïs", "maize flour": "Farine de maïs", "maize meal": "Farine de maïs", "beans": "Haricots",
           "rice": "Riz", "sorghum": "Sorgho", "millet": "Mil", "cassava": "Manioc", "cassava flour": "Farine de manioc",
           "sugar": "Sucre", "oil": "Huile", "wheat flour": "Farine de blé", "groundnuts": "Arachides",
           "cowpeas": "Niébé", "potatoes": "Pommes de terre", "tomatoes": "Tomates", "onions": "Oignons",
           "salt": "Sel", "milk": "Lait", "eggs": "Œufs", "bread": "Pain", "wheat": "Blé", "lentils": "Lentilles"},
}
LOCAL_DETAIL: dict[str, dict[str, str]] = {
    "en": {},
    "sw": {"white": "nyeupe", "yellow": "njano", "imported": "kutoka nje", "local": "ya ndani", "dry": "kavu",
           "red": "nyekundu"},
    "fr": {"white": "blanc", "yellow": "jaune", "imported": "importé", "local": "local", "dry": "sec", "red": "rouge"},
}


def food_name(commodity: str, lang: str) -> str:
    """Maize (white, dry) reads Mahindi (nyeupe, kavu) in Swahili and Maïs (blanc, sec) in French."""
    if lang == "en":
        return commodity
    base, _, rest = commodity.partition(" (")
    local = (LOCAL_FOOD.get(lang) or {}).get(fold(base).strip())
    if local is None:
        return commodity
    detail = LOCAL_DETAIL.get(lang) or {}
    details = [d.strip() for d in rest.rstrip(")").split(",") if d.strip()]
    said = [detail.get(fold(d), d) for d in details]
    return local + (f" ({', '.join(said)})" if said else "")


UNIT = {"en": "per {unit}", "sw": "kwa {unit}", "fr": "le {unit}"}
UNIT_MANY = {"en": "per {unit}", "sw": "kwa {unit}", "fr": "les {unit}"}


def unit_name(unit: str, lang: str) -> str:
    """How a language says the unit: per KG; French counts several units in the plural, les 90 kg but le kg."""
    many = unit[:1].isdigit() and unit.split()[0] not in ("1", "1.0")
    return say(UNIT_MANY if many else UNIT, lang, unit=unit)


LINE = {"en": "{food} at {market}: {currency} {price} {unit} in {month}",
        "sw": "{food} soko la {market}: {currency} {price} {unit} mwezi {month}",
        "fr": "{food} au marché de {market} : {currency} {price} {unit} en {month}"}
CHANGE = {"up": {"en": "up {pct}% on {prev}", "sw": "juu kwa {pct}% kuliko {prev}", "fr": "en hausse de {pct} % sur {prev}"},
          "down": {"en": "down {pct}% on {prev}", "sw": "chini kwa {pct}% kuliko {prev}",
                   "fr": "en baisse de {pct} % sur {prev}"},
          "same": {"en": "the same as {prev}", "sw": "sawa na {prev}", "fr": "comme en {prev}"}}
ITEM = {"en": "{food} {currency} {price} {unit} ({month})", "sw": "{food} {currency} {price} {unit} ({month})",
        "fr": "{food} {currency} {price} {unit} ({month})"}
FAR = {"en": "({km} km from {place})", "sw": "(km {km} kutoka {place})", "fr": "(à {km} km de {place})"}
FOOT = {"en": "WFP prices.", "sw": "Bei za WFP.", "fr": "Prix du PAM."}
TOP = {"en": "Latest WFP prices at {market}{far}:", "sw": "Bei za karibuni za WFP soko la {market}{far}:",
       "fr": "Derniers prix du PAM au marché de {market}{far} :"}
STAPLES = ("maize", "beans", "rice", "sorghum", "millet", "cassava", "wheat", "flour", "yam", "gari", "plantain", "teff",
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
THIN = {"en": "Recent WFP prices for {country} cover too few staple foods to be useful. Ask traders or your "
              "agriculture office.",
        "sw": "Bei za karibuni za WFP kwa {country} zinahusu vyakula vikuu vichache mno. Waulize wafanyabiashara au "
              "ofisi ya kilimo.",
        "fr": "Les prix récents du PAM pour {country} couvrent trop peu d'aliments de base pour être utiles. Demandez "
              "aux commerçants ou au service agricole."}
MIN_STAPLES = 2  # distinct staple foods with a recent price, below which a country's prices are a stated gap
NO_FOOD = {"en": "ACE has no recent WFP price for {food} near {place}.",
           "sw": "ACE haina bei ya karibuni ya WFP ya {food} karibu na {place}.",
           "fr": "ACE n'a pas de prix récent du PAM pour {food} près de {place}."}


def wanted_food(text: str) -> str | None:
    for phrase in FOOD_PHRASES:
        if contains_phrase(text, phrase):
            return FOODS[phrase]
    for tok in tokens(text):
        for form in word_forms(tok):
            if form in FOODS:
                return FOODS[form]
    return None


def staple_count(records: list[dict], today: date) -> int:
    """Distinct staple foods with a price recent enough to quote, across every market of a country."""
    found = set()
    for m in records:
        for item in m["items"]:
            if age_days(item["series"][-1][0], today) <= MAX_AGE_DAYS:
                name = fold(item["commodity"])
                found.update(word for word in STAPLES if word in name)
    return len(found)


def fmt_price(value: float) -> str:
    return f"{value:,.0f}" if value >= 100 else f"{value:,.2f}".rstrip("0").rstrip(".")


def age_days(month: str, today: date) -> int:
    y, m = (int(v) for v in month[:7].split("-"))
    return (today - date(y, m, 15)).days


class PricesService:
    id = "market_prices"
    title = {"en": "Market prices", "sw": "Bei za soko", "fr": "Prix du marché", "pt": "Preços no mercado",
             "ar": "أسعار السوق", "am": "የገበያ ዋጋ", "om": "Gatii gabaa", "so": "Qiimaha suuqa"}
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
        if staple_count(snap.records, date.today()) < MIN_STAPLES:
            return False, f"recent WFP prices cover fewer than {MIN_STAPLES} staple foods"
        return True, f"{len(snap.records)} markets, latest {month_year(snap.data_date, 'en')}"

    def answer(self, q: Query, ctx: Context) -> Result:
        country = (q.place.country if q.place else q.country) or ""
        if country and country not in SLUGS:
            return Refusal(self.id, "gap", {lang: say(GAP, lang, country=country_said(country, lang)) for lang in LANGS})
        if q.place is None and q.location is None:
            return needs_place(self.id, q.country)
        snap = ctx.snapshots.get("prices", country)
        if snap is None:
            return Refusal(self.id, "gap", {lang: say(GAP, lang, country=country_said(country, lang) if country else "")
                                            for lang in LANGS})
        today = q.now.date()
        if snap.data_date and age_days(snap.data_date, today) > MAX_AGE_DAYS:
            return Refusal(self.id, "stale", {lang: say(OLD, lang, country=country_said(country, lang),
                                                        month=month_year(snap.data_date, lang)) for lang in LANGS},
                           [cite_snapshot(snap)])
        if staple_count(snap.records, today) < MIN_STAPLES:
            return Refusal(self.id, "gap", {lang: say(THIN, lang, country=country_said(country, lang)) for lang in LANGS},
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
            where = place_name or country
            return Refusal(self.id, "no_match", {lang: say(NO_FOOD, lang, food=food_name(food or "", lang).lower(),
                                                           place=where) for lang in LANGS}, [cite_snapshot(snap)])
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
                values = dict(food=food_name(item["commodity"], lang), market=market["market"], currency=item["currency"],
                              price=fmt_price(price), unit=unit_name(item["unit"], lang), month=month_year(month, lang))
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
            text[lang] = fit([french(p) for p in pieces] if lang == "fr" else pieces, q.max_chars)
        return Answer(
            self.id, text, [cite_snapshot(snap)], confidence="high", data_date=snap.data_date,
            data={"country": country, "market": {k: market[k] for k in ("market", "admin1", "lat", "lon")},
                  "distance_km": round(km, 1), "items": shown})


i18n.localize("services.prices", globals(), ("LINE", "CHANGE", "ITEM", "FAR", "FOOT", "TOP", "OLD", "GAP", "THIN",
                                             "NO_FOOD", "UNIT", "UNIT_MANY", "LOCAL_FOOD", "LOCAL_DETAIL"))
