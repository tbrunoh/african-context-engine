"""The 34 countries ACE covers, and how a phone number tells us which one a caller is in.

One deployment can serve every covered country at once: the international
dialling code of the caller's number picks the country, so the emergency
numbers, packs and default language are always right for that caller.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    code: str               # ISO 3166-1 alpha-2
    name: str
    dial: str               # international dialling code without the plus
    languages: tuple[str, ...]  # languages ACE serves there, default first


COUNTRIES: dict[str, Country] = {c.code: c for c in (
    Country("KE", "Kenya", "254", ("en", "sw")),
    Country("TZ", "Tanzania", "255", ("sw", "en")),
    Country("UG", "Uganda", "256", ("en", "sw", "lg")),
    Country("RW", "Rwanda", "250", ("en", "fr", "rw")),
    Country("ZA", "South Africa", "27", ("en", "zu", "xh", "af", "st", "tn", "ts")),
    Country("BW", "Botswana", "267", ("en", "tn")),
    Country("NA", "Namibia", "264", ("en", "af")),
    Country("ZW", "Zimbabwe", "263", ("en", "sn")),
    Country("NG", "Nigeria", "234", ("en", "ha", "yo", "ig", "pcm")),
    Country("GH", "Ghana", "233", ("en", "ak", "ee")),
    Country("SN", "Senegal", "221", ("fr", "wo")),
    Country("CI", "Côte d'Ivoire", "225", ("fr", "dyu")),
    Country("TG", "Togo", "228", ("fr", "ee")),
    # Added in 2.1
    Country("CD", "DR Congo", "243", ("fr", "sw", "ln")),
    Country("MW", "Malawi", "265", ("en", "ny")),
    Country("BI", "Burundi", "257", ("fr", "sw", "rn")),
    Country("CM", "Cameroon", "237", ("fr", "en")),
    Country("BJ", "Benin", "229", ("fr", "yo")),
    Country("ZM", "Zambia", "260", ("en", "bem", "ny")),
    Country("TD", "Chad", "235", ("fr", "ar")),
    Country("GN", "Guinea", "224", ("fr", "fuf")),
    Country("BF", "Burkina Faso", "226", ("fr", "mos", "dyu")),
    Country("SS", "South Sudan", "211", ("en", "ar")),
    Country("ET", "Ethiopia", "251", ("am", "om", "so", "en", "ti")),
    Country("MZ", "Mozambique", "258", ("pt", "ts")),
    Country("GW", "Guinea-Bissau", "245", ("pt", "fr")),
    Country("AO", "Angola", "244", ("pt",)),
    Country("SO", "Somalia", "252", ("so", "ar", "en")),
    Country("SD", "Sudan", "249", ("ar", "en")),
    Country("DZ", "Algeria", "213", ("ar", "fr")),
    Country("EG", "Egypt", "20", ("ar", "en")),
    Country("LY", "Libya", "218", ("ar", "en")),
    Country("MA", "Morocco", "212", ("ar", "fr")),
    Country("TN", "Tunisia", "216", ("ar", "fr")),
)}

ISO3: dict[str, str] = {"KE": "KEN", "TZ": "TZA", "UG": "UGA", "RW": "RWA", "ZA": "ZAF", "BW": "BWA", "NA": "NAM",
                        "ZW": "ZWE", "NG": "NGA", "GH": "GHA", "SN": "SEN", "CI": "CIV", "TG": "TGO", "CD": "COD",
                        "MW": "MWI", "BI": "BDI", "CM": "CMR", "BJ": "BEN", "ZM": "ZMB", "TD": "TCD", "GN": "GIN",
                        "BF": "BFA", "SS": "SSD", "ET": "ETH", "MZ": "MOZ", "GW": "GNB", "AO": "AGO", "SO": "SOM",
                        "SD": "SDN", "DZ": "DZA", "EG": "EGY", "LY": "LBY", "MA": "MAR", "TN": "TUN"}
# The release each country joined, for docs and the coverage table.
ADDED_IN = {code: "1.1" for code in ("KE", "TZ", "UG", "RW", "ZA", "BW", "NA", "ZW", "NG", "GH", "SN", "CI", "TG")}
ADDED_IN.update({code: "2.1" for code in ISO3 if code not in ADDED_IN})

# Longest prefixes first, so "27" never shadows a longer code that starts with 27.
_BY_DIAL = sorted(COUNTRIES.values(), key=lambda c: -len(c.dial))


# ACE languages that people in a country often write from across a border, though the country's menus do not offer
# them: Somali and Afaan Oromo in Kenya, Hausa and Fula in Cameroon, isiNdebele readers of isiZulu in Zimbabwe.
# ACE reads a message in one of these and answers in it, and never tells its writer that it does not read it.
ALSO_READ: dict[str, tuple[str, ...]] = {
    "KE": ("so", "om", "lg"), "TZ": ("lg", "rw", "rn"), "UG": ("rw",), "RW": ("rn",), "BI": ("rw",),
    "CD": ("rw", "bem"), "CM": ("ha", "fuf", "ln"), "GH": ("ha",), "BJ": ("ee", "ha"), "TG": ("yo", "ak"),
    "SN": ("fuf",), "CI": ("mos",), "ZW": ("zu", "st", "tn", "ny", "ts"), "MZ": ("sw", "ny", "sn"),
    "BW": ("sn", "st"), "NA": ("tn",), "MW": ("zu", "sw"), "ZM": ("sw", "sn"), "ZA": ("sn", "ny"),
}


def readable(country_code: str | None) -> tuple[str, ...] | None:
    """The languages ACE reads for a caller in a country: those it offers there, then those from across a border,
    then English, which ACE reads in every country even where its menus do not offer it."""
    country = COUNTRIES.get(country_code or "")
    if country is None:
        return None
    extra = tuple(dict.fromkeys(c for c in (*ALSO_READ.get(country.code, ()), "en") if c not in country.languages))
    return country.languages + extra


def country_for_msisdn(msisdn: str) -> Country | None:
    """The covered country for an E.164 number, or None when it is outside ACE coverage."""
    digits = msisdn.lstrip("+")
    for country in _BY_DIAL:
        if digits.startswith(country.dial):
            return country
    return None


def default_language(country_code: str | None, fallback: str = "en") -> str:
    country = COUNTRIES.get((country_code or "").upper())
    return country.languages[0] if country else fallback
