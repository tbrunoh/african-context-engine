"""Text utilities for short, noisy, code switched messages in English, Swahili and French.

Messages to ACE are typed on feature phones, spoken into voice lines and
forwarded from mobile money inboxes. They mix languages, drop vowels and
skip punctuation. Everything here is deliberately simple, transparent and
dependency free so contributors can extend it for their own language.
"""
from __future__ import annotations

import re
import unicodedata

_TOKEN = re.compile(r"[a-z0-9]+")
SUPPORTED_LANGUAGES = ("en", "sw", "fr")

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

# Words that are frequent in Swahili text and rare in English text. Used only
# for a light language guess when the channel does not tell us the language.
_SW_MARKERS = frozenset(
    "na ya wa kwa ni za katika kwenye hii yangu yako yake nini gani vipi lini wapi je sana pia "
    "habari jambo tafadhali naomba nina kuna mtoto mama shamba mahindi pesa mgonjwa damu "
    "msaada asante sijui nifanye nisaidie".split()
)
_FR_MARKERS = frozenset(
    "le les des du est sont je mon ma mes vous nous que qui quoi comment pourquoi avec pour dans "
    "pas bonjour merci enceinte enfant argent malade sang aide maïs mais champ chenille".split()
)
_EN_MARKERS = frozenset(
    "the and is are my what how when where why please help with have this that your "
    "maize child money sick blood thank".split()
)


ACTION_CUES = (
    "what do i do", "what should i do", "what can i do", "how do i stop", "how to stop", "how do i control",
    "how to control", "how to kill", "get rid", "how do i prevent", "how to prevent", "how do i store",
    "how to store", "what to do", "help me", "nifanye", "nifanye nini", "nini kifanyike", "jinsi ya kuzuia",
    "nitazuia", "nitaua", "jinsi ya kuua", "jinsi ya kuhifadhi", "nisaidie", "nichukue hatua",
    "que faire", "que dois je faire", "comment lutter", "comment eviter", "comment proteger",
    "comment conserver", "comment tuer", "aidez moi",
)


def wants_action(text: str) -> bool:
    """True when a message asks what to do rather than what something is."""
    return any(contains_phrase(text, cue) for cue in ACTION_CUES)


def fold(text: str) -> str:
    """Lowercase and strip accents so that typing differences do not matter."""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(fold(text))


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


def terms(text: str, drop_stopwords: bool = True) -> list[str]:
    """Index and query terms: folded tokens, stopwords removed, lightly stemmed."""
    stop = STOPWORDS["en"] | STOPWORDS["sw"] | STOPWORDS["fr"] if drop_stopwords else frozenset()
    return [stem(t) for t in tokens(text) if t not in stop and len(t) > 1]


def guess_language(text: str, default: str = "en") -> str:
    """Return "en", "sw" or "fr" from marker word counts. Ties go to the default."""
    toks = tokens(text)
    counts = {
        "sw": sum(t in _SW_MARKERS for t in toks),
        "en": sum(t in _EN_MARKERS for t in toks),
        "fr": sum(fold(t) in {fold(m) for m in _FR_MARKERS} for t in toks),
    }
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
