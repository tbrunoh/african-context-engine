"""Keyword commands that work the same on SMS, WhatsApp, USSD free text and the API.

Commands are recognised only by their first word, in English or Swahili, so
ordinary questions are never mistaken for commands. The safety rail always
runs before commands: HELP followed by an emergency is still an emergency.
"""
from __future__ import annotations

from dataclasses import dataclass

from .text import fold

COMMANDS: dict[str, tuple[str, ...]] = {
    "help": ("help", "msaada", "menu", "menyu", "start", "anza"),
    "forget": ("forget", "futa", "delete"),
    "stop": ("stop", "acha", "sitisha"),
    "language": ("lang", "language", "lugha"),
    "english": ("english", "kiingereza"),
    "swahili": ("swahili", "kiswahili"),
    "tip": ("tip", "dokezo", "ushauri"),
    "scam": ("scam", "utapeli", "fraud"),
    "sources": ("sources", "source", "vyanzo", "chanzo"),
    "more": ("more", "zaidi", "next", "endelea"),
}
_LOOKUP = {word: name for name, words in COMMANDS.items() for word in words}
# Commands that must be the whole message, so a question that starts with the
# word is still treated as a question ("check my maize for armyworm").
_BARE_ONLY = {"help", "forget", "stop", "english", "swahili", "sources", "more"}


@dataclass(frozen=True)
class Command:
    name: str
    arg: str = ""


def parse_command(text: str) -> Command | None:
    stripped = text.strip()
    if not stripped:
        return None
    first, _, rest = stripped.partition(" ")
    name = _LOOKUP.get(fold(first).strip(".,!?:;"))
    if name is None:
        return None
    rest = rest.strip()
    if name in _BARE_ONLY and rest:
        return None
    if name == "language":
        target = fold(rest)
        if target.startswith(("sw", "ki")):
            return Command("swahili")
        if target.startswith(("en", "eng")):
            return Command("english")
        return Command("language")
    if name == "scam" and not rest:
        return Command("scam")
    if name == "tip" and not rest:
        return Command("tip")
    return Command(name, rest)


TEXTS: dict[str, dict[str, str]] = {
    "help": {
        "en": ("ACE gives checked local guidance. Ask a question in English or Swahili. Commands: "
               "SCAM + message to check a message, TIP + your advice to share knowledge, SOURCES, "
               "MORE, LANG SW, FORGET to delete your data."),
        "sw": ("ACE hutoa ushauri wa eneo lako uliokaguliwa. Uliza swali kwa Kiswahili au Kiingereza. "
               "Amri: UTAPELI + ujumbe kuukagua, DOKEZO + ushauri wako, VYANZO, ZAIDI, LUGHA EN, "
               "FUTA kufuta data yako."),
    },
    "help_short": {
        "en": "Ask ACE a question in English or Swahili. SCAM + message checks it. TIP shares advice. FORGET deletes your data.",
        "sw": "Uliza ACE swali kwa Kiswahili au Kiingereza. UTAPELI + ujumbe huukagua. DOKEZO hutuma ushauri. FUTA hufuta data.",
    },
    "forgotten": {
        "en": "Done. Everything ACE held about this number has been deleted.",
        "sw": "Imekamilika. Kila kitu ACE ilichohifadhi kuhusu nambari hii kimefutwa.",
    },
    "stopped": {
        "en": "You will not get any further messages from ACE unless you write again. Send FORGET to delete your data.",
        "sw": "Hutapokea ujumbe zaidi kutoka ACE isipokuwa uandike tena. Tuma FUTA kufuta data yako.",
    },
    "language": {
        "en": "Reply LANG SW for Kiswahili or LANG EN for English.",
        "sw": "Jibu LUGHA SW kwa Kiswahili au LUGHA EN kwa Kiingereza.",
    },
    "english": {"en": "ACE will reply in English.", "sw": "ACE will reply in English."},
    "swahili": {"en": "ACE itajibu kwa Kiswahili.", "sw": "ACE itajibu kwa Kiswahili."},
    "tip_thanks": {
        "en": "Thank you. Your tip is saved for review by an expert. It will not be shared until it is checked.",
        "sw": "Asante. Dokezo lako limehifadhiwa ili likaguliwe na mtaalamu. Halitatumika hadi likaguliwe.",
    },
    "tip_usage": {
        "en": "Send TIP followed by your advice, for example: TIP neem leaves help against armyworm in Embu.",
        "sw": "Tuma DOKEZO kisha ushauri wako, kwa mfano: DOKEZO majani ya mwarubaini husaidia dhidi ya viwavijeshi.",
    },
    "scam_usage": {
        "en": "Send SCAM followed by the message you are unsure about, and ACE will check it.",
        "sw": "Tuma UTAPELI kisha ujumbe unaoutilia shaka, na ACE itaukagua.",
    },
    "no_sources": {
        "en": "There is no earlier answer to show sources for. Ask a question first.",
        "sw": "Hakuna jibu la awali la kuonyesha vyanzo. Uliza swali kwanza.",
    },
    "no_more": {
        "en": "That is all ACE has on this topic for now. Ask another question or send HELP.",
        "sw": "Hayo ndiyo yote ACE inayo kuhusu mada hii kwa sasa. Uliza swali jingine au tuma MSAADA.",
    },
    "clarify": {
        "en": "ACE has no checked guidance for that yet. ACE can help with: {topics}. Send TIP to suggest knowledge.",
        "sw": "ACE haina ushauri uliokaguliwa kuhusu hilo bado. ACE inaweza kusaidia: {topics}. Tuma DOKEZO kupendekeza.",
    },
}


def say(key: str, language: str, **kwargs: str) -> str:
    lang = language if language in ("en", "sw") else "en"
    return TEXTS[key][lang].format(**kwargs)
