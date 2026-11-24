"""The 13 countries ACE covers, and how a phone number tells us which one a caller is in.

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
)}

ISO3: dict[str, str] = {"KE": "KEN", "TZ": "TZA", "UG": "UGA", "RW": "RWA", "ZA": "ZAF", "BW": "BWA", "NA": "NAM",
                        "ZW": "ZWE", "NG": "NGA", "GH": "GHA", "SN": "SEN", "CI": "CIV", "TG": "TGO"}

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
