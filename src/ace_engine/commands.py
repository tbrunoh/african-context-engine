"""Keyword commands that work the same on SMS, WhatsApp, USSD free text and the API.

Commands are recognised only by their first word, in English, Swahili or
French, so ordinary questions are never mistaken for commands. The safety
rail always runs before commands: HELP followed by an emergency is still an
emergency.
"""
from __future__ import annotations

from dataclasses import dataclass

from .text import fold

COMMANDS: dict[str, tuple[str, ...]] = {
    "help": ("help", "msaada", "menu", "menyu", "start", "anza", "aide"),
    "forget": ("forget", "futa", "delete", "oublier", "effacer"),
    "stop": ("stop", "acha", "sitisha", "arret", "arreter"),
    "language": ("lang", "language", "lugha", "langue"),
    "english": ("english", "kiingereza", "anglais"),
    "swahili": ("swahili", "kiswahili"),
    "french": ("francais", "french", "kifaransa"),
    "tip": ("tip", "dokezo", "ushauri", "astuce", "conseil"),
    "scam": ("scam", "utapeli", "fraud", "arnaque", "fraude"),
    "sources": ("sources", "source", "vyanzo", "chanzo"),
    "more": ("more", "zaidi", "next", "endelea", "plus", "suite"),
}
LANGUAGE_COMMANDS = {"english": "en", "swahili": "sw", "french": "fr"}
_LOOKUP = {word: name for name, words in COMMANDS.items() for word in words}
# Commands that must be the whole message, so a question that starts with the
# word is still treated as a question ("stop armyworm", "plus de pluie ?").
_BARE_ONLY = {"help", "forget", "stop", "english", "swahili", "french", "sources", "more"}


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
        if target.startswith(("en", "an")):
            return Command("english")
        if target.startswith("fr"):
            return Command("french")
        return Command("language")
    if name in ("scam", "tip") and not rest:
        return Command(name)
    return Command(name, rest)


TEXTS: dict[str, dict[str, str]] = {
    "help": {
        "en": ("ACE gives checked local guidance. Ask a question in English, Swahili or French. Commands: "
               "SCAM + message to check a message, TIP + your advice to share knowledge, SOURCES, "
               "MORE, LANG SW or LANG FR, FORGET to delete your data."),
        "sw": ("ACE hutoa ushauri wa eneo lako uliokaguliwa. Uliza swali kwa Kiswahili, Kiingereza au Kifaransa. "
               "Amri: UTAPELI + ujumbe kuukagua, DOKEZO + ushauri wako, VYANZO, ZAIDI, LUGHA EN, "
               "FUTA kufuta data yako."),
        "fr": ("ACE donne des conseils locaux vérifiés. Posez votre question en français, en anglais ou en swahili. "
               "Commandes : ARNAQUE + message pour le vérifier, ASTUCE + votre conseil, SOURCES, SUITE, "
               "LANGUE EN, OUBLIER pour effacer vos données."),
    },
    "help_short": {
        "en": "Ask ACE a question in English, Swahili or French. SCAM + message checks it. FORGET deletes your data.",
        "sw": "Uliza ACE swali kwa Kiswahili au Kiingereza. UTAPELI + ujumbe huukagua. FUTA hufuta data.",
        "fr": "Posez votre question à ACE. ARNAQUE + message pour le vérifier. OUBLIER efface vos données.",
    },
    "forgotten": {
        "en": "Done. Everything ACE held about this number has been deleted.",
        "sw": "Imekamilika. Kila kitu ACE ilichohifadhi kuhusu nambari hii kimefutwa.",
        "fr": "C'est fait. Tout ce que ACE gardait sur ce numéro a été effacé.",
    },
    "stopped": {
        "en": "You will not get any further messages from ACE unless you write again. Send FORGET to delete your data.",
        "sw": "Hutapokea ujumbe zaidi kutoka ACE isipokuwa uandike tena. Tuma FUTA kufuta data yako.",
        "fr": ("Vous ne recevrez plus de messages de ACE sauf si vous écrivez à nouveau. "
               "Envoyez OUBLIER pour effacer vos données."),
    },
    "language": {
        "en": "Reply LANG SW for Kiswahili, LANG FR for French or LANG EN for English.",
        "sw": "Jibu LUGHA SW kwa Kiswahili, LUGHA FR kwa Kifaransa au LUGHA EN kwa Kiingereza.",
        "fr": "Répondez LANGUE FR pour le français, LANGUE EN pour l'anglais ou LANGUE SW pour le swahili.",
    },
    "english": {"en": "ACE will reply in English.", "sw": "ACE will reply in English.", "fr": "ACE will reply in English."},
    "swahili": {"en": "ACE itajibu kwa Kiswahili.", "sw": "ACE itajibu kwa Kiswahili.", "fr": "ACE itajibu kwa Kiswahili."},
    "french": {"en": "ACE répondra en français.", "sw": "ACE répondra en français.", "fr": "ACE répondra en français."},
    "tip_thanks": {
        "en": "Thank you. Your tip is saved for review by an expert. It will not be shared until it is checked.",
        "sw": "Asante. Dokezo lako limehifadhiwa ili likaguliwe na mtaalamu. Halitatumika hadi likaguliwe.",
        "fr": "Merci. Votre conseil est enregistré pour être vérifié par un expert. Il ne sera pas partagé avant.",
    },
    "tip_usage": {
        "en": "Send TIP followed by your advice, for example: TIP neem leaves help against armyworm in Embu.",
        "sw": "Tuma DOKEZO kisha ushauri wako, kwa mfano: DOKEZO majani ya mwarubaini husaidia dhidi ya viwavijeshi.",
        "fr": "Envoyez ASTUCE suivi de votre conseil, par exemple : ASTUCE le neem aide contre la chenille légionnaire.",
    },
    "scam_usage": {
        "en": "Send SCAM followed by the message you are unsure about, and ACE will check it.",
        "sw": "Tuma UTAPELI kisha ujumbe unaoutilia shaka, na ACE itaukagua.",
        "fr": "Envoyez ARNAQUE suivi du message qui vous inquiète, et ACE le vérifiera.",
    },
    "no_sources": {
        "en": "There is no earlier answer to show sources for. Ask a question first.",
        "sw": "Hakuna jibu la awali la kuonyesha vyanzo. Uliza swali kwanza.",
        "fr": "Il n'y a pas encore de réponse dont montrer les sources. Posez d'abord une question.",
    },
    "no_more": {
        "en": "That is all ACE has on this topic for now. Ask another question or send HELP.",
        "sw": "Hayo ndiyo yote ACE inayo kuhusu mada hii kwa sasa. Uliza swali jingine au tuma MSAADA.",
        "fr": "C'est tout ce que ACE a sur ce sujet pour le moment. Posez une autre question ou envoyez AIDE.",
    },
    "clarify": {
        "en": "ACE has no checked guidance for that yet. ACE can help with: {topics}. Send TIP to suggest knowledge.",
        "sw": "ACE haina ushauri uliokaguliwa kuhusu hilo bado. ACE inaweza kusaidia: {topics}. Tuma DOKEZO kupendekeza.",
        "fr": "ACE n'a pas encore de conseil vérifié sur ce sujet. ACE peut aider pour : {topics}. Envoyez ASTUCE pour proposer.",
    },
}


def say(key: str, language: str, **kwargs: str) -> str:
    lang = language if language in ("en", "sw", "fr") else "en"
    return TEXTS[key][lang].format(**kwargs)
