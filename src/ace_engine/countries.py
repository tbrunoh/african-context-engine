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
    Country("UG", "Uganda", "256", ("en", "sw")),
    Country("RW", "Rwanda", "250", ("en", "fr")),
    Country("ZA", "South Africa", "27", ("en",)),
    Country("BW", "Botswana", "267", ("en",)),
    Country("NA", "Namibia", "264", ("en",)),
    Country("ZW", "Zimbabwe", "263", ("en",)),
    Country("NG", "Nigeria", "234", ("en",)),
    Country("GH", "Ghana", "233", ("en",)),
    Country("SN", "Senegal", "221", ("fr",)),
    Country("CI", "Côte d'Ivoire", "225", ("fr",)),
    Country("TG", "Togo", "228", ("fr",)),
    # Added in 2.1
    Country("CD", "DR Congo", "243", ("fr", "sw")),
    Country("MW", "Malawi", "265", ("en",)),
    Country("BI", "Burundi", "257", ("fr", "sw")),
    Country("CM", "Cameroon", "237", ("fr", "en")),
    Country("BJ", "Benin", "229", ("fr",)),
    Country("ZM", "Zambia", "260", ("en",)),
    Country("TD", "Chad", "235", ("fr", "ar")),
    Country("GN", "Guinea", "224", ("fr",)),
    Country("BF", "Burkina Faso", "226", ("fr",)),
    Country("SS", "South Sudan", "211", ("en", "ar")),
    Country("ET", "Ethiopia", "251", ("am", "om", "so", "en")),
    Country("MZ", "Mozambique", "258", ("pt",)),
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
