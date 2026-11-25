"""Languages beyond the three ACE was built in, loaded from one plain file per language.

English, Swahili and French live in the code next to the rules they belong to. Every other language lives in
``ace_engine/locales/<code>.yaml``: its replies (templates), the words that trigger the safety rail and the
services (phrases), and the small word lists the text tools need (words). Adding a language is adding one file:
nothing else in the engine changes, and the completeness test fails until every template has a rendering.

A locale file says whether a fluent speaker has reviewed it. Unreviewed languages work, and ACE serves them,
but ``ace packs validate --strict`` and the release notes list them until review, exactly as for unreviewed pack
translations. Safety phrases are additive only: a locale can widen what the rail catches, never narrow it.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

BUILT_IN = ("en", "sw", "fr")
LOCALE_DIR = Path(__file__).parent / "locales"
# The order languages appear in menus and docs after the three built in.
ORDER = ("pt", "ar", "am", "om", "so")


@dataclass(frozen=True)
class Locale:
    code: str
    name: str              # the language's English name
    native: str            # the language's own name, as a menu shows it
    script: str            # ISO 15924: Latn, Arab, Ethi
    encoding: str          # gsm7 (Latin text folded to the GSM alphabet) or ucs2
    direction: str         # ltr or rtl
    reviewed: bool
    templates: Mapping[str, Any]
    phrases: Mapping[str, Any]
    words: Mapping[str, Any]
    meta: Mapping[str, Any]

    @property
    def confirm(self) -> str:
        return str(self.meta.get("confirm", ""))

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self.meta.get("names") or ())


@lru_cache(maxsize=1)
def locales() -> dict[str, Locale]:
    found: dict[str, Locale] = {}
    for path in sorted(LOCALE_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        meta = data.get("meta") or {}
        code = meta.get("code") or path.stem
        found[code] = Locale(code=code, name=meta["name"], native=meta["native"], script=meta.get("script", "Latn"),
                             encoding=meta.get("encoding", "gsm7"), direction=meta.get("direction", "ltr"),
                             reviewed=bool(meta.get("reviewed", False)), templates=data.get("templates") or {},
                             phrases=data.get("phrases") or {}, words=data.get("words") or {}, meta=meta)
    ordered = {c: found[c] for c in ORDER if c in found}
    ordered.update({c: v for c, v in found.items() if c not in ordered})
    return ordered


def added_languages() -> tuple[str, ...]:
    return tuple(locales())


def all_languages() -> tuple[str, ...]:
    return BUILT_IN + added_languages()


NATIVE_NAMES = {"en": "English", "sw": "Kiswahili", "fr": "Français"}
ENGLISH_NAMES = {"en": "English", "sw": "Swahili", "fr": "French"}


def native_name(code: str) -> str:
    loc = locales().get(code)
    return loc.native if loc else NATIVE_NAMES.get(code, code)


def english_name(code: str) -> str:
    loc = locales().get(code)
    return loc.name if loc else ENGLISH_NAMES.get(code, code)


def is_ucs2(code: str) -> bool:
    """True for languages whose script is outside the GSM alphabet, so SMS and USSD carry fewer characters."""
    loc = locales().get(code)
    return bool(loc and loc.encoding == "ucs2")


def unreviewed() -> list[str]:
    return [c for c, loc in locales().items() if not loc.reviewed]


def template(path: str, code: str) -> Any:
    loc = locales().get(code)
    return None if loc is None else loc.templates.get(path)


def localize(prefix: str, namespace: Mapping[str, Any], names: Iterable[str] | None = None) -> None:
    """Fill every per language dict in a module with the added languages.

    A per language dict is any dict with an "en" key. Its path is the module prefix and the chain of keys, for
    example ``services.rain.WORDS.likely``. Dicts are filled in place, so every reference to them sees the new
    languages. A missing rendering is left out, and the completeness test reports it.
    """
    for name in names or list(namespace):
        value = namespace[name]
        if isinstance(value, dict):
            _fill(value, f"{prefix}.{name}")


def _fill(d: dict, path: str) -> None:
    if "en" in d and all(isinstance(k, str) for k in d):
        for code, loc in locales().items():
            if code not in d and path in loc.templates:
                d[code] = _freeze(loc.templates[path], d["en"])
        return
    for key, value in d.items():
        if isinstance(value, dict) and isinstance(key, (str, int)):
            _fill(value, f"{path}.{getattr(key, 'name', key)}")


def _freeze(value: Any, like: Any) -> Any:
    """Match the container type of the English value: tuples stay tuples, sets stay sets."""
    if isinstance(like, tuple) and isinstance(value, list):
        return tuple(value)
    if isinstance(like, (set, frozenset)) and isinstance(value, list):
        return type(like)(value)
    return value


def phrases(path: str, base: Iterable[str]) -> tuple[str, ...]:
    """A phrase group widened with every added language's phrases for it. Order is kept, duplicates dropped."""
    out = list(base)
    for loc in locales().values():
        out.extend(loc.phrases.get(path) or ())
    return tuple(dict.fromkeys(out))


def phrase_map(path: str, base: Mapping[str, str]) -> dict[str, str]:
    """A word to meaning map (for example a food word to its canonical name) widened with every added language."""
    out = dict(base)
    for loc in locales().values():
        out.update(loc.phrases.get(path) or {})
    return out


def words(kind: str) -> dict[str, frozenset[str]]:
    """Per language word lists from the locale files, such as stopwords and language markers."""
    return {code: frozenset(loc.words.get(kind) or ()) for code, loc in locales().items()}


def missing() -> dict[str, list[str]]:
    """Per language dicts that lack an added language, for tests and ``ace packs validate --strict``."""
    from importlib import import_module
    found: dict[str, dict] = {}
    for module in TEMPLATE_MODULES:
        mod = import_module(f"ace_engine.{module}")
        for name, value in vars(mod).items():
            if isinstance(value, dict):
                _paths(value, f"{module}.{name}", found)
    return {code: sorted(p for p, d in found.items() if code not in d) for code in locales()}


def _paths(d: dict, path: str, out: dict[str, dict]) -> None:
    if "en" in d and all(isinstance(k, str) for k in d) and ("sw" in d or "fr" in d):
        out[path] = d
        return
    for key, value in d.items():
        if isinstance(value, dict) and isinstance(key, (str, int)):
            _paths(value, f"{path}.{getattr(key, 'name', key)}", out)


TEMPLATE_MODULES = ("safety", "commands", "scam", "channels.ussd", "channels.voice", "services.base",
                    "services.rain", "services.warnings", "services.facility", "services.prices",
                    "services.pregnancy", "services.pests")
