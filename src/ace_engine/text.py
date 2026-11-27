"""Text utilities for short, noisy, code switched messages in every language ACE serves.

Messages to ACE are typed on feature phones, spoken into voice lines and
forwarded from mobile money inboxes. They mix languages, drop vowels and
skip punctuation. Everything here is deliberately simple, transparent and
dependency free so contributors can extend it for their own language.
"""
from __future__ import annotations

import re
import unicodedata
from functools import cache

from . import i18n
from .encoding import AFRICAN_LETTERS

# Letters and digits in any script, so Arabic, Ge'ez and Latin text all tokenise.
_TOKEN = re.compile(r"[^\W_]+")
SUPPORTED_LANGUAGES = i18n.all_languages()

STOPWORDS: dict[str, frozenset[str]] = {
    "en": frozenset(
        "a an the and or but if of to in on at for from by with about is are was were be been being "
        "i me my we our you your he she it its they them their this that these those what which who "
        "how when where why can could should would will do does did have has had not no so very "
        "just please hi hello help any some there here than then also too am".split()
    ),
    "sw": frozenset(
        "na ya wa kwa ni la za cha vya pa ku mu katika kwenye hii huu hiyo hizo ile hilo hapa pale "
        "mimi wewe yeye sisi nyinyi wao yangu yako yake yetu yenu yao je nini gani vipi lini wapi "
        "nani kama lakini au tu sana pia bado hata ndiyo hapana sasa habari jambo tafadhali naomba "
        "nina una ana tuna mna wana kuna wangu wako wake yuko kidogo".split()
    ),
    "fr": frozenset(
        "le la les un une des du de d l et ou mais si que qui quoi quel quelle quels comment quand ou "
        "pourquoi je j me m mon ma mes tu te ton ta tes il elle on nous vous ils elles leur leurs ce cet "
        "cette ces est sont suis es a ai as avons avez ont au aux en dans sur pour par avec sans pas ne "
        "plus tres bonjour salut merci svp sil vous plait faire fait dois peux".split()
    ),
}

for _code, _words in i18n.words("stopwords").items():
    STOPWORDS[_code] = _words

# Words that are frequent in Swahili text and rare in English text. Used only
# for a light language guess when the channel does not tell us the language.
_SW_MARKERS = frozenset(
    "na ya wa kwa ni za katika kwenye hii yangu yako yake nini gani vipi lini wapi je sana pia "
    "habari jambo tafadhali naomba nina kuna mtoto mama shamba mahindi pesa mgonjwa damu "
    "msaada asante sijui nifanye nisaidie nataka ninataka mimi wewe yeye sisi leo jana kesho hapa "
    "mke mume mwanangu mjamzito hospitali mvua bei soko homa anaumwa naumwa".split()
)
_FR_MARKERS = frozenset(
    "le les des du est sont je mon mes vous nous que qui quoi comment pourquoi avec pour dans "
    "pas bonjour merci enceinte enfant argent malade sang aide maïs mais champ chenille "
    "fille fils femme mari bebe mere pere aidez hier maintenant veux suis besoin tres".split()
)
_EN_MARKERS = frozenset(
    "the and is are my what how when where why please help with have this that your "
    "maize child money sick blood thank".split()
)


ACTION_CUES_BUILT_IN = (
    "what do i do", "what should i do", "what can i do", "how do i stop", "how to stop", "how do i control",
    "how to control", "how to kill", "get rid", "how do i prevent", "how to prevent", "how do i store",
    "how to store", "what to do", "help me", "nifanye", "nifanye nini", "nini kifanyike", "jinsi ya kuzuia",
    "nitazuia", "nitaua", "jinsi ya kuua", "jinsi ya kuhifadhi", "nisaidie", "nichukue hatua",
    "que faire", "que dois je faire", "comment lutter", "comment eviter", "comment proteger",
    "comment conserver", "comment tuer", "aidez moi",
)


ACTION_CUES = i18n.phrases("text.ACTION_CUES", ACTION_CUES_BUILT_IN)


def wants_action(text: str) -> bool:
    """True when a message asks what to do rather than what something is."""
    return any(contains_phrase(text, cue) for cue in ACTION_CUES)


# Arabic letters people type interchangeably, folded to one form: alef with hamza or madda to bare alef, alef
# maqsura to ya, ta marbuta to ha. Tatweel (the stretching stroke) is dropped.
_ARABIC = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ـ": None, "ؤ": "و", "ئ": "ي",
                         **{chr(0x0660 + i): str(i) for i in range(10)}, **{chr(0x06F0 + i): str(i) for i in range(10)}})
# Ge'ez letter families that sound the same in Amharic and are typed interchangeably, folded to one family:
# ሐ and ኀ to ሀ, ሠ to ሰ, ዐ to አ, ፀ to ጸ. Each family is eight code points, one per vowel order.
_ETHIOPIC = {0x1210: 0x1200, 0x1280: 0x1200, 0x1220: 0x1230, 0x12D0: 0x12A0, 0x1340: 0x1338}
_ETHIOPIC_MAP = {base + i: target + i for base, target in _ETHIOPIC.items() for i in range(8)}
# Clitics Arabic writes joined to the next word: wa (and), the article al and its forms with bi, li, fa, ka.
_AR_PREFIX = re.compile(r"^(?:و)?(?:بال|لل|فال|كال|وال|ال)(?=\w{2,})|^و(?=\w{3,})")


def fold(text: str) -> str:
    """Lowercase, strip accents and harmonise letter forms so typing differences do not matter."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(AFRICAN_LETTERS.get(c, c) for c in text if not unicodedata.combining(c)).lower()
    if any("\u0600" <= c <= "\u06ff" for c in text):
        text = text.translate(_ARABIC)
    if any("\u1200" <= c <= "\u137f" for c in text):
        text = text.translate(_ETHIOPIC_MAP)
    return text


def _arabic_stem(token: str) -> str:
    return _AR_PREFIX.sub("", token) if "\u0600" <= token[:1] <= "\u06ff" else token


def tokens(text: str) -> list[str]:
    return [_arabic_stem(t) for t in _TOKEN.findall(fold(text))]


def stem(token: str) -> str:
    """A tiny, conservative suffix stripper for English plurals and verb forms.

    Swahili inflects mainly with prefixes, so we leave Swahili tokens alone and
    rely on pack keywords to list common forms.
    """
    for suffix in ("ing", "ies", "es", "ed", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            base = token[: -len(suffix)]
            return base + "y" if suffix == "ies" else base
    return token


_ALL_STOP = frozenset().union(*({fold(w) for w in ws} for ws in STOPWORDS.values()))


def terms(text: str, drop_stopwords: bool = True) -> list[str]:
    """Index and query terms: folded tokens, stopwords removed, lightly stemmed."""
    stop = _ALL_STOP if drop_stopwords else frozenset()
    return [stem(t) for t in tokens(text) if t not in stop and len(t) > 1]


# A marker counts only as one whole word: a marker such as "b'a" would split into "b" and "a", and "a" is in
# every French sentence.
_ADDED_MARKERS = {code: frozenset(t[0] for t in (tokens(w) for w in ws) if len(t) == 1)
                  for code, ws in i18n.words("markers").items()}
_MARKERS: dict[str, frozenset[str]] = {"sw": _SW_MARKERS, "en": _EN_MARKERS,
                                       "fr": frozenset(fold(m) for m in _FR_MARKERS), **_ADDED_MARKERS}
# Scripts that point to a language on their own. Ge'ez is written for Amharic and Tigrinya, so marker words
# choose between them; Amharic wins a tie, as the language most people who type Ge'ez read.
_SCRIPTS = (("\u0600", "\u06ff", ("ar",)), ("\u1200", "\u137f", ("am", "ti")))


# A language that shares most of its words with another, as Nigerian Pidgin does with English, counts each of its
# own marker words more, so a message with one Pidgin word among common English ones still reads as Pidgin.
_MARKER_WEIGHT = {code: int(loc.meta.get("marker_weight", 1)) for code, loc in i18n.locales().items()}


def _marker_counts(toks: list[str], candidates) -> dict[str, int]:
    return {code: _MARKER_WEIGHT.get(code, 1) * sum(t in _MARKERS.get(code, ()) for t in toks) for code in candidates}


def script_language(text: str, allowed: tuple[str, ...] | None = None) -> str | None:
    """The language a non Latin script points to: Arabic script to Arabic, Ge'ez to Amharic or Tigrinya.

    Script is evidence on its own, so it is not limited to the caller's country: an Amharic message from a
    Kenyan number is still Amharic. Among the languages a script serves, the caller's languages come first."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return None
    for lo, hi, codes in _SCRIPTS:
        codes = tuple(c for c in codes if c in SUPPORTED_LANGUAGES)
        if not codes or sum(lo <= c <= hi for c in letters) * 2 < len(letters):
            continue
        if len(codes) == 1:
            return codes[0]
        preferred = tuple(c for c in codes if allowed is None or c in allowed) or codes
        counts = _marker_counts(tokens(text), preferred)
        best = max(counts.values())
        winners = [c for c in preferred if counts[c] == best]
        return winners[0]
    return None


def has_marker(text: str, allowed: tuple[str, ...] | None = None) -> bool:
    """True when any marker word of a Latin script language (among allowed, when given) is in the text."""
    latin = [c for c in SUPPORTED_LANGUAGES if c not in ("ar", "am", "ti") and (allowed is None or c in allowed)]
    return any(_marker_counts(tokens(text), latin).values())


def guess_language(text: str, default: str = "en", allowed: tuple[str, ...] | None = None) -> str:
    """The language of a message: its script first, then marker word counts. Ties go to the default.

    A tie between two languages that are not the default goes to the one the caller's country lists first.

    With ``allowed`` (the languages ACE serves in the caller's country), marker words only choose among those
    languages, so a short English question from Kenya is never read as Portuguese because it shares a word
    with Portuguese. A caller can still switch to any language with LANG and a code."""
    by_script = script_language(text, allowed)
    if by_script:
        return by_script
    toks = tokens(text)
    latin = [c for c in SUPPORTED_LANGUAGES if c not in ("ar", "am", "ti")]
    candidates = [c for c in latin if allowed is None or c in allowed]
    counts = _marker_counts(toks, candidates)
    best = max(counts.values(), default=0)
    if best == 0:
        # English is not offered everywhere, but a message plainly in English (two English marker words and none
        # from the country's languages) still gets an English reply rather than one its writer may not read.
        if allowed and "en" not in candidates and _marker_counts(toks, ("en",))["en"] >= 2:
            return "en"
        return default
    winners = [lang for lang, n in counts.items() if n == best]
    if default in winners:
        return default
    if len(winners) == 1 or not allowed:
        return winners[0] if len(winners) == 1 else default
    # Close languages of one country, such as Sesotho and Setswana, share words; a tie between them goes to the
    # one the country lists first, which its speakers read, rather than to a default neither of them wrote in.
    return next(lang for lang in allowed if lang in winners)


def contains_phrase(haystack: str, phrase: str) -> bool:
    """Whole word phrase match on folded text, tolerant of punctuation and spacing."""
    return phrase_in(token_hay(haystack), phrase)


def token_hay(text: str) -> str:
    """A message folded and tokenised once, ready for many phrase checks with phrase_in."""
    return " " + " ".join(tokens(text)) + " "


@cache
def _needle(phrase: str) -> str:
    return " " + " ".join(tokens(phrase)) + " "


def phrase_in(hay: str, phrase: str) -> bool:
    """contains_phrase on a hay from token_hay. Phrases are tokenised once and cached, so the safety rail checks
    thousands of phrases in every language without re-reading the message for each one."""
    needle = _needle(phrase)
    return needle.strip() != "" and needle in hay


def truncate_words(text: str, limit: int, suffix: str = "...") -> str:
    """Cut text at a word boundary so it fits within limit characters."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[: max(0, limit - len(suffix))]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;:") + suffix


ETHIOPIC_PREFIXES = "የበለከ"  # of, in, for, from: የበቆሎ ዋጋ is the price of maize
SOMALI_ENDINGS = ("da", "ta", "ka", "ga", "ha")  # the definite article: galleyda is the maize


def word_forms(tok: str) -> list[str]:
    """A word and the bare forms people attach to it: an Amharic preposition prefix or a Somali definite ending.

    Used where a service looks for a named thing (a food, a crop), so the price of maize finds maize in every
    language. Retrieval does not use it, because a stripped form can collide with another word."""
    out = [tok]
    if len(tok) > 2 and tok[0] in ETHIOPIC_PREFIXES:
        out.append(tok[1:])
    out += [tok[:-2] for end in SOMALI_ENDINGS if tok.endswith(end) and len(tok) > 4]
    return out


def token_forms(text: str) -> set[str]:
    return {form for tok in tokens(text) for form in word_forms(tok)}

