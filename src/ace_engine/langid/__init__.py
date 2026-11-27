"""Telling a language ACE speaks from one it does not.

ACE guesses a message's language from marker words, and only among the languages of the caller's country, so a
message in a language ACE does not speak is still read as one of those. A Gikuyu message from Kenya reads as
Swahili, and the reply comes in a language its writer may not read. This module compares the message with
character profiles of ACE's languages and of languages ACE does not speak but its callers do. When a message is
plainly closer to one of those, ACE says that it does not read that language yet and names the languages it does
read in the caller's country, instead of answering in the wrong one.

The profiles are counts of three letter sequences in folded text (see benchmark/langid/build.py for how they are
built, and from what). profiles.json is shared under CC BY-SA 4.0, because one of its sources is.

The safety rail always runs first, and the reply that says ACE does not read a language also gives the caller's
emergency numbers, so a person in danger who writes in any language still gets them.
"""
from __future__ import annotations

import json
import math
import re
import threading
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Protocol

from ..text import _MARKERS, fold, guess_language, has_marker, script_language, tokens

_LETTERS = re.compile(r"[^\W\d_]+")
PROFILES = Path(__file__).with_name("profiles.json")
# A message must hold this many three letter sequences, often four or five words, after names, places and links are
# removed, before ACE judges its language: a
# greeting or a single word is too short to tell.
MIN_GRAMS = 24
# How much closer, per sequence on average, the message must be to a language ACE does not speak than to the best
# language ACE offers in the caller's country. Set on WAXAL's validation split; WAXAL's test split stays held out.
MARGIN = 0.4
_VOCABULARY = 60000  # smoothing: about the number of distinct sequences across all profiles


def grams(text: str) -> list[str]:
    """The three letter sequences of a text, each word padded with a space on both sides, after folding."""
    out: list[str] = []
    for word in _LETTERS.findall(fold(text)):
        padded = f" {word} "
        out.extend(padded[i:i + 3] for i in range(len(padded) - 2))
    return out


@cache
def profiles() -> dict[str, dict]:
    return json.loads(PROFILES.read_text(encoding="utf-8"))["languages"]


def _score(gs: list[str], prof: dict) -> float:
    counts, total = prof["grams"], prof["total"]
    denominator = math.log(total + 0.5 * _VOCABULARY)
    return sum(math.log(counts.get(g, 0) + 0.5) - denominator for g in gs) / len(gs)


# A message with no marker word at all is read by its character profile, among the caller's country languages,
# when it is long enough and one language is clearly closest. Set on FLORES-200 dev and WAXAL validation.
PICK_GRAMS = 16
PICK_MARGIN = 0.1


def closest_offered(text: str, offered: tuple[str, ...] | None) -> str | None:
    """The language among offered a message is clearly closest to by its letters, or None when it is unclear."""
    langs = profiles()
    ours = [c for c in (offered or ()) if c in langs]
    gs = grams(text)
    if len(ours) < 2 or len(gs) < PICK_GRAMS:
        return None
    scores = sorted(((_score(gs, langs[c]), c) for c in ours), reverse=True)
    return scores[0][1] if scores[0][0] - scores[1][0] >= PICK_MARGIN else None


def detect_language(text: str, default: str = "en", allowed: tuple[str, ...] | None = None,
                    also: tuple[str, ...] = (), ignore: frozenset[str] = frozenset()) -> str:
    """The language of a message: its script, then its marker words, then, when it has no marker word at all,
    the closest character profile among the caller's country languages and the ACE languages written there from
    across a border (also, see countries.ALSO_READ). Marker words always win when present.

    The letters are read after names, links and the country's place names (ignore) are removed, so Kakamega
    hospital from Kenya is never answered in Afaan Oromo because Kakamega has Oromo letters."""
    if script_language(text, allowed):
        return guess_language(text, default, allowed)
    # Marker words are read without the country's place names, so Homa Bay is not Swahili because homa is.
    words = content(text, ignore, names=False) or text
    guess = guess_language(words, default, allowed)
    if guess != default or has_marker(words, allowed):
        return guess
    if not allowed:
        return default
    # Judge the words that show a language: a message that is mostly place names keeps the country's default.
    # Arabic written in Latin letters, as in ana 3ayez a3raf, has no profile, so where Arabic is offered a message with
    # no marker word keeps the country's default, as before letters were read, rather than going to English or French.
    if "ar" in allowed:
        return default
    return closest_offered(content(text, ignore), (*allowed, *also)) or default


@dataclass(frozen=True)
class Unread:
    """A message in a language ACE does not speak: its code and own name, when ACE can tell which one."""
    code: str
    name: str
    margin: float


# Links, addresses and numbers carry no language, and names of people and places are shared across languages: a list
# of Kenyan towns is not Gikuyu. They are removed before a message is judged.
_LINKS = re.compile(r"(?:https?://|www\.)\S+|\S+@\S+|\b\S+\.(?:com|org|net|ly|me|co|io|info|biz|africa)\b\S*",
                    re.IGNORECASE)
_WORD = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*")
_SENTENCE_END = ".!?:;\n"
# Countries where ACE offers a language whose speakers often write it in Latin letters, Arabic as Arabizi and Amharic
# or Tigrinya in Latin transliteration. A Latin message there may be one of ACE's languages that no profile covers,
# so ACE never turns a message away in those countries.
_TRANSLITERATED = ("ar", "am", "ti")
# Messages with two or more marker words of English, French or Portuguese, the languages most callers mix in, are
# never turned away. Marker words of African languages do not count, because neighbouring languages share them.
_LINGUA_FRANCA = ("en", "fr", "pt")


def content(text: str, ignore: frozenset[str] = frozenset(), names: bool = True) -> str:
    """The words of a message that can show its language: no links, numbers, names or places.

    A capitalised word that does not start a sentence is taken as a name, unless most words are in capitals,
    and any word in ignore (folded place names of the caller's country) is dropped. With names False, capitalised
    words are kept and only links, numbers and place names go."""
    text = _LINKS.sub(" ", text)
    words = list(_WORD.finditer(text))
    shouting = sum(len(w.group(0)) > 1 and w.group(0).isupper() for w in words) * 2 > len(words)
    kept: list[str] = []
    for w in words:
        word = w.group(0)
        before = text[:w.start()].rstrip()
        starts_sentence = not before or before[-1] in _SENTENCE_END
        if names and not shouting and word[:1].isupper() and not starts_sentence:
            continue
        if fold(word) in ignore:
            continue
        kept.append(word)
    return " ".join(kept)


def carries_language(text: str, ignore: frozenset[str] = frozenset()) -> bool:
    """True when a message holds enough of its own words to show a language: a marker word, or enough letters once
    names and places are removed. A bare place name, such as a county given in answer to ACE's question, does not."""
    words = content(text, ignore)
    return has_marker(words) or len(grams(words)) >= PICK_GRAMS


def unread_language(text: str, offered: tuple[str, ...] | None = None,
                    ignore: frozenset[str] = frozenset(), also: tuple[str, ...] = ()) -> Unread | None:
    """The language ACE does not speak that a message is written in, or None when ACE should read it.

    offered is the list of languages ACE serves in the caller's country, also the ACE languages written there from
    across a border, which count as ACE's own, and ignore the folded place names of that country. Text mostly
    outside Latin script is left to the script check: Arabic script is Arabic, and Ge'ez is Amharic or Tigrinya."""
    if offered and any(code in offered for code in _TRANSLITERATED):
        return None
    letters = [c for c in text if c.isalpha()]
    if not letters or sum(c.isascii() or "\u00c0" <= c <= "\u024f" or "\u1e00" <= c <= "\u1eff" or c in "ɓɗƙƴɛɔŋɖƒɣʋɩʊɲ"
                          for c in letters) * 2 < len(letters):
        return None
    toks = tokens(text)
    if any(sum(t in _MARKERS.get(code, ()) for t in toks) >= 2 for code in _LINGUA_FRANCA):
        return None
    gs = grams(content(text, ignore))
    if len(gs) < MIN_GRAMS:
        return None
    langs = profiles()
    ours = [c for c in (*(offered or ()), *also) if c in langs] or [c for c, p in langs.items() if p["ace"]]
    best_ours = max(_score(gs, langs[c]) for c in ours)
    others = {c: _score(gs, p) for c, p in langs.items() if not p["ace"]}
    code = max(others, key=others.get)
    margin = others[code] - best_ours
    return Unread(code, langs[code]["name"], round(margin, 3)) if margin > MARGIN else None


# ------------------------------------------------------------------ optional providers

class LanguageIdentifier(Protocol):
    """A fuller language identifier an operator can plug in, such as Cloud Translation's detectLanguage or GlotLID.

    ACE asks it only to confirm a message its own check would turn away, so it costs one call for those messages
    and none for the rest. It returns (ACE or ISO 639 code, confidence) pairs, most likely first."""

    def identify(self, text: str) -> list[tuple[str, float]]: ...


# ISO 639-3 and FLORES style codes for ACE's languages, so any identifier's answer maps onto ACE's codes. Every Fula
# variety maps to Pular, the Fula ACE writes, and Twi and Fante to Akan.
TO_ACE = {
    "eng": "en", "fra": "fr", "por": "pt", "swh": "sw", "swa": "sw", "arb": "ar", "ara": "ar", "amh": "am",
    "gaz": "om", "orm": "om", "som": "so", "hau": "ha", "yor": "yo", "ibo": "ig", "pcm": "pcm", "zul": "zu",
    "xho": "xh", "afr": "af", "sot": "st", "tsn": "tn", "tso": "ts", "sna": "sn", "nya": "ny", "bem": "bem",
    "kin": "rw", "run": "rn", "lug": "lg", "lin": "ln", "aka": "ak", "twi": "ak", "fat": "ak", "ewe": "ee",
    "wol": "wo", "dyu": "dyu", "mos": "mos", "fuf": "fuf", "fuv": "fuf", "fuc": "fuf", "ful": "fuf", "ff": "fuf",
    "tir": "ti", "swc": "sw",
    # Close neighbours whose speakers read an ACE language, as the profiles leave them out
    "bam": "dyu", "bm": "dyu", "emk": "dyu", "nde": "zu", "nd": "zu", "nbl": "zu", "nr": "zu", "kri": "pcm",
    "tum": "ny",
    # Arabic varieties
    "ary": "ar", "arz": "ar", "aeb": "ar", "arq": "ar", "apd": "ar", "ayl": "ar", "acm": "ar", "apc": "ar",
    "ajp": "ar", "acq": "ar", "ars": "ar", "shu": "ar",
}


def to_ace(code: str) -> str:
    """An identifier's language code as ACE's code: fuf_Latn, fuv or ff to fuf, sw-KE to sw, kin to rw."""
    base = code.replace("__label__", "").split("_")[0].split("-")[0].lower()
    return TO_ACE.get(base, base)


IDENTIFIER_DEADLINE = 3.0  # seconds a person may wait for a plugged in identifier, credentials included


def confirmed_by(identifier: LanguageIdentifier | None, text: str, offered: tuple[str, ...] | None,
                 deadline: float = IDENTIFIER_DEADLINE) -> bool:
    """False when a plugged in identifier says, with at least even confidence, that the message is in a language
    ACE offers the caller: then ACE answers instead of turning the message away. True otherwise, including when the
    identifier fails or takes longer than the deadline: then ACE's own check stands, so a slow provider never
    keeps a person waiting."""
    if identifier is None:
        return True
    box: dict[str, list[tuple[str, float]]] = {}

    def ask() -> None:
        try:
            box["found"] = identifier.identify(text)
        except Exception:  # an outage: ACE's own check stands
            pass

    # A daemon thread, so a provider that never answers can neither keep the person waiting nor hold the server open.
    worker = threading.Thread(target=ask, name="ace-langid", daemon=True)
    worker.start()
    worker.join(deadline)
    if "found" not in box:
        return True
    found = box["found"]
    if not found:
        return True
    code, confidence = found[0]
    return not (to_ace(code) in (offered or ()) and confidence >= 0.5)


class GlotLID:
    """GlotLID (Apache 2.0), an open fastText model of more than 2,000 languages, run on the operator's own server.

    It needs `pip install fasttext` and the model file (about 1.7 GB) downloaded once from the GlotLID page on
    Hugging Face; ACE does not ship or download it."""

    def __init__(self, model_path: str, k: int = 3) -> None:
        import fasttext  # optional dependency, imported only when GlotLID is used

        self.model = fasttext.load_model(model_path)
        self.k = k

    def identify(self, text: str) -> list[tuple[str, float]]:
        labels, scores = self.model.predict(" ".join(text.split()), k=self.k)
        return [(str(label), float(score)) for label, score in zip(labels, scores, strict=False)]
