"""Keyword commands that work the same on SMS, WhatsApp, USSD free text and the API.

Commands are recognised only by their first word, in every language ACE
serves, so ordinary questions are never mistaken for commands. The safety
rail always runs before commands: HELP followed by an emergency is still an
emergency.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import i18n
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
for _name in list(COMMANDS):
    COMMANDS[_name] = i18n.phrases(f"commands.COMMANDS.{_name}", COMMANDS[_name])
for _code, _loc in i18n.locales().items():
    _cmd = _loc.name.lower()
    # The bare name works, as ENGLISH does, but not a name of three letters or fewer: BEM is Portuguese for well.
    COMMANDS[_cmd] = tuple(fold(n) for n in _loc.names if len(n) > 3)
    LANGUAGE_COMMANDS[_cmd] = _code
# Every name a language goes by, to read LANG PT, LUGHA KIARABU or LANGUE ARABE.
LANGUAGE_NAMES: dict[str, str] = {"en": "en", "english": "en", "kiingereza": "en", "anglais": "en", "an": "en",
                                  "sw": "sw", "swahili": "sw", "kiswahili": "sw",
                                  "fr": "fr", "francais": "fr", "french": "fr", "kifaransa": "fr"}
for _code, _loc in i18n.locales().items():
    for _n in _loc.names:
        LANGUAGE_NAMES[fold(_n)] = _code
    for _n in (_code, _loc.name, _loc.native):
        LANGUAGE_NAMES[fold(_n)] = _code
_LOOKUP = {fold(word): name for name, words in COMMANDS.items() for word in words}
# Commands that must be the whole message, so a question that starts with the
# word is still treated as a question ("stop armyworm", "plus de pluie ?").
_BARE_ONLY = {"help", "forget", "stop", "sources", "more", *LANGUAGE_COMMANDS}


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
        if not rest:
            return Command("language")
        code = language_code(rest)
        if code:
            return Command(next(n for n, c in LANGUAGE_COMMANDS.items() if c == code))
        # A single word that names no language ACE speaks, such as LANG KIKUYU, gets the menu of the languages it
        # does speak there. In many languages the word for language also means tongue, as in my tongue hurts, so
        # anything longer that names no language is a question, not a command.
        return Command("language") if len(rest.strip(" .!?").split()) == 1 else None
    if name in ("scam", "tip") and not rest:
        return Command(name)
    if name == "tip" and rest.endswith("?"):
        return None  # the word for tip often means advice too, so advice on armyworm? is a question
    return Command(name, rest)


def language_code(text: str) -> str | None:
    """The language a LANG argument names, by code or by any of its names, or None."""
    target = fold(text).strip(" .!")
    if not target:
        return None
    if target in LANGUAGE_NAMES:
        return LANGUAGE_NAMES[target]
    first = target.split()[0]
    if first in LANGUAGE_NAMES:
        return LANGUAGE_NAMES[first]
    # Short and misspelt forms of the first three languages, such as swa, kiswahil, eng or franc. Only these, because
    # many language names begin with ki: LANG KIKUYU must not switch to Swahili.
    for prefix, code in (("swa", "sw"), ("kiswa", "sw"), ("eng", "en"), ("angl", "en"), ("kiinge", "en"),
                         ("kinge", "en"), ("fran", "fr"), ("fren", "fr"), ("kifara", "fr")):
        if first.startswith(prefix):
            return code
    return None


TEXTS: dict[str, dict[str, str]] = {
    "help": {
        "en": ("ACE gives checked local guidance. Ask a question in your language. Commands: "
               "SCAM + message to check a message, TIP + your advice to share knowledge, SOURCES, "
               "MORE, LANG + code (for example LANG FR), FORGET to delete your data."),
        "sw": ("ACE hutoa ushauri wa eneo lako uliokaguliwa. Uliza swali kwa lugha yako. "
               "Amri: UTAPELI + ujumbe kuukagua, DOKEZO + ushauri wako, VYANZO, ZAIDI, LUGHA + msimbo "
               "(kwa mfano LUGHA EN), FUTA kufuta data yako."),
        "fr": ("ACE donne des conseils locaux vérifiés. Posez votre question dans votre langue. "
               "Commandes : ARNAQUE + message pour le vérifier, ASTUCE + votre conseil, SOURCES, SUITE, "
               "LANGUE + code (par exemple LANGUE EN), OUBLIER pour effacer vos données."),
    },
    "help_short": {
        "en": "Ask ACE a question in your language. SCAM + message checks it. FORGET deletes your data.",
        "sw": "Uliza ACE swali kwa lugha yako. UTAPELI + ujumbe huukagua. FUTA hufuta data.",
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
        "en": "Reply LANG and a code:",
        "sw": "Jibu LUGHA na msimbo:",
        "fr": "Répondez LANGUE et un code :",
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
    # A message in a language ACE does not speak (see langid): said in the caller's country language.
    "unread": {
        "en": "ACE does not read this language yet. Please write in one of these: {languages}.",
        "sw": "ACE bado haisomi lugha hii. Tafadhali andika kwa mojawapo ya hizi: {languages}.",
        "fr": "ACE ne lit pas encore cette langue. Merci d'écrire dans l'une de celles-ci : {languages}.",
    },
}


# Each added language confirms the switch in its own words, whatever language the request came in.
for _code, _loc in i18n.locales().items():
    TEXTS[_loc.name.lower()] = {lang: _loc.confirm for lang in i18n.all_languages()}
for _key in ("english", "swahili", "french"):
    TEXTS[_key].update({lang: TEXTS[_key]["en"] for lang in i18n.added_languages()})
i18n.localize("commands", globals(), ("TEXTS",))


def language_menu(codes: tuple[str, ...] | None = None) -> str:
    """LANG codes with each language's own name: the caller's country languages, or every language ACE serves.

    32 names would not fit one SMS or a USSD screen, so a caller sees their own country's languages. Any other
    language still works by name or code, as LANG HAUSA or LANG HA."""
    langs = tuple(c for c in (codes or ()) if c in i18n.all_languages()) or i18n.all_languages()
    return ", ".join(f"{code.upper()} {i18n.native_name(code)}" for code in langs)


def say(key: str, language: str, menu: tuple[str, ...] | None = None, **kwargs: str) -> str:
    lang = language if language in i18n.all_languages() else "en"
    text = (TEXTS[key].get(lang) or TEXTS[key]["en"]).format(**kwargs)
    return f"{text} {language_menu(menu)}." if key == "language" else text
