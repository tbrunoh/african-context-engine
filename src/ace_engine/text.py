"""Text utilities for short, noisy, code switched messages in every language ACE serves.

Messages to ACE are typed on feature phones, spoken into voice lines and
forwarded from mobile money inboxes. They mix languages, drop vowels and
skip punctuation. Everything here is deliberately simple, transparent and
dependency free so contributors can extend it for their own language.
"""
from __future__ import annotations

import re
import unicodedata

from . import i18n

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
        "nina una ana tuna mna wana kuna".split()
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
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
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


_ADDED_MARKERS = {code: frozenset(tokens(" ".join(ws))) for code, ws in i18n.words("markers").items()}
_SCRIPT_LANGUAGE = (("\u0600", "\u06ff", "ar"), ("\u1200", "\u137f", "am"))


def script_language(text: str) -> str | None:
    """The language a non Latin script points to: Arabic script to Arabic, Ge'ez to Amharic."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return None
    for lo, hi, code in _SCRIPT_LANGUAGE:
        if code in SUPPORTED_LANGUAGES and sum(lo <= c <= hi for c in letters) * 2 >= len(letters):
            return code
    return None


def guess_language(text: str, default: str = "en") -> str:
    """The language of a message: its script first, then marker word counts. Ties go to the default."""
    by_script = script_language(text)
    if by_script:
        return by_script
    toks = tokens(text)
    counts = {
        "sw": sum(t in _SW_MARKERS for t in toks),
        "en": sum(t in _EN_MARKERS for t in toks),
        "fr": sum(fold(t) in {fold(m) for m in _FR_MARKERS} for t in toks),
    }
    for code, markers in _ADDED_MARKERS.items():
        if code not in ("ar", "am"):
            counts[code] = sum(t in markers for t in toks)
    best = max(counts.values())
    if best == 0:
        return default
    winners = [lang for lang, n in counts.items() if n == best]
    return default if default in winners else winners[0] if len(winners) == 1 else default


def contains_phrase(haystack: str, phrase: str) -> bool:
    """Whole word phrase match on folded text, tolerant of punctuation and spacing."""
    hay = " " + " ".join(tokens(haystack)) + " "
    needle = " " + " ".join(tokens(phrase)) + " "
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

